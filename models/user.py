"""
models/user.py — User model  (README v2 patch)

เพิ่มจากเดิม:
  - set_password()  — เปลี่ยนรหัสผ่าน (ใช้ใน admin edit_user)
  - delete()        — ลบบัญชี (ใช้ใน admin delete_user)
"""

from __future__ import annotations

import bcrypt
from flask_login import UserMixin
from db import get_db


class User(UserMixin):
    def __init__(self, row: dict):
        self.id         = row["id"]
        self.username   = row["username"]
        self.email      = row["email"]
        self.full_name  = row["full_name"]
        self.role       = row["role"]
        self._is_active = bool(row["is_active"])
        self._password  = row["password"]

    # ── Flask-Login ────────────────────────────────────────

    def get_id(self) -> str:
        return str(self.id)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_active(self) -> bool:
        return self._is_active

    # ── Password ───────────────────────────────────────────

    def check_password(self, plain: str) -> bool:
        return bcrypt.checkpw(plain.encode(), self._password.encode())

    @staticmethod
    def hash_password(plain: str) -> str:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

    def set_password(self, plain: str) -> None:
        """เปลี่ยนรหัสผ่าน — ใช้ใน admin"""
        hashed = self.hash_password(plain)
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, self.id))
        conn.commit()
        cur.close()
        self._password = hashed

    # ── Queries ────────────────────────────────────────────

    @classmethod
    def get_by_id(cls, user_id: int) -> "User | None":
        """ใช้กับ login_manager — คืนเฉพาะ active user"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id = %s AND is_active = TRUE", (user_id,))
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_by_id_any(cls, user_id: int) -> "User | None":
        """ใช้กับ admin — คืน user ทุกสถานะ"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_by_username(cls, username: str) -> "User | None":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_by_email(cls, email: str) -> "User | None":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def create(cls, username: str, email: str, password: str, full_name: str) -> "User":
        hashed = cls.hash_password(password)
        conn   = get_db()
        cur    = conn.cursor(dictionary=True)
        cur.execute(
            "INSERT INTO users (username, email, password, full_name) VALUES (%s,%s,%s,%s)",
            (username, email, hashed, full_name),
        )
        conn.commit()
        user_id = cur.lastrowid
        cur.close()
        return cls.get_by_id_any(user_id)

    @classmethod
    def exists_full_name(cls, full_name: str) -> bool:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE full_name = %s", (full_name,))
        result = cur.fetchone()
        cur.close()
        return result is not None

    @classmethod
    def get_all(cls) -> list["User"]:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users ORDER BY id")
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    # ── Mutations ──────────────────────────────────────────

    def set_role(self, role: str) -> None:
        if role not in ("voter", "admin"):
            raise ValueError("role ต้องเป็น 'voter' หรือ 'admin'")
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("UPDATE users SET role = %s WHERE id = %s", (role, self.id))
        conn.commit()
        cur.close()
        self.role = role

    def set_active(self, is_active: bool) -> None:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("UPDATE users SET is_active = %s WHERE id = %s", (is_active, self.id))
        conn.commit()
        cur.close()
        self._is_active = is_active

    def delete(self) -> None:
        """ลบบัญชี — ใช้ใน admin"""
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s", (self.id,))
        conn.commit()
        cur.close()
