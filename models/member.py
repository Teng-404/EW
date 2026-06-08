"""
models/member.py — Member model

สมาชิกสหกรณ์ที่นำเข้าจาก Excel โดย admin
ใช้เป็น identity หลักในระบบยืนยันตัวตนและลงคะแนน
"""

from __future__ import annotations
from db import get_db


class Member:
    def __init__(self, row: dict):
        self.id        = row["id"]
        self.full_name = row["full_name"]
        self.email     = row.get("email")        # Email เดิมในระบบ
        self.email_new = row.get("email_new")    # Email ใหม่ถ้าเปลี่ยนตอนยืนยันตัวตน
        self.verified  = bool(row.get("verified", False))
        self.created_at = row.get("created_at")

    @property
    def active_email(self) -> str | None:
        """Email ที่ใช้รับ OTP จริง (email_new ถ้ามี มิฉะนั้น email)"""
        return self.email_new or self.email

    # ── Queries ────────────────────────────────────────────

    @classmethod
    def get_by_id(cls, member_id: int) -> "Member | None":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM members WHERE id = %s", (member_id,))
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_by_email(cls, email: str) -> "Member | None":
        """ค้นหาจาก email เดิม หรือ email_new"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM members WHERE email = %s OR email_new = %s LIMIT 1",
            (email, email),
        )
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_by_full_name(cls, full_name: str) -> "Member | None":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM members WHERE full_name = %s LIMIT 1", (full_name,))
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_all(cls) -> list["Member"]:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM members ORDER BY id")
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def get_verified(cls) -> list["Member"]:
        """คืนสมาชิกที่ยืนยันตัวตนแล้ว"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM members WHERE verified = TRUE ORDER BY full_name")
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def get_email_changed(cls) -> list["Member"]:
        """คืนสมาชิกที่เปลี่ยน Email"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM members WHERE email_new IS NOT NULL ORDER BY full_name"
        )
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def count_verified(cls) -> int:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM members WHERE verified = TRUE")
        (n,) = cur.fetchone()
        cur.close()
        return n

    # ── Mutations ──────────────────────────────────────────

    def mark_verified(self, email_new: str | None = None) -> None:
        """ทำเครื่องหมายว่าผ่านขั้นยืนยันตัวตนแล้ว และบันทึก email_new ถ้ามี"""
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE members SET verified = TRUE, email_new = %s WHERE id = %s",
            (email_new, self.id),
        )
        conn.commit()
        cur.close()
        self.verified  = True
        self.email_new = email_new

    # ── Bulk import ────────────────────────────────────────

    @classmethod
    def replace_all(cls, rows: list[dict]) -> int:
        """
        ลบสมาชิกเก่าทั้งหมด แล้ว insert ใหม่จาก list of dict
        แต่ละ dict ต้องมีคีย์ 'full_name' และ 'email' (optional)
        คืนจำนวนแถวที่ import
        """
        conn = get_db()
        cur  = conn.cursor()

        # ลบก่อน (CASCADE ไปถึง otps และ access_logs)
        cur.execute("DELETE FROM members")

        count = 0
        for r in rows:
            full_name = str(r.get("full_name", "")).strip()
            email     = str(r.get("email", "")).strip().lower() or None
            if not full_name:
                continue
            cur.execute(
                "INSERT INTO members (full_name, email) VALUES (%s, %s)",
                (full_name, email),
            )
            count += 1

        conn.commit()
        cur.close()
        return count
