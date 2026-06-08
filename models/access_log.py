"""
models/access_log.py — Access Log model

บันทึกทุกการเข้าใช้งานระบบ (verify, vote, admin)
"""

from __future__ import annotations
from datetime import datetime
from db import get_db


class AccessLog:
    def __init__(self, row: dict):
        self.id          = row["id"]
        self.member_id   = row.get("member_id")
        self.action      = row["action"]
        self.ip_address  = row["ip_address"]
        self.system_type = row.get("system_type")
        self.logged_at   = row.get("logged_at")

    @classmethod
    def log(
        cls,
        action: str,
        ip_address: str,
        system_type: str = None,
        member_id: int = None,
    ) -> None:
        """บันทึก log — ใช้ง่าย ไม่ raise exception"""
        try:
            conn = get_db()
            cur  = conn.cursor()
            cur.execute(
                """
                INSERT INTO access_logs (member_id, action, ip_address, system_type)
                VALUES (%s, %s, %s, %s)
                """,
                (member_id, action, ip_address, system_type),
            )
            conn.commit()
            cur.close()
        except Exception:
            pass  # log ไม่ควร break request หลัก

    @classmethod
    def search(
        cls,
        keyword: str = "",
        ip: str = "",
        date_from: str = "",
        date_to: str = "",
        system_type: str = "",
        limit: int = 500,
    ) -> list["AccessLog"]:
        conn   = get_db()
        cur    = conn.cursor(dictionary=True)
        wheres = ["1=1"]
        params = []

        if keyword:
            wheres.append(
                "(m.full_name LIKE %s OR al.action LIKE %s)"
            )
            params += [f"%{keyword}%", f"%{keyword}%"]
        if ip:
            wheres.append("al.ip_address LIKE %s")
            params.append(f"%{ip}%")
        if date_from:
            wheres.append("al.logged_at >= %s")
            params.append(date_from)
        if date_to:
            wheres.append("al.logged_at <= %s")
            params.append(date_to + " 23:59:59")
        if system_type:
            wheres.append("al.system_type = %s")
            params.append(system_type)

        sql = f"""
            SELECT al.*, m.full_name AS member_name
            FROM   access_logs al
            LEFT JOIN members m ON m.id = al.member_id
            WHERE  {' AND '.join(wheres)}
            ORDER  BY al.logged_at DESC
            LIMIT  %s
        """
        params.append(limit)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows   # คืน raw dict list (ใช้ใน template โดยตรง)

    @classmethod
    def get_all_raw(cls, limit: int = 1000) -> list[dict]:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT al.*, m.full_name AS member_name
            FROM   access_logs al
            LEFT JOIN members m ON m.id = al.member_id
            ORDER  BY al.logged_at DESC
            LIMIT  %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows
