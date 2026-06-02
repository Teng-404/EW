"""
models/user.py — User model

รองรับ Flask-Login ผ่าน UserMixin
ทุก query ผ่าน get_db() เพื่อใช้ connection pool
"""

from __future__ import annotations

import bcrypt
from flask_login import UserMixin
from db import get_db


class User(UserMixin):
    def __init__(self, row: dict):
        self.id        = row["id"]
        self.username  = row["username"]
        self.email     = row["email"]
        self.full_name = row["full_name"]
        self.role      = row["role"]
        self._is_active = bool(row["is_active"])
        self._password = row["password"]       # bcrypt hash (private)

    # ── Flask-Login required ───────────────────────────────
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

    # ── Queries ────────────────────────────────────────────
    @classmethod
    def get_by_id(cls, user_id: int) -> "User | None":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id = %s AND is_active = TRUE", (user_id,))
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
        """สร้าง user ใหม่ คืน User object"""
        hashed = cls.hash_password(password)
        conn   = get_db()
        cur    = conn.cursor(dictionary=True)
        cur.execute(
            """
            INSERT INTO users (username, email, password, full_name)
            VALUES (%s, %s, %s, %s)
            """,
            (username, email, hashed, full_name),
        )
        conn.commit()
        user_id = cur.lastrowid
        cur.close()
        return cls.get_by_id(user_id)

    @classmethod
    def exists_full_name(cls, full_name: str) -> bool:
        """ตรวจว่าชื่อ-สกุลนี้เคย vote แล้วหรือยัง (ระดับ app)"""
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE full_name = %s", (full_name,))
        result = cur.fetchone()
        cur.close()
        return result is not None

    def has_voted(self, election_id: int) -> bool:
        """ตรวจว่า user นี้ vote วาระนี้แล้วหรือยัง"""
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT 1 FROM votes WHERE user_id = %s AND election_id = %s",
            (self.id, election_id),
        )
        result = cur.fetchone()
        cur.close()
        return result is not None
