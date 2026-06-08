"""
models/election.py — Election model  (README v2 patch)

เพิ่ม field: type, max_votes, is_visible
ปรับ create() รับ type, max_votes, is_visible
เพิ่ม get_visible_open(), get_by_type(), update_settings()
"""

from __future__ import annotations
from datetime import datetime
from db import get_db

ELECTION_TYPES = {
    "president":  "เลือกตั้งประธานกรรมการ",
    "treasurer":  "เลือกตั้งเหรัญญิก",
    "committee":  "เลือกตั้งกรรมการ",
}


class Election:
    def __init__(self, row: dict):
        self.id         = row["id"]
        self.title      = row["title"]
        self.type       = row.get("type", "committee")
        self.max_votes  = row.get("max_votes", 1)
        self.is_visible = bool(row.get("is_visible", True))
        self.status     = row["status"]
        self.start_time = row.get("start_time")
        self.end_time   = row.get("end_time")
        self.created_at = row.get("created_at")
        self.created_by = row.get("created_by")

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    @property
    def is_closed(self) -> bool:
        return self.status == "closed"

    @property
    def type_label(self) -> str:
        return ELECTION_TYPES.get(self.type, self.type)

    @classmethod
    def get_by_id(cls, election_id: int) -> "Election | None":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM elections WHERE id = %s", (election_id,))
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_by_type(cls, election_type: str) -> "Election | None":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM elections WHERE type = %s ORDER BY id LIMIT 1",
            (election_type,),
        )
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_all(cls) -> list["Election"]:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM elections ORDER BY type, created_at")
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def get_open(cls) -> list["Election"]:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM elections WHERE status = 'open' ORDER BY type")
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def get_visible_open(cls) -> list["Election"]:
        """วาระที่เปิดและมองเห็น — ใช้แสดงเมนูในหน้า ballot"""
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM elections WHERE status='open' AND is_visible=TRUE ORDER BY type"
        )
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def create(
        cls,
        title: str,
        election_type: str,
        max_votes: int = 1,
        is_visible: bool = True,
        created_by: int = None,
    ) -> "Election":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "INSERT INTO elections (title, type, max_votes, is_visible, created_by) VALUES (%s,%s,%s,%s,%s)",
            (title, election_type, max_votes, is_visible, created_by),
        )
        conn.commit()
        election_id = cur.lastrowid
        cur.close()
        return cls.get_by_id(election_id)

    def set_status(self, status: str) -> None:
        if status not in ("pending", "open", "closed"):
            raise ValueError("status ไม่ถูกต้อง")
        conn = get_db()
        cur  = conn.cursor()
        now  = datetime.now()
        if status == "open":
            cur.execute("UPDATE elections SET status=%s, start_time=%s WHERE id=%s", (status, now, self.id))
        elif status == "closed":
            cur.execute("UPDATE elections SET status=%s, end_time=%s WHERE id=%s", (status, now, self.id))
        else:
            cur.execute("UPDATE elections SET status=%s WHERE id=%s", (status, self.id))
        conn.commit()
        cur.close()
        self.status = status

    def update_settings(self, title=None, max_votes=None, is_visible=None) -> None:
        updates, params = [], []
        if title is not None:
            updates.append("title=%s");      params.append(title)
        if max_votes is not None:
            updates.append("max_votes=%s");  params.append(max_votes)
        if is_visible is not None:
            updates.append("is_visible=%s"); params.append(is_visible)
        if not updates:
            return
        params.append(self.id)
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(f"UPDATE elections SET {', '.join(updates)} WHERE id=%s", params)
        conn.commit()
        cur.close()

    def delete(self) -> None:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("DELETE FROM elections WHERE id=%s", (self.id,))
        conn.commit()
        cur.close()
