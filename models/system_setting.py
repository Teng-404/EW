"""
models/system_setting.py — System settings model

เก็บค่า flag เปิด/ระงับแต่ละระบบ
  verify_enabled  — ระบบยืนยันตัวตน (ขั้นที่ 1)
  vote_enabled    — ระบบลงคะแนน (ขั้นที่ 2)
"""

from __future__ import annotations
from db import get_db


class SystemSetting:

    @staticmethod
    def get(key: str, default: str = "1") -> str:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT value FROM system_settings WHERE setting_key = %s", (key,)
        )
        row = cur.fetchone()
        cur.close()
        return row["value"] if row else default

    @staticmethod
    def set(key: str, value: str) -> None:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            """
            INSERT INTO system_settings (setting_key, value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE value = %s, updated_at = NOW()
            """,
            (key, value, value),
        )
        conn.commit()
        cur.close()

    @staticmethod
    def is_enabled(key: str) -> bool:
        return SystemSetting.get(key) == "1"

    @staticmethod
    def get_all() -> dict:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT setting_key, value FROM system_settings")
        rows = cur.fetchall()
        cur.close()
        return {r["setting_key"]: r["value"] for r in rows}
