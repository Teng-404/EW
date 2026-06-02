"""
models/candidate.py — Candidate model

ผู้สมัครแต่ละคนผูกกับวาระ (election_id)
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
        # vote_count อาจถูก join มาจาก query พิเศษ
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
        """คืนผู้สมัครทั้งหมดในวาระ เรียงตามหมายเลข"""
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
        """คืนผู้สมัครพร้อม vote_count — ใช้แสดงผลคะแนน"""
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
            (election_id, name, party, bio, photo_url, number),
        )
        conn.commit()
        cid = cur.lastrowid
        cur.close()
        return cls.get_by_id(cid)

    def update(self, name: str, party: str, bio: str, number: int = None) -> None:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            """
            UPDATE candidates
            SET name = %s, party = %s, bio = %s, number = %s
            WHERE id = %s
            """,
            (name, party, bio, number, self.id),
        )
        conn.commit()
        cur.close()
        self.name   = name
        self.party  = party
        self.bio    = bio
        self.number = number

    def delete(self) -> None:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("DELETE FROM candidates WHERE id = %s", (self.id,))
        conn.commit()
        cur.close()
