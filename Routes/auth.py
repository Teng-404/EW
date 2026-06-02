"""
routes/auth.py — Authentication Blueprint

GET/POST /login        — เข้าสู่ระบบ
GET/POST /register     — สมัครสมาชิก
GET      /logout       — ออกจากระบบ
GET/POST /verify-otp   — ยืนยัน OTP ก่อน vote
"""

import smtplib
from email.mime.text import MIMEText

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, current_app,
)
from flask_login import login_user, logout_user, login_required, current_user

from models.user import User
from models.vote import OTP

auth_bp = Blueprint("auth", __name__)


# ── Helpers ────────────────────────────────────────────────

def _send_otp_email(to_email: str, code: str) -> None:
    """ส่ง OTP ทาง email — ถ้าไม่มี MAIL_USERNAME ให้ print ใน dev"""
    cfg = current_app.config
    if not cfg.get("MAIL_USERNAME"):
        current_app.logger.warning(f"[DEV] OTP for {to_email}: {code}")
        return

    msg = MIMEText(
        f"รหัส OTP ของคุณสำหรับการลงคะแนน: {code}\n\nรหัสนี้จะหมดอายุใน 5 นาที",
        "plain",
        "utf-8",
    )
    msg["Subject"] = f"[Election Web] รหัส OTP: {code}"
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


# ── Register ───────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("vote.index"))

    if request.method == "POST":
        username  = request.form.get("username", "").strip()
        email     = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        password  = request.form.get("password", "")
        confirm   = request.form.get("confirm_password", "")

        # ── Validation ─────────────────────────────────────
        errors = []
        if not all([username, email, full_name, password]):
            errors.append("กรุณากรอกข้อมูลให้ครบทุกช่อง")
        if len(password) < 8:
            errors.append("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
        if password != confirm:
            errors.append("รหัสผ่านไม่ตรงกัน")
        if User.get_by_username(username):
            errors.append("ชื่อผู้ใช้นี้ถูกใช้แล้ว")
        if User.get_by_email(email):
            errors.append("อีเมลนี้ถูกใช้แล้ว")
        if User.exists_full_name(full_name):
            errors.append("ชื่อ-นามสกุลนี้มีในระบบแล้ว")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "auth/register.html",
                username=username, email=email, full_name=full_name,
            )

        user = User.create(username, email, password, full_name)
        login_user(user)
        flash("สมัครสมาชิกสำเร็จ ยินดีต้อนรับ!", "success")
        return redirect(url_for("vote.index"))

    return render_template("auth/register.html")


# ── Login ──────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("vote.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.get_by_username(username)
        if not user or not user.check_password(password):
            flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "danger")
            return render_template("auth/login.html", username=username)

        if not user.is_active:
            flash("บัญชีนี้ถูกระงับการใช้งาน", "danger")
            return render_template("auth/login.html", username=username)

        login_user(user, remember=remember)
        flash(f"ยินดีต้อนรับ, {user.full_name}!", "success")

        next_page = request.args.get("next")
        return redirect(next_page or url_for("vote.index"))

    return render_template("auth/login.html")


# ── Logout ─────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("ออกจากระบบแล้ว", "info")
    return redirect(url_for("auth.login"))


# ── OTP — ขอรหัส ───────────────────────────────────────────

@auth_bp.route("/request-otp/<int:election_id>")
@login_required
def request_otp(election_id: int):
    """สร้าง OTP และส่งให้ user — เรียกก่อนเข้าหน้า vote"""
    from models.election import Election

    election = Election.get_by_id(election_id)
    if not election or not election.is_open:
        flash("การเลือกตั้งนี้ไม่ได้เปิดรับการลงคะแนน", "warning")
        return redirect(url_for("vote.index"))

    if current_user.has_voted(election_id):
        flash("คุณได้ลงคะแนนในวาระนี้แล้ว", "info")
        return redirect(url_for("vote.results", election_id=election_id))

    code = OTP.create(current_user.id, purpose="vote")
    try:
        _send_otp_email(current_user.email, code)
        flash(f"ส่งรหัส OTP ไปยัง {current_user.email} แล้ว", "info")
    except Exception:
        flash("ส่ง OTP ไม่สำเร็จ กรุณาลองใหม่", "danger")
        return redirect(url_for("vote.index"))

    # เก็บ election_id ใน session เพื่อใช้ใน verify_otp
    session["otp_election_id"] = election_id
    return redirect(url_for("auth.verify_otp"))


# ── OTP — ยืนยันรหัส ───────────────────────────────────────

@auth_bp.route("/verify-otp", methods=["GET", "POST"])
@login_required
def verify_otp():
    election_id = session.get("otp_election_id")
    if not election_id:
        flash("ไม่พบข้อมูลการลงคะแนน กรุณาเริ่มใหม่", "warning")
        return redirect(url_for("vote.index"))

    if request.method == "POST":
        code = request.form.get("otp_code", "").strip()

        if OTP.verify(current_user.id, code, purpose="vote"):
            session["otp_verified_election"] = election_id
            session.pop("otp_election_id", None)
            return redirect(url_for("vote.cast_vote", election_id=election_id))

        flash("รหัส OTP ไม่ถูกต้องหรือหมดอายุแล้ว", "danger")

    return render_template("auth/verify_otp.html", election_id=election_id)
