"""
seed_admin.py — สร้างบัญชี admin คนแรก (รันครั้งเดียว)

วิธีใช้:
    python seed_admin.py

จะถามชื่อ-นามสกุล / username / email / รหัสผ่าน แล้วสร้าง user
พร้อม role='admin' ให้อัตโนมัติ (รหัสผ่านถูก hash ด้วย bcrypt ผ่านโมเดล User
ของโปรเจกต์ จึง login เข้าได้ทันที)

ถ้ามี username/email/full_name ซ้ำอยู่แล้ว จะแจ้งเตือนและไม่สร้างซ้ำ
"""

import getpass

from app import create_app
from db import get_db
from models.user import User


def _exists(field: str, value: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT 1 FROM users WHERE {field} = %s LIMIT 1", (value,))
    found = cur.fetchone() is not None
    cur.close()
    return found


def main() -> None:
    print("=== สร้างบัญชี Admin ===\n")

    full_name = input("ชื่อ-นามสกุล : ").strip()
    username  = input("Username     : ").strip()
    email     = input("Email        : ").strip().lower()

    pw1 = getpass.getpass("รหัสผ่าน (อย่างน้อย 8 ตัว) : ")
    pw2 = getpass.getpass("ยืนยันรหัสผ่าน             : ")

    # ── ตรวจสอบเบื้องต้น ──
    if not all([full_name, username, email, pw1]):
        print("\n[ผิดพลาด] กรอกข้อมูลให้ครบทุกช่อง")
        return
    if len(pw1) < 8:
        print("\n[ผิดพลาด] รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
        return
    if pw1 != pw2:
        print("\n[ผิดพลาด] รหัสผ่านไม่ตรงกัน")
        return

    app = create_app()
    with app.app_context():
        if _exists("username", username):
            print(f"\n[ผิดพลาด] username '{username}' มีอยู่แล้ว")
            return
        if _exists("email", email):
            print(f"\n[ผิดพลาด] email '{email}' มีอยู่แล้ว")
            return
        if _exists("full_name", full_name):
            print(f"\n[ผิดพลาด] ชื่อ-นามสกุล '{full_name}' มีอยู่แล้ว")
            return

        # สร้าง user (default role = voter) แล้วเลื่อนเป็น admin
        user = User.create(username, email, pw1, full_name)
        user.set_role("admin")

        print(f"\n[สำเร็จ] สร้าง admin '{username}' แล้ว — login ได้ทันทีที่ /login")


if __name__ == "__main__":
    main()
