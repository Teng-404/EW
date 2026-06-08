"""
models/candidate.py — Candidate model  (README v2 patch)

เปลี่ยนจากเดิม:
  - create()  — party และ bio มี default "" ทำให้เรียกแบบ keyword-only ได้
  - update()  — รับ photo_url เพิ่ม, party และ bio optional (default None = ไม่เปลี่ยน)
"""

from __future__ import annotations
from db import get_db


class Candidate:
    def __init__(self, row: dict):
        self.id          = row["id"]
        self.election_id = row["election_id"]
        self.name        = row["name"]
        self.party       = row.get("party")
        self.bio         = row.get("bio")
        self.photo_url   = row.get("photo_url")
        self.number      = row.get("number")
        self.created_at  = row.get("created_at")
        self.vote_count  = row.get("vote_count", 0)

    # ── Queries ────────────────────────────────────────────

    @classmethod
    def get_by_id(cls, candidate_id: int) -> "Candidate | None":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM candidates WHERE id = %s", (candidate_id,))
        row = cur.fetchone()
        cur.close()
        return cls(row) if row else None

    @classmethod
    def get_by_election(cls, election_id: int) -> list["Candidate"]:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM candidates WHERE election_id = %s ORDER BY number, id",
            (election_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    @classmethod
    def get_by_election_with_votes(cls, election_id: int) -> list["Candidate"]:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT c.*,
                   COUNT(v.id) AS vote_count
            FROM   candidates c
            LEFT JOIN votes v ON v.candidate_id = c.id
                             AND v.election_id  = c.election_id
            WHERE  c.election_id = %s
            GROUP  BY c.id
            ORDER  BY vote_count DESC, c.number, c.id
            """,
            (election_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return [cls(r) for r in rows]

    # ── Mutations ──────────────────────────────────────────

    @classmethod
    def create(
        cls,
        election_id: int,
        name: str,
        party: str = "",
        bio: str = "",
        photo_url: str = "",
        number: int = None,
    ) -> "Candidate":
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """
            INSERT INTO candidates (election_id, name, party, bio, photo_url, number)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (election_id, name, party or None, bio or None, photo_url or None, number),
        )
        conn.commit()
        cid = cur.lastrowid
        cur.close()
        return cls.get_by_id(cid)

    def update(
        self,
        name: str,
        party: str = None,
        bio: str = None,
        photo_url: str = None,
        number: int = None,
    ) -> None:
        """
        อัปเดตผู้สมัคร — ถ้า argument เป็น None จะคง value เดิมไว้
        เรียกได้ทั้ง update(name, party, bio, number)  ← backward compat
        และ update(name, photo_url=url, number=n)       ← รูปแบบใหม่
        """
        new_party     = party     if party     is not None else self.party
        new_bio       = bio       if bio       is not None else self.bio
        new_photo_url = photo_url if photo_url is not None else self.photo_url
        new_number    = number    if number    is not None else self.number

        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            """
            UPDATE candidates
            SET    name = %s, party = %s, bio = %s, photo_url = %s, number = %s
            WHERE  id = %s
            """,
            (name, new_party, new_bio, new_photo_url, new_number, self.id),
        )
        conn.commit()
        cur.close()
        self.name      = name
        self.party     = new_party
        self.bio       = new_bio
        self.photo_url = new_photo_url
        self.number    = new_number

    def delete(self) -> None:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("DELETE FROM candidates WHERE id = %s", (self.id,))
        conn.commit()
        cur.close()
