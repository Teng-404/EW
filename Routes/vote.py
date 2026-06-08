"""
routes/vote.py — Vote Blueprint  (README v2)

GET/POST  /vote                       — ขอ OTP ก่อนลงคะแนน (ขั้นที่ 2)
POST      /vote/request-otp           — ส่ง OTP
GET/POST  /vote/otp                   — กรอก OTP
GET       /vote/ballot                — หน้าหลัก เมนูซ้าย
GET       /vote/ballot/<type>         — รายชื่อผู้สมัครตามประเภท
POST      /vote/ballot/<type>/submit  — บันทึกคะแนน
GET       /results                    — ผลคะแนน Realtime (ทุกประเภท)
GET       /results/json               — JSON สำหรับ Chart.js
"""

import hashlib
import smtplib
from email.mime.text import MIMEText

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, jsonify, current_app,
)

from models.election       import Election, ELECTION_TYPES
from models.candidate      import Candidate
from models.member         import Member
from models.system_setting import SystemSetting
from models.access_log     import AccessLog
from models.vote           import OTP, Vote

vote_bp = Blueprint("vote", __name__)


# ── หน้าแรก (compat — base.html และ auth.py ยัง url_for vote.index) ──

@vote_bp.route("/")
def index():
    elections = Election.get_all()
    return render_template("index.html", elections=elections)


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


def _member_hash(member_id: int) -> str:
    """เข้ารหัส member_id ก่อนบันทึกใน votes"""
    secret = current_app.config.get("SECRET_KEY", "secret")
    return hashlib.sha256(f"{secret}:{member_id}".encode()).hexdigest()


def _ballot_guard():
    """ตรวจ session vote_member_id — redirect ถ้าไม่ผ่าน OTP"""
    if not session.get("vote_member_id"):
        flash("กรุณายืนยัน OTP ก่อนลงคะแนน", "warning")
        return redirect(url_for("vote.request_otp"))
    return None


# ── Step 2a: ขอ OTP ลงคะแนน ───────────────────────────────

@vote_bp.route("/vote", methods=["GET", "POST"])
def request_otp():
    if not SystemSetting.is_enabled("vote_enabled"):
        flash("ยังไม่เปิดให้ใช้งานระบบลงคะแนน", "warning")
        return render_template("vote_request_otp.html", disabled=True)

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("กรุณากรอก Email", "danger")
            return render_template("vote_request_otp.html")

        member = Member.get_by_email(email)
        if not member:
            flash("ไม่พบข้อมูลสมาชิกในระบบ", "danger")
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
    member_id = session.get("vote_pending_member_id")
    if not member_id:
        flash("กรุณาขอ OTP ก่อน", "warning")
        return redirect(url_for("vote.request_otp"))

    if request.method == "POST":
        code = request.form.get("otp", "").strip()
        if OTP.verify_for_member(member_id, code, purpose="vote"):
            session.pop("vote_pending_member_id", None)
            session["vote_member_id"] = member_id
            AccessLog.log("vote_otp_verified", _client_ip(), "vote", member_id)
            return redirect(url_for("vote.ballot"))
        else:
            AccessLog.log("vote_otp_failed", _client_ip(), "vote", member_id)
            flash("รหัส OTP ไม่ถูกต้องหรือหมดอายุ", "danger")

    return render_template("verify_otp.html", purpose="vote")


# ── Ballot: หน้าหลัก เมนูซ้าย ─────────────────────────────

@vote_bp.route("/vote/ballot")
def ballot():
    redir = _ballot_guard()
    if redir:
        return redir

    member_id  = session["vote_member_id"]
    member     = Member.get_by_id(member_id)
    elections  = Election.get_visible_open()

    # ตรวจว่าลงคะแนนวาระไหนแล้ว
    member_hash = _member_hash(member_id)
    voted_types = {
        e.type for e in elections
        if Vote.has_voted(member_hash, e.id)
    }

    return render_template(
        "vote_ballot.html",
        elections=elections,
        voted_types=voted_types,
        member=member,
        ELECTION_TYPES=ELECTION_TYPES,
    )


# ── Ballot: รายชื่อผู้สมัครตามประเภท ─────────────────────

@vote_bp.route("/vote/ballot/<election_type>")
def ballot_detail(election_type: str):
    redir = _ballot_guard()
    if redir:
        return redir

    if election_type not in ELECTION_TYPES:
        flash("ประเภทวาระไม่ถูกต้อง", "danger")
        return redirect(url_for("vote.ballot"))

    election = Election.get_by_type(election_type)
    if not election or not election.is_open:
        flash("วาระนี้ยังไม่เปิดรับลงคะแนน", "warning")
        return redirect(url_for("vote.ballot"))

    member_id   = session["vote_member_id"]
    member_hash = _member_hash(member_id)

    if Vote.has_voted(member_hash, election.id):
        flash("คุณได้ลงคะแนนวาระนี้แล้ว", "info")
        return redirect(url_for("vote.ballot"))

    candidates = Candidate.get_by_election(election.id)
    return render_template(
        "vote_detail.html",
        election=election,
        candidates=candidates,
        max_votes=election.max_votes,
    )


# ── Ballot: บันทึกคะแนน ────────────────────────────────────

@vote_bp.route("/vote/ballot/<election_type>/submit", methods=["POST"])
def ballot_submit(election_type: str):
    redir = _ballot_guard()
    if redir:
        return redir

    election = Election.get_by_type(election_type)
    if not election or not election.is_open:
        flash("วาระนี้ไม่ได้เปิดรับลงคะแนน", "warning")
        return redirect(url_for("vote.ballot"))

    member_id   = session["vote_member_id"]
    member_hash = _member_hash(member_id)

    if Vote.has_voted(member_hash, election.id):
        flash("คุณได้ลงคะแนนวาระนี้แล้ว", "info")
        return redirect(url_for("vote.ballot"))

    # รับ candidate_ids (รองรับ max_votes > 1)
    candidate_ids = request.form.getlist("candidate_id", type=int)
    if not candidate_ids:
        flash("กรุณาเลือกผู้สมัครอย่างน้อย 1 คน", "danger")
        return redirect(url_for("vote.ballot_detail", election_type=election_type))

    if len(candidate_ids) > election.max_votes:
        flash(f"เลือกได้ไม่เกิน {election.max_votes} คน", "danger")
        return redirect(url_for("vote.ballot_detail", election_type=election_type))

    valid_ids = {c.id for c in Candidate.get_by_election(election.id)}
    if not all(cid in valid_ids for cid in candidate_ids):
        flash("ผู้สมัครไม่ถูกต้อง", "danger")
        return redirect(url_for("vote.ballot_detail", election_type=election_type))

    try:
        for cid in candidate_ids:
            Vote.cast_hashed(member_hash, cid, election.id)
        AccessLog.log(f"voted_{election_type}", _client_ip(), "vote", member_id)
        flash("ลงคะแนนสำเร็จ!", "success")
    except Exception:
        flash("เกิดข้อผิดพลาด ไม่สามารถบันทึกคะแนนได้", "danger")

    return redirect(url_for("vote.ballot"))


# ── Results ────────────────────────────────────────────────

@vote_bp.route("/results")
def results():
    elections = Election.get_all()
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
