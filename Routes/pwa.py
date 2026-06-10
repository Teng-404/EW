"""
pwa.py — Progressive Web App blueprint สำหรับ Election Web

หน้าที่:
  • /sw.js          เสิร์ฟ service worker จาก root scope (จำเป็น —
                    SW ที่อยู่ใต้ /static/ จะคุมได้แค่ /static/ เท่านั้น)
  • /offline        หน้า fallback เมื่อผู้ใช้ออฟไลน์
  • (manifest.webmanifest เสิร์ฟเป็น static ปกติผ่าน url_for ใน <head>)

วิธีติดตั้ง (ในไฟล์สร้างแอพ เช่น app.py / __init__.py):

    from pwa import pwa_bp
    app.register_blueprint(pwa_bp)

จากนั้นเพิ่ม {% include '_pwa_head.html' %} ลงใน <head> ของ
base.html และหน้า auth ที่ไม่ extends base.html (login/register/verify_otp)
"""

import os

from flask import Blueprint, send_from_directory, render_template, current_app, make_response

pwa_bp = Blueprint("pwa", __name__)


@pwa_bp.route("/sw.js")
def service_worker():
    """
    ต้องเสิร์ฟจาก root '/' เพื่อให้ service worker คุมได้ทั้งเว็บ
    ตัวไฟล์เก็บไว้ใน static/js/ แต่ URL ที่เสิร์ฟยังเป็น /sw.js (scope = ทั้งเว็บ)
    """
    resp = make_response(send_from_directory(os.path.join(current_app.static_folder, "js"), "sw.js"))
    resp.headers["Content-Type"] = "application/javascript; charset=utf-8"
    resp.headers["Service-Worker-Allowed"] = "/"
    # ห้าม browser แคช service worker นาน ๆ ไม่งั้นอัปเดตยาก
    resp.headers["Cache-Control"] = "no-cache, max-age=0"
    return resp


@pwa_bp.route("/offline")
def offline():
    """หน้าแสดงเมื่อออฟไลน์ (ถูก precache โดย service worker)"""
    return render_template("offline.html")
