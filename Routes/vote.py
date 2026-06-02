"""
routes/vote.py — Vote Blueprint

GET  /                          — หน้าแรก (รายการวาระเลือกตั้ง)
GET  /vote/<election_id>        — หน้าลงคะแนน (ต้อง verify OTP ก่อน)
POST /vote/<election_id>        — บันทึกคะแนน
GET  /results/<election_id>     — ผลคะแนน
GET  /results/<election_id>/json — ผลคะแนน JSON (สำหรับ Chart.js realtime)
"""

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, jsonify,
)
from flask_login import login_required, current_user
from mysql.connector import IntegrityError

from models.election  import Election
from models.candidate import Candidate
from models.vote      import Vote

vote_bp = Blueprint("vote", __name__)


# ── หน้าแรก ────────────────────────────────────────────────

@vote_bp.route("/")
def index():
    elections = Election.get_all()
    voted_ids: set[int] = set()

    if current_user.is_authenticated:
        voted_ids = {e.id for e in elections if current_user.has_voted(e.id)}

    return render_template("index.html", elections=elections, voted_ids=voted_ids)


# ── ลงคะแนน ────────────────────────────────────────────────

@vote_bp.route("/vote/<int:election_id>", methods=["GET", "POST"])
@login_required
def cast_vote(election_id: int):
    election = Election.get_by_id(election_id)

    # ── Guard: election ต้องมีและเปิดอยู่ ──────────────────
    if not election or not election.is_open:
        flash("การเลือกตั้งนี้ไม่ได้เปิดรับการลงคะแนน", "warning")
        return redirect(url_for("vote.index"))

    # ── Guard: ต้อง verify OTP ก่อน ────────────────────────
    if session.get("otp_verified_election") != election_id:
        flash("กรุณายืนยัน OTP ก่อนลงคะแนน", "warning")
        return redirect(url_for("auth.request_otp", election_id=election_id))

    # ── Guard: vote ซ้ำ ─────────────────────────────────────
    if current_user.has_voted(election_id):
        flash("คุณได้ลงคะแนนในวาระนี้แล้ว", "info")
        session.pop("otp_verified_election", None)
        return redirect(url_for("vote.results", election_id=election_id))

    candidates = Candidate.get_by_election(election_id)

    if request.method == "POST":
        candidate_id = request.form.get("candidate_id", type=int)

        if not candidate_id:
            flash("กรุณาเลือกผู้สมัคร", "danger")
            return render_template("vote.html", election=election, candidates=candidates)

        # ตรวจว่า candidate อยู่ในวาระนี้จริง
        valid_ids = {c.id for c in candidates}
        if candidate_id not in valid_ids:
            flash("ผู้สมัครไม่ถูกต้อง", "danger")
            return render_template("vote.html", election=election, candidates=candidates)

        try:
            Vote.cast(current_user.id, candidate_id, election_id)
            session.pop("otp_verified_election", None)
            flash("ลงคะแนนสำเร็จ!", "success")
            return redirect(url_for("vote.results", election_id=election_id))
        except IntegrityError:
            flash("เกิดข้อผิดพลาด: คุณอาจลงคะแนนแล้ว", "danger")
            return redirect(url_for("vote.results", election_id=election_id))

    return render_template("vote.html", election=election, candidates=candidates)


# ── ผลคะแนน ────────────────────────────────────────────────

@vote_bp.route("/results/<int:election_id>")
def results(election_id: int):
    election = Election.get_by_id(election_id)
    if not election:
        flash("ไม่พบวาระการเลือกตั้งนี้", "danger")
        return redirect(url_for("vote.index"))

    candidates = Candidate.get_by_election_with_votes(election_id)
    total_votes = sum(c.vote_count for c in candidates)

    return render_template(
        "results.html",
        election=election,
        candidates=candidates,
        total_votes=total_votes,
    )


@vote_bp.route("/results/<int:election_id>/json")
def results_json(election_id: int):
    """JSON endpoint สำหรับ Chart.js polling realtime"""
    election = Election.get_by_id(election_id)
    if not election:
        return jsonify({"error": "not found"}), 404

    candidates = Candidate.get_by_election_with_votes(election_id)
    total = sum(c.vote_count for c in candidates)

    return jsonify({
        "election": {
            "id":     election.id,
            "title":  election.title,
            "status": election.status,
        },
        "total_votes": total,
        "candidates": [
            {
                "id":         c.id,
                "name":       c.name,
                "party":      c.party,
                "number":     c.number,
                "vote_count": c.vote_count,
                "percent":    round(c.vote_count / total * 100, 1) if total else 0,
            }
            for c in candidates
        ],
    })
