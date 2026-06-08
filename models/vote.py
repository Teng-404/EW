"""
models/vote.py — Vote model + OTP helper  (README v2 patch)

การเปลี่ยนแปลงจากเดิม:
  - Vote.cast_hashed()     — บันทึกโดยใช้ member_id_hash แทน user_id
  - Vote.has_voted()       — ตรวจจาก member_id_hash + election_id
  - OTP.create_for_member  — ใช้ member_id (ไม่ใช่ user_id)
  - OTP.verify_for_member  — ใช้ member_id

เก็บ Vote.cast() และ OTP.create()/verify() เดิมไว้ (ใช้กับ admin login)
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from db import get_db


class Vote:
    def __init__(self, row: dict):
        self.id             = row["id"]
        self.member_id_hash = row.get("member_id_hash")
        self.candidate_id   = row["candidate_id"]
        self.election_id    = row["election_id"]
        self.voted_at       = row.get("voted_at")

    # ── New: hash-based cast ───────────────────────────────

    @classmethod
    def cast_hashed(
        cls, member_id_hash: str, candidate_id: int, election_id: int
    ) -> "Vote":
        """บันทึกคะแนนโดยใช้ hash แทน member_id จริง"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            INSERT INTO votes (member_id_hash, candidate_id, election_id)
            VALUES (%s, %s, %s)
            """,
            (member_id_hash, candidate_id, election_id),
        )
        conn.commit()
        vote_id = cur.lastrowid
        cur.close()
        cur2 = conn.cursor(dictionary=True)
        cur2.execute("SELECT * FROM votes WHERE id = %s", (vote_id,))
        row = cur2.fetchone()
        cur2.close()
        return cls(row)

    @classmethod
    def has_voted(cls, member_id_hash: str, election_id: int) -> bool:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT 1 FROM votes WHERE member_id_hash = %s AND election_id = %s",
            (member_id_hash, election_id),
        )
        result = cur.fetchone()
        cur.close()
        return result is not None

    @classmethod
    def count_by_election(cls, election_id: int) -> int:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT COUNT(DISTINCT member_id_hash) FROM votes WHERE election_id = %s",
            (election_id,),
        )
        (n,) = cur.fetchone()
        cur.close()
        return n

    # ── Legacy (ใช้กับ admin/users ที่ยังอ้างอิง user_id) ─

    @classmethod
    def cast(cls, user_id: int, candidate_id: int, election_id: int) -> None:
        """Legacy — ไม่ควรใช้ใน flow ใหม่"""
        pass

    @classmethod
    def get_voters_by_election(cls, election_id: int) -> list[dict]:
        """สำหรับ admin export — คืน hash + voted_at เท่านั้น"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT member_id_hash, voted_at
            FROM   votes
            WHERE  election_id = %s
            ORDER  BY voted_at
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

    # ── New: member-based OTP ──────────────────────────────

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
