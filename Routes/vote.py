"""
routes/vote.py — Vote Blueprint  (README v3)

GET/POST  /vote                       — ขอ OTP ก่อนลงคะแนน (ต้องล็อกอินก่อน)
GET/POST  /vote/otp                   — กรอก OTP
GET       /vote/ballot                — (compat) เด้งกลับหน้าแรก
GET       /vote/ballot/<id>           — รายชื่อผู้สมัครของวาระ
POST      /vote/ballot/<id>/submit    — บันทึกคะแนน
GET       /results                    — ผลคะแนน Realtime (ทุกประเภท)
GET       /results/json               — JSON สำหรับ Chart.js

หมายเหตุความลับ/ความโปร่งใส:
  - ตรวจการมาใช้สิทธิ + กันลงคะแนนซ้ำ → ใช้ Turnout (เก็บ member_id จริง)
  - บันทึกผลการลงคะแนน               → ใช้ Vote.cast_secret (ไม่ผูกกับผู้ลงคะแนน)

หมายเหตุ OTP (ปรับใหม่):
  - 1 OTP = ลงคะแนนได้ 1 ครั้ง — ใช้ flag session["vote_authorized"]
    ตั้งค่าเมื่อยืนยัน OTP สำเร็จ และถูกล้างทันทีหลังลงคะแนนสำเร็จ
  - session["vote_member_id"] เก็บ "ตัวตน" คงไว้ (ใช้แสดงสถานะ/กันลงซ้ำ)
    แต่ลำพังตัวตนอย่างเดียวลงคะแนนไม่ได้ ต้องมี vote_authorized ด้วย
"""

import smtplib
from email.mime.text import MIMEText

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, jsonify, current_app,
)
from flask_login import current_user

from models.election       import Election, ELECTION_TYPES
from models.candidate      import Candidate
from models.member         import Member
from models.system_setting import SystemSetting
from models.access_log     import AccessLog
from models.vote           import OTP, Vote, Turnout

vote_bp = Blueprint("vote", __name__)


# ── หน้าแรก (เป็นเมนูลงคะแนนในตัว) ───────────────────────────

@vote_bp.route("/")
def index():
    elections = Election.get_all()

    # ตรวจว่าผู้ใช้ลงคะแนนวาระไหนไปแล้ว (ถ้าผ่าน OTP แล้ว)
    voted_ids = set()
    member    = None
    member_id = session.get("vote_member_id")
    if member_id:
        member    = Member.get_by_id(member_id)
        voted_ids = {e.id for e in elections if Turnout.has_voted(member_id, e.id)}

    return render_template(
        "index.html",
        elections=elections,
        voted_ids=voted_ids,
        member=member,
    )


# ── Helpers ────────────────────────────────────────────────

def _client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")


def _send_otp_email(to_email: str, code: str) -> None:
    cfg = current_app.config
    if not cfg.get("MAIL_USERNAME"):
        current_app.logger.warning(f"[DEV] OTP (vote) for {to_email}: {code}")
        return
    msg = MIMEText(
        f"รหัส OTP ของคุณสำหรับการลงคะแนน: {code}\n\nรหัสนี้จะหมดอายุใน 5 นาที",
        "plain", "utf-8",
    )
    msg["Subject"] = f"[Election Web] รหัส OTP ลงคะแนน: {code}"
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


def _login_guard():
    """ข้อ 1 — ต้องล็อกอินเข้าสู่ระบบก่อนเสมอ ไม่งั้นเด้งไปหน้าล็อกอิน"""
    if not current_user.is_authenticated:
        flash("กรุณาเข้าสู่ระบบก่อนลงคะแนน", "warning")
        return redirect(url_for("auth.login", next=url_for("vote.request_otp")))
    return None


def _ballot_guard():
    """ต้องล็อกอิน + ผ่าน OTP + ยังมีสิทธิ์ลงคะแนนที่ยังไม่ถูกใช้"""
    redir = _login_guard()
    if redir:
        return redir
    if not session.get("vote_member_id"):
        flash("กรุณายืนยัน OTP ก่อนลงคะแนน", "warning")
        return redirect(url_for("vote.request_otp"))
    # ★ OTP ก่อนหน้าถูกใช้ไปแล้ว — การลงคะแนนครั้งใหม่ต้องขอ OTP ใหม่
    if not session.get("vote_authorized"):
        flash("กรุณาขอ OTP ใหม่สำหรับการลงคะแนนครั้งนี้", "warning")
        return redirect(url_for("vote.request_otp"))
    return None


# ── Step 2a: ขอ OTP ลงคะแนน ───────────────────────────────

@vote_bp.route("/vote", methods=["GET", "POST"])
def request_otp():
    # ข้อ 1 — ยังไม่ล็อกอิน ให้เด้งไปหน้าล็อกอินก่อนเสมอ
    redir = _login_guard()
    if redir:
        return redir

    if not SystemSetting.is_enabled("vote_enabled"):
        flash("ยังไม่เปิดให้ใช้งานระบบลงคะแนน", "warning")
        return render_template("vote_request_otp.html", disabled=True)

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("กรุณากรอก Email", "danger")
            return render_template("vote_request_otp.html")

        # ค้นหาจาก members ก่อน ถ้าไม่เจอให้ลอง users แล้ว auto-create
        member = Member.get_by_email(email)
        if not member:
            from models.user import User
            user = User.get_by_email(email)
            if user:
                from db import get_db
                conn = get_db()
                cur  = conn.cursor(dictionary=True)
                cur.execute(
                    "INSERT INTO members (full_name, email, verified) VALUES (%s, %s, TRUE)",
                    (user.full_name, user.email),
                )
                conn.commit()
                member_id = cur.lastrowid
                cur.close()
                member = Member.get_by_id(member_id)
            else:
                flash("ไม่พบข้อมูลในระบบ กรุณาติดต่อเจ้าหน้าที่", "danger")
                return render_template("vote_request_otp.html")

        if not member.verified:
            flash("กรุณายืนยันตัวตนก่อน (ขั้นที่ 1) แล้วจึงลงคะแนน", "warning")
            return redirect(url_for("verify.verify_identity"))

        send_to = member.active_email
        try:
            code = OTP.create_for_member(member.id, purpose="vote")
            _send_otp_email(send_to, code)
            session["vote_pending_member_id"] = member.id
            AccessLog.log("request_vote_otp", _client_ip(), "vote", member.id)
            flash(f"ส่ง OTP ไปยัง {send_to} แล้ว", "success")
        except Exception:
            flash("ส่ง OTP ล้มเหลว กรุณาลองใหม่", "danger")
            return render_template("vote_request_otp.html")

        return redirect(url_for("vote.verify_otp"))

    return render_template("vote_request_otp.html")


# ── Step 2b: กรอก OTP ─────────────────────────────────────

@vote_bp.route("/vote/otp", methods=["GET", "POST"])
def verify_otp():
    redir = _login_guard()
    if redir:
        return redir

    member_id = session.get("vote_pending_member_id")
    if not member_id:
        flash("กรุณาขอ OTP ก่อน", "warning")
        return redirect(url_for("vote.request_otp"))

    if request.method == "POST":
        code = request.form.get("otp", "").strip()
        if OTP.verify_for_member(member_id, code, purpose="vote"):
            session.pop("vote_pending_member_id", None)
            session["vote_member_id"]  = member_id   # ตัวตน (คงไว้เพื่อแสดงสถานะ/กันซ้ำ)
            session["vote_authorized"] = True        # ★ สิทธิ์ลงคะแนน 1 ครั้งต่อ 1 OTP
            AccessLog.log("vote_otp_verified", _client_ip(), "vote", member_id)
            return redirect(url_for("vote.index"))
        else:
            AccessLog.log("vote_otp_failed", _client_ip(), "vote", member_id)
            flash("รหัส OTP ไม่ถูกต้องหรือหมดอายุ", "danger")

    return render_template("verify_otp.html", purpose="vote")


# ── Ballot: (compat) เด้งกลับหน้าแรก ──────────────────────
# ข้อ 3/4 — เลิกใช้ vote_ballot.html แล้ว หน้าแรก (index) ทำหน้าที่นี้แทน

@vote_bp.route("/vote/ballot")
def ballot():
    redir = _ballot_guard()
    if redir:
        return redir
    return redirect(url_for("vote.index"))


# ── Ballot: รายชื่อผู้สมัครของวาระ ────────────────────────

@vote_bp.route("/vote/ballot/<int:election_id>")
def ballot_detail(election_id: int):
    redir = _ballot_guard()
    if redir:
        return redir

    election = Election.get_by_id(election_id)
    if not election or not election.is_open:
        flash("วาระนี้ยังไม่เปิดรับลงคะแนน", "warning")
        return redirect(url_for("vote.index"))

    member_id = session["vote_member_id"]

    if Turnout.has_voted(member_id, election.id):
        flash("คุณได้ลงคะแนนวาระนี้แล้ว", "info")
        return redirect(url_for("vote.index"))

    candidates = Candidate.get_by_election(election.id)
    return render_template(
        "vote_detail.html",
        election=election,
        candidates=candidates,
        max_votes=election.max_votes,
    )


# ── Ballot: บันทึกคะแนน ────────────────────────────────────

@vote_bp.route("/vote/ballot/<int:election_id>/submit", methods=["POST"])
def ballot_submit(election_id: int):
    redir = _ballot_guard()
    if redir:
        return redir

    election = Election.get_by_id(election_id)
    if not election or not election.is_open:
        flash("วาระนี้ไม่ได้เปิดรับลงคะแนน", "warning")
        return redirect(url_for("vote.index"))

    member_id = session["vote_member_id"]

    if Turnout.has_voted(member_id, election.id):
        flash("คุณได้ลงคะแนนวาระนี้แล้ว", "info")
        return redirect(url_for("vote.index"))

    # รับ candidate_ids (รองรับ max_votes > 1)
    candidate_ids = request.form.getlist("candidate_id", type=int)
    if not candidate_ids:
        flash("กรุณาเลือกผู้สมัครอย่างน้อย 1 คน", "danger")
        return redirect(url_for("vote.ballot_detail", election_id=election_id))

    if len(candidate_ids) > election.max_votes:
        flash(f"เลือกได้ไม่เกิน {election.max_votes} คน", "danger")
        return redirect(url_for("vote.ballot_detail", election_id=election_id))

    valid_ids = {c.id for c in Candidate.get_by_election(election.id)}
    if not all(cid in valid_ids for cid in candidate_ids):
        flash("ผู้สมัครไม่ถูกต้อง", "danger")
        return redirect(url_for("vote.ballot_detail", election_id=election_id))

    try:
        # 1) บันทึกบัตรลงคะแนน (ลับ — ไม่ผูกกับผู้ลงคะแนน)
        for cid in candidate_ids:
            Vote.cast_secret(cid, election.id)
        # 2) บันทึกการมาใช้สิทธิ (ตรวจสอบได้ — กันลงคะแนนซ้ำ)
        Turnout.record(member_id, election.id)
        AccessLog.log(f"voted_{election.type}_{election.id}", _client_ip(), "vote", member_id)
        # 3) ★ ใช้สิทธิ์ OTP นี้แล้ว — วาระถัดไปต้องขอ OTP ใหม่
        session.pop("vote_authorized", None)
        flash("ลงคะแนนสำเร็จ!", "success")
    except Exception:
        flash("เกิดข้อผิดพลาด ไม่สามารถบันทึกคะแนนได้", "danger")

    return redirect(url_for("vote.index"))


# ── Results ────────────────────────────────────────────────

@vote_bp.route("/results")
def results():
    election_id = request.args.get("election", type=int)
    elections = Election.get_all()
    if election_id:
        elections = [e for e in elections if e.id == election_id]
    data = []
    for e in elections:
        candidates = Candidate.get_by_election_with_votes(e.id)
        total      = sum(c.vote_count for c in candidates)
        data.append({"election": e, "candidates": candidates, "total": total})
    return render_template("results.html", data=data)


@vote_bp.route("/results/json")
def results_json():
    elections = Election.get_all()
    out = []
    for e in elections:
        candidates = Candidate.get_by_election_with_votes(e.id)
        total      = sum(c.vote_count for c in candidates)
        out.append({
            "id":     e.id,
            "title":  e.title,
            "type":   e.type,
            "status": e.status,
            "total_votes": total,
            "candidates": [
                {
                    "id":         c.id,
                    "name":       c.name,
                    "number":     c.number,
                    "vote_count": c.vote_count,
                    "percent":    round(c.vote_count / total * 100, 1) if total else 0,
                }
                for c in candidates
            ],
        })
    return jsonify(out)
