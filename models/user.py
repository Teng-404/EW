"""
models/user.py — User model  (README v2 patch + Excel import + bulk manage)

เพิ่มจากเดิม:
  - set_password()       — เปลี่ยนรหัสผ่าน
  - delete()             — ลบบัญชี
  - _unique_username()   — สร้าง username ไม่ซ้ำจากอีเมล
  - import_from_rows()   — นำเข้าผู้ใช้จาก Excel (full_name, username, email, password)
                           ตั้ง source='excel' เพื่อให้แยกจัดการได้ภายหลัง
  - get_imported()       — รายชื่อผู้ใช้ที่นำเข้าจาก Excel (source='excel')
  - update_profile()     — แก้ไข full_name / username / email
  - bulk_delete()        — ลบผู้ใช้หลายคนพร้อมกัน (เฉพาะ role=voter)

* ต้องรัน migration เพิ่มคอลัมน์ users.source ก่อน (ดู migration_add_users_source.sql)
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
        self.source     = row.get("source", "self")

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

    @classmethod
    def get_imported(cls) -> list["User"]:
        """ผู้ใช้ที่นำเข้าจาก Excel (source='excel')"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE source = 'excel' ORDER BY id DESC")
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def get_voters(cls) -> list["User"]:
        """ผู้ใช้ role=voter ทั้งหมด (ทั้งที่นำเข้า Excel และที่สมัครเอง)
        — สำหรับหน้าจัดการ/ลบเป็นชุด"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE role = 'voter' ORDER BY id DESC")
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    # ── Bulk import (จาก Excel) ────────────────────────────

    @staticmethod
    def _unique_username(cur, email: str, full_name: str) -> str:
        """สร้าง username ไม่ซ้ำ จากส่วนหน้าของอีเมล (fallback เป็น 'user')"""
        base = (email or "").split("@")[0]
        base = "".join(ch for ch in base if ch.isalnum() or ch in "._-")
        if not base:
            base = "user"
        base = base[:40]
        candidate, n = base, 1
        while True:
            cur.execute("SELECT 1 FROM users WHERE username = %s LIMIT 1", (candidate,))
            if not cur.fetchone():
                return candidate
            n += 1
            candidate = f"{base}{n}"

    @classmethod
    def import_from_rows(cls, rows: list[dict]) -> dict:
        """
        นำเข้าผู้ใช้จาก Excel — แต่ละ row = {full_name, username, email, password}
          - ค้นจาก email ก่อน ถ้าไม่เจอค้นจาก full_name
          - ไม่เจอ + มีรหัสผ่าน  -> สร้างใหม่ (role=voter, source=excel)
                                    ใช้ username ที่กรอกมา ถ้าเว้นว่างจะสร้างจากอีเมลอัตโนมัติ
          - เจอแล้ว              -> อัปเดต email + รหัสผ่าน (ถ้ามี) + username (ถ้ากรอกมา)
          - คนใหม่แต่ไม่มีรหัสผ่าน -> ข้าม
        commit ทีละแถว เพื่อให้แถวที่ผิดพลาด (เช่น username/email ซ้ำ) ไม่ทำให้ทั้งไฟล์ล้ม
        คืน {'added': x, 'updated': y, 'skipped': z}
        """
        conn = get_db()
        cur  = conn.cursor(dictionary=True)

        added = updated = skipped = 0
        for r in rows:
            full_name = (r.get("full_name") or "").strip()
            username  = (r.get("username") or "").strip()
            email     = (r.get("email") or "").strip().lower()
            password  = (r.get("password") or "").strip()

            if not full_name or not email:
                skipped += 1
                continue

            try:
                cur.execute(
                    "SELECT id FROM users WHERE email = %s OR full_name = %s LIMIT 1",
                    (email, full_name),
                )
                existing = cur.fetchone()

                if existing:
                    sets, params = ["email = %s"], [email]
                    if password:
                        sets.append("password = %s")
                        params.append(cls.hash_password(password))
                    if username:
                        sets.append("username = %s")
                        params.append(username)
                    params.append(existing["id"])
                    cur.execute(
                        f"UPDATE users SET {', '.join(sets)} WHERE id = %s", params
                    )
                    conn.commit()
                    updated += 1
                else:
                    if not password:
                        skipped += 1
                        continue
                    uname = username or cls._unique_username(cur, email, full_name)
                    cur.execute(
                        "INSERT INTO users (username, email, password, full_name, role, source) "
                        "VALUES (%s, %s, %s, %s, 'voter', 'excel')",
                        (uname, email, cls.hash_password(password), full_name),
                    )
                    conn.commit()
                    added += 1
            except Exception:
                conn.rollback()
                skipped += 1
                continue

        cur.close()
        return {"added": added, "updated": updated, "skipped": skipped}

    @classmethod
    def bulk_delete(cls, ids: list[int]) -> int:
        """ลบผู้ใช้หลายคน — เฉพาะ role=voter เพื่อกันลบ admin โดยไม่ตั้งใจ"""
        ids = [int(i) for i in ids if i]
        if not ids:
            return 0
        placeholders = ",".join(["%s"] * len(ids))
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            f"DELETE FROM users WHERE id IN ({placeholders}) AND role = 'voter'",
            ids,
        )
        conn.commit()
        n = cur.rowcount
        cur.close()
        return n

    # ── Mutations ──────────────────────────────────────────

    def update_profile(self, full_name=None, username=None, email=None) -> None:
        """แก้ไขข้อมูลโปรไฟล์ — ค่าที่เป็น None จะไม่ถูกแตะ"""
        sets, params = [], []
        if full_name is not None:
            sets.append("full_name = %s"); params.append(full_name)
        if username is not None:
            sets.append("username = %s");  params.append(username)
        if email is not None:
            sets.append("email = %s");     params.append(email)
        if not sets:
            return
        params.append(self.id)
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = %s", params)
        conn.commit()
        cur.close()
        if full_name is not None: self.full_name = full_name
        if username is not None:  self.username  = username
        if email is not None:     self.email     = email

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
