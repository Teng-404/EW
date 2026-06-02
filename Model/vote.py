"""
models/vote.py — Vote model + OTP helper

แยก logic การ vote และ OTP ออกจาก route
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from db import get_db


class Vote:
    def __init__(self, row: dict):
        self.id           = row["id"]
        self.user_id      = row["user_id"]
        self.candidate_id = row["candidate_id"]
        self.election_id  = row["election_id"]
        self.voted_at     = row.get("voted_at")

    @classmethod
    def cast(cls, user_id: int, candidate_id: int, election_id: int) -> "Vote":
        """
        บันทึกคะแนน — raise IntegrityError ถ้า vote ซ้ำ (UNIQUE constraint)
        ตรวจสอบ user.has_voted() ก่อนเรียกฟังก์ชันนี้เสมอ
        """
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            INSERT INTO votes (user_id, candidate_id, election_id)
            VALUES (%s, %s, %s)
            """,
            (user_id, candidate_id, election_id),
        )
        conn.commit()
        vote_id = cur.lastrowid
        cur.close()

        # คืน Vote object ที่เพิ่งสร้าง
        cur2 = conn.cursor(dictionary=True)
        cur2.execute("SELECT * FROM votes WHERE id = %s", (vote_id,))
        row = cur2.fetchone()
        cur2.close()
        return cls(row)

    @classmethod
    def get_voters_by_election(cls, election_id: int) -> list[dict]:
        """คืนรายชื่อผู้ลงคะแนนในวาระ (สำหรับ admin export)"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT u.full_name, u.username, v.voted_at
            FROM   votes v
            JOIN   users u ON u.id = v.user_id
            WHERE  v.election_id = %s
            ORDER  BY v.voted_at
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

    @classmethod
    def create(cls, user_id: int, purpose: str = "vote") -> str:
        """สร้าง OTP ใหม่ (ยกเลิก OTP เก่าที่ยังไม่ใช้ก่อน) คืน code"""
        code       = cls._generate_code()
        expires_at = datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)

        conn = get_db()
        cur  = conn.cursor()

        # ยกเลิก OTP เก่า
        cur.execute(
            "UPDATE otps SET used = TRUE WHERE user_id = %s AND purpose = %s AND used = FALSE",
            (user_id, purpose),
        )

        # สร้างใหม่
        cur.execute(
            "INSERT INTO otps (user_id, code, purpose, expires_at) VALUES (%s, %s, %s, %s)",
            (user_id, code, purpose, expires_at),
        )
        conn.commit()
        cur.close()
        return code

    @classmethod
    def verify(cls, user_id: int, code: str, purpose: str = "vote") -> bool:
        """ตรวจ OTP — คืน True และ mark used ถ้าถูก"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id FROM otps
            WHERE  user_id    = %s
              AND  code       = %s
              AND  purpose    = %s
              AND  used       = FALSE
              AND  expires_at > NOW()
            LIMIT 1
            """,
            (user_id, code, purpose),
        )
        row = cur.fetchone()

        if not row:
            cur.close()
            return False

        # Mark ว่าใช้แล้ว
        cur.execute("UPDATE otps SET used = TRUE WHERE id = %s", (row["id"],))
        conn.commit()
        cur.close()
        return True
