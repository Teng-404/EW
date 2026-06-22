"""
routes/auth.py — Authentication Blueprint  (patched)

GET/POST /login        — เข้าสู่ระบบ (รองรับ login ด้วย username หรือ email)
GET/POST /register     — สมัครสมาชิก
GET      /logout       — ออกจากระบบ

หมายเหตุการแก้ไข:
  - ลบ /request-otp/<id> และ /verify-otp ออก
    เดิมเป็น OTP flow แบบ user-based ที่อ้างถึง endpoint ที่ไม่มีจริง
    (vote.cast_vote, vote.results(election_id=...), current_user.has_voted)
    flow การยืนยัน OTP จริงอยู่ใน verify_bp (ยืนยันตัวตน) + vote_bp (ลงคะแนน)
    แบบ member-based ทั้งหมดแล้ว — โค้ดเก่าจึงเป็น dead code ที่ทำให้สับสน
  - หากมีไฟล์ templates/auth/verify_otp.html ค้างอยู่ สามารถลบทิ้งได้
    (ไม่มี route ใดเรนเดอร์อีกต่อไป)
  - login() รองรับการกรอกได้ทั้ง "ชื่อผู้ใช้" หรือ "อีเมล"
    เพราะผู้ใช้ที่นำเข้าจาก Excel จะได้ username อัตโนมัติ จึงสะดวกกว่า
    หากให้ใช้อีเมลล็อกอินได้ด้วย (ช่องในหน้า login ยังชื่อ username เหมือนเดิม)
"""

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session,
)
from flask_login import login_user, logout_user, login_required, current_user

from models.user import User

auth_bp = Blueprint("auth", __name__)


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

        # รองรับล็อกอินด้วย username หรือ email
        user = User.get_by_username(username)
        if not user:
            user = User.get_by_email(username.lower())

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
