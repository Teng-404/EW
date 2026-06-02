"""
models/election.py — Election model

จัดการวาระการเลือกตั้ง: สร้าง, เปิด/ปิด, ดึงข้อมูล
"""

from __future__ import annotations

from datetime import datetime
from db import get_db


class Election:
    def __init__(self, row: dict):
        self.id          = row["id"]
        self.title       = row["title"]
        self.description = row.get("description")
        self.status      = row["status"]          # pending | open | closed
        self.start_time  = row.get("start_time")
        self.end_time    = row.get("end_time")
        self.created_at  = row.get("created_at")
        self.created_by  = row.get("created_by")

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    @property
    def is_closed(self) -> bool:
        return self.status == "closed"

    # ── Queries ────────────────────────────────────────────
    @classmethod
    def get_by_id(cls, election_id: int) -> "Election | None":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM elections WHERE id = %s", (election_id,))
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_all(cls) -> list["Election"]:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM elections ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def get_open(cls) -> list["Election"]:
        """คืนเฉพาะวาระที่กำลังเปิดรับ vote"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM elections WHERE status = 'open' ORDER BY start_time")
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def create(cls, title: str, description: str = "", created_by: int = None) -> "Election":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "INSERT INTO elections (title, description, created_by) VALUES (%s, %s, %s)",
            (title, description, created_by),
        )
        conn.commit()
        election_id = cur.lastrowid
        cur.close()
        return cls.get_by_id(election_id)

    def set_status(self, status: str) -> None:
        """เปลี่ยน status: pending → open → closed"""
        valid = ("pending", "open", "closed")
        if status not in valid:
            raise ValueError(f"status ต้องเป็น {valid}")

        now  = datetime.now()
        conn = get_db()
        cur  = conn.cursor()

        if status == "open":
            cur.execute(
                "UPDATE elections SET status = 'open', start_time = %s WHERE id = %s",
                (now, self.id),
            )
        elif status == "closed":
            cur.execute(
                "UPDATE elections SET status = 'closed', end_time = %s WHERE id = %s",
                (now, self.id),
            )
        else:
            cur.execute(
                "UPDATE elections SET status = %s WHERE id = %s",
                (status, self.id),
            )

        conn.commit()
        cur.close()
        self.status = status

    def delete(self) -> None:
        """ลบวาระ (cascade ลบ candidates + votes ด้วย)"""
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("DELETE FROM elections WHERE id = %s", (self.id,))
        conn.commit()
        cur.close()
