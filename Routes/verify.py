"""
routes/verify.py — Verify Identity Blueprint  (ขั้นที่ 1)

GET/POST  /verify              — กรอก Email / ชื่อ เพื่อขอ OTP
POST      /verify/request-otp  — ส่ง OTP ไปยัง Email
GET/POST  /verify/otp          — กรอก OTP ยืนยันตัวตน
"""

import smtplib
from email.mime.text import MIMEText

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, current_app,
)

from models.member         import Member
from models.vote           import OTP
from models.system_setting import SystemSetting
from models.access_log     import AccessLog

verify_bp = Blueprint("verify", __name__)


# ── Helpers ────────────────────────────────────────────────

def _send_otp_email(to_email: str, code: str, purpose: str = "verify") -> None:
    cfg = current_app.config
    if not cfg.get("MAIL_USERNAME"):
        current_app.logger.warning(f"[DEV] OTP ({purpose}) for {to_email}: {code}")
        return

    subject = "[Election Web] รหัส OTP ยืนยันตัวตน"
    body    = (
        f"รหัส OTP ของคุณสำหรับการยืนยันตัวตน: {code}\n\n"
        "รหัสนี้จะหมดอายุใน 5 นาที"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"]    = cfg["MAIL_USERNAME"]
    msg["To"]      = to_email

    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as smtp:
            if cfg.get("MAIL_USE_TLS"):
                smtp.starttls()
            smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            smtp.sendmail(cfg["MAIL_USERNAME"], to_email, msg.as_string())
    except Exception as e:
        current_app.logger.error(f"ส่ง OTP ล้มเหลว: {e}")
        raise


def _client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")


# ── Step 1: ยืนยันตัวตน ────────────────────────────────────

@verify_bp.route("/verify", methods=["GET", "POST"])
def verify_identity():
    if not SystemSetting.is_enabled("verify_enabled"):
        flash("ยังไม่เปิดให้ใช้งานระบบยืนยันตัวตน", "warning")
        return render_template("verify_identity.html", disabled=True)

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        email_in = request.form.get("email_new", "").strip().lower()  # ถ้าต้องการเปลี่ยน

        if not email:
            flash("กรุณากรอก Email", "danger")
            return render_template("verify_identity.html")

        member = Member.get_by_email(email)
        if not member:
            flash("ไม่พบข้อมูลสมาชิกในระบบ กรุณาติดต่อเจ้าหน้าที่", "danger")
            return render_template("verify_identity.html")

        if member.verified:
            flash("บัญชีนี้ยืนยันตัวตนไปแล้ว", "info")
            return redirect(url_for("vote.request_otp"))

        # เก็บ member_id ใน session
        session["verify_member_id"] = member.id
        session["verify_email_new"] = email_in or None

        # ส่ง OTP
        send_to = email_in or email
        try:
            code = OTP.create_for_member(member.id, purpose="verify")
            _send_otp_email(send_to, code, purpose="verify")
            AccessLog.log("request_verify_otp", _client_ip(), "verify", member.id)
            flash(f"ส่ง OTP ไปยัง {send_to} แล้ว", "success")
        except Exception:
            flash("ส่ง OTP ล้มเหลว กรุณาลองใหม่", "danger")
            return render_template("verify_identity.html")

        return redirect(url_for("verify.verify_otp"))

    return render_template("verify_identity.html")


# ── Step 1b: กรอก OTP ยืนยันตัวตน ─────────────────────────

@verify_bp.route("/verify/otp", methods=["GET", "POST"])
def verify_otp():
    member_id = session.get("verify_member_id")
    if not member_id:
        flash("กรุณาเริ่มต้นยืนยันตัวตนใหม่", "warning")
        return redirect(url_for("verify.verify_identity"))

    if request.method == "POST":
        code = request.form.get("otp", "").strip()

        if OTP.verify_for_member(member_id, code, purpose="verify"):
            member    = Member.get_by_id(member_id)
            email_new = session.pop("verify_email_new", None)
            member.mark_verified(email_new)
            session.pop("verify_member_id", None)
            AccessLog.log("verified_identity", _client_ip(), "verify", member.id)
            flash("ยืนยันตัวตนสำเร็จ! คุณสามารถลงคะแนนได้แล้ว", "success")
            return redirect(url_for("vote.request_otp"))
        else:
            AccessLog.log("verify_otp_failed", _client_ip(), "verify", member_id)
            flash("รหัส OTP ไม่ถูกต้องหรือหมดอายุ", "danger")

    return render_template("verify_otp.html", purpose="verify")
