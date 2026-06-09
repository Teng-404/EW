"""
models/vote.py — Vote model + Turnout + OTP helper  (README v3 patch)

หลักการความลับ/ความโปร่งใส (ข้อกำหนดใหม่):
  - "การมาใช้สิทธิ" (ใคร มาลงคะแนนแล้วบ้าง)  → ตรวจสอบได้ เก็บใน  vote_turnout
        เก็บ member_id จริง + เวลา เพื่อความโปร่งใส กันลงคะแนนซ้ำ และตรวจสอบรายชื่อได้
  - "ผลการลงคะแนน" (เลือกใคร)              → เป็นความลับ เก็บใน  votes
        เก็บเฉพาะ candidate_id + election_id เท่านั้น ไม่มีตัวระบุผู้ลงคะแนน
        จึงตรวจนับผลได้ แต่ย้อนกลับไปหาผู้ลงคะแนนไม่ได้

การเปลี่ยนแปลงจากเดิม:
  - ตัด member_id_hash ออกจากตาราง votes (เดิม hash แบบ deterministic = ย้อนรอยได้)
  - Vote.cast_secret()      — บันทึกบัตรลงคะแนนแบบไม่ผูกกับผู้ลงคะแนน
  - Vote.count_by_election() — นับจำนวนบัตรในวาระ
  - Turnout.record/has_voted/count_by_election/list_by_election — บันทึก/ตรวจการมาใช้สิทธิ
  - OTP ทั้งหมดคงเดิม
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from db import get_db


# ── บัตรลงคะแนน (เป็นความลับ — ไม่ผูกกับผู้ลงคะแนน) ───────────

class Vote:
    """บัตรลงคะแนน 1 ใบ = ผู้สมัคร 1 คน ในวาระ 1 วาระ
    ไม่มีฟิลด์ใดที่ระบุตัวผู้ลงคะแนนได้ → ตรวจนับผลได้ แต่ย้อนรอยไม่ได้
    """

    def __init__(self, row: dict):
        self.id           = row["id"]
        self.candidate_id = row["candidate_id"]
        self.election_id  = row["election_id"]
        self.voted_at     = row.get("voted_at")

    @classmethod
    def cast_secret(cls, candidate_id: int, election_id: int) -> None:
        """บันทึกบัตรลงคะแนนแบบไม่ระบุตัวตน"""
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO votes (candidate_id, election_id) VALUES (%s, %s)",
            (candidate_id, election_id),
        )
        conn.commit()
        cur.close()

    @classmethod
    def count_by_election(cls, election_id: int) -> int:
        """จำนวนบัตรลงคะแนนทั้งหมดในวาระ (รวมทุกผู้สมัคร)"""
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM votes WHERE election_id = %s", (election_id,))
        (n,) = cur.fetchone()
        cur.close()
        return n


# ── การมาใช้สิทธิ (ตรวจสอบได้ — โปร่งใส) ─────────────────────

class Turnout:
    """ทะเบียนผู้มาใช้สิทธิ — แยกออกจากบัตรลงคะแนนโดยสิ้นเชิง
    ใช้สำหรับ: กันลงคะแนนซ้ำ, นับจำนวนผู้มาใช้สิทธิ, ตรวจสอบรายชื่อ
    """

    @classmethod
    def record(cls, member_id: int, election_id: int) -> None:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "INSERT IGNORE INTO vote_turnout (member_id, election_id) VALUES (%s, %s)",
            (member_id, election_id),
        )
        conn.commit()
        cur.close()

    @classmethod
    def has_voted(cls, member_id: int, election_id: int) -> bool:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT 1 FROM vote_turnout WHERE member_id = %s AND election_id = %s",
            (member_id, election_id),
        )
        result = cur.fetchone()
        cur.close()
        return result is not None

    @classmethod
    def count_by_election(cls, election_id: int) -> int:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM vote_turnout WHERE election_id = %s",
            (election_id,),
        )
        (n,) = cur.fetchone()
        cur.close()
        return n

    @classmethod
    def list_by_election(cls, election_id: int) -> list[dict]:
        """รายชื่อผู้มาใช้สิทธิในวาระ — สำหรับตรวจสอบความโปร่งใส (admin export)"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT t.member_id,
                   m.full_name,
                   t.voted_at
            FROM   vote_turnout t
            LEFT JOIN members m ON m.id = t.member_id
            WHERE  t.election_id = %s
            ORDER  BY t.voted_at
            """,
            (election_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows


# ── OTP ───────────────────────────────────────────────────────

OTP_EXPIRE_MINUTES = 5


class OTP:
    @staticmethod
    def _generate_code(length: int = 6) -> str:
        return "".join(random.choices(string.digits, k=length))

    # ── member-based OTP ───────────────────────────────────

    @classmethod
    def create_for_member(cls, member_id: int, purpose: str = "vote") -> str:
        code       = cls._generate_code()
        expires_at = datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE otps SET used = TRUE WHERE member_id = %s AND purpose = %s AND used = FALSE",
            (member_id, purpose),
        )
        cur.execute(
            "INSERT INTO otps (member_id, code, purpose, expires_at) VALUES (%s, %s, %s, %s)",
            (member_id, code, purpose, expires_at),
        )
        conn.commit()
        cur.close()
        return code

    @classmethod
    def verify_for_member(cls, member_id: int, code: str, purpose: str = "vote") -> bool:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id FROM otps
            WHERE  member_id  = %s
              AND  code       = %s
              AND  purpose    = %s
              AND  used       = FALSE
              AND  expires_at > NOW()
            LIMIT 1
            """,
            (member_id, code, purpose),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            return False
        cur.execute("UPDATE otps SET used = TRUE WHERE id = %s", (row["id"],))
        conn.commit()
        cur.close()
        return True

    # ── Legacy (user-based) ────────────────────────────────

    @classmethod
    def create(cls, user_id: int, purpose: str = "vote") -> str:
        """Legacy — ใช้ user_id แทน member_id"""
        return cls.create_for_member(user_id, purpose)

    @classmethod
    def verify(cls, user_id: int, code: str, purpose: str = "vote") -> bool:
        return cls.verify_for_member(user_id, code, purpose)
