"""
db.py — MySQL connection helper

ใช้ connection pooling เพื่อไม่ต้อง connect/disconnect ทุก request
วิธีใช้:
    from db import get_db, close_db
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
"""

import mysql.connector
from mysql.connector import pooling
from flask import g
from config import ActiveConfig

_pool: pooling.MySQLConnectionPool | None = None


def init_pool() -> None:
    """สร้าง connection pool ตอน app เริ่ม (เรียกใน create_app)"""
    global _pool
    _pool = pooling.MySQLConnectionPool(
        pool_name="ew_pool",
        pool_size=10,
        pool_reset_session=True,
        **ActiveConfig.get_db_config(),
    )


def get_db():
    """
    คืน connection จาก pool และผูกไว้กับ Flask request context (g)
    ทำให้ใน 1 request ได้ connection เดิมตลอด
    """
    if "db" not in g:
        if _pool is None:
            raise RuntimeError("DB pool ยังไม่ถูก init — เรียก init_pool() ก่อน")
        g.db = _pool.get_connection()
    return g.db


def close_db(e=None) -> None:
    """คืน connection กลับ pool เมื่อ request จบ (ลงทะเบียนใน create_app)"""
    db = g.pop("db", None)
    if db is not None and db.is_connected():
        db.close()
