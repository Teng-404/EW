"""
routes/admin.py — Admin Blueprint  (url_prefix="/admin")

GET  /admin/                              — dashboard
GET  /admin/elections                     — จัดการวาระ
POST /admin/elections/create              — สร้างวาระใหม่
POST /admin/elections/<id>/status         — เปิด/ปิดวาระ
POST /admin/elections/<id>/delete         — ลบวาระ
GET  /admin/elections/<id>/candidates     — รายการผู้สมัครในวาระ
POST /admin/elections/<id>/candidates/add — เพิ่มผู้สมัคร
POST /admin/candidates/<id>/edit          — แก้ไขผู้สมัคร
POST /admin/candidates/<id>/delete        — ลบผู้สมัคร
GET  /admin/elections/<id>/voters         — รายชื่อผู้ลงคะแนน
GET  /admin/elections/<id>/voters/export  — export Excel ผู้ลงคะแนน
GET  /admin/elections/<id>/results/export — export Excel ผลคะแนน
"""

import io
import functools
from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, send_file, abort,
)
from flask_login import login_required, current_user

from models.election  import Election
from models.candidate import Candidate
from models.vote      import Vote

admin_bp = Blueprint("admin", __name__)


# ── Guard decorator ────────────────────────────────────────

def admin_required(f):
    @functools.wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


# ── Dashboard ──────────────────────────────────────────────

@admin_bp.route("/")
@admin_required
def dashboard():
    elections = Election.get_all()
    stats = []
    for e in elections:
        candidates = Candidate.get_by_election_with_votes(e.id)
        total_votes = sum(c.vote_count for c in candidates)
        stats.append({
            "election":    e,
            "candidates":  len(candidates),
            "total_votes": total_votes,
        })
    return render_template("admin/dashboard.html", stats=stats)


# ── Elections — CRUD ───────────────────────────────────────

@admin_bp.route("/elections")
@admin_required
def elections():
    return render_template("admin/elections.html", elections=Election.get_all())


@admin_bp.route("/elections/create", methods=["POST"])
@admin_required
def create_election():
    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title:
        flash("กรุณาระบุชื่อวาระการเลือกตั้ง", "danger")
        return redirect(url_for("admin.elections"))

    Election.create(title, description, created_by=current_user.id)
    flash(f"สร้างวาระ '{title}' สำเร็จ", "success")
    return redirect(url_for("admin.elections"))


@admin_bp.route("/elections/<int:election_id>/status", methods=["POST"])
@admin_required
def set_election_status(election_id: int):
    election = Election.get_by_id(election_id)
    if not election:
        abort(404)

    new_status = request.form.get("status")
    try:
        election.set_status(new_status)
        flash(f"เปลี่ยนสถานะวาระเป็น '{new_status}' แล้ว", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("admin.elections"))


@admin_bp.route("/elections/<int:election_id>/delete", methods=["POST"])
@admin_required
def delete_election(election_id: int):
    election = Election.get_by_id(election_id)
    if not election:
        abort(404)

    election.delete()
    flash("ลบวาระการเลือกตั้งแล้ว", "info")
    return redirect(url_for("admin.elections"))


# ── Candidates — CRUD ──────────────────────────────────────

@admin_bp.route("/elections/<int:election_id>/candidates")
@admin_required
def manage_candidates(election_id: int):
    election   = Election.get_by_id(election_id)
    if not election:
        abort(404)
    candidates = Candidate.get_by_election(election_id)
    return render_template(
        "admin/candidates.html",
        election=election,
        candidates=candidates,
    )


@admin_bp.route("/elections/<int:election_id>/candidates/add", methods=["POST"])
@admin_required
def add_candidate(election_id: int):
    election = Election.get_by_id(election_id)
    if not election:
        abort(404)

    name      = request.form.get("name", "").strip()
    party     = request.form.get("party", "").strip()
    bio       = request.form.get("bio", "").strip()
    photo_url = request.form.get("photo_url", "").strip()
    number    = request.form.get("number", type=int)

    if not name:
        flash("กรุณาระบุชื่อผู้สมัคร", "danger")
        return redirect(url_for("admin.manage_candidates", election_id=election_id))

    Candidate.create(election_id, name, party, bio, photo_url, number)
    flash(f"เพิ่มผู้สมัคร '{name}' สำเร็จ", "success")
    return redirect(url_for("admin.manage_candidates", election_id=election_id))


@admin_bp.route("/candidates/<int:candidate_id>/edit", methods=["POST"])
@admin_required
def edit_candidate(candidate_id: int):
    candidate = Candidate.get_by_id(candidate_id)
    if not candidate:
        abort(404)

    name   = request.form.get("name", "").strip()
    party  = request.form.get("party", "").strip()
    bio    = request.form.get("bio", "").strip()
    number = request.form.get("number", type=int)

    if not name:
        flash("กรุณาระบุชื่อผู้สมัคร", "danger")
        return redirect(url_for("admin.manage_candidates", election_id=candidate.election_id))

    candidate.update(name, party, bio, number)
    flash("แก้ไขข้อมูลผู้สมัครแล้ว", "success")
    return redirect(url_for("admin.manage_candidates", election_id=candidate.election_id))


@admin_bp.route("/candidates/<int:candidate_id>/delete", methods=["POST"])
@admin_required
def delete_candidate(candidate_id: int):
    candidate = Candidate.get_by_id(candidate_id)
    if not candidate:
        abort(404)

    election_id = candidate.election_id
    candidate.delete()
    flash("ลบผู้สมัครแล้ว", "info")
    return redirect(url_for("admin.manage_candidates", election_id=election_id))


# ── Voters list ────────────────────────────────────────────

@admin_bp.route("/elections/<int:election_id>/voters")
@admin_required
def voters(election_id: int):
    election = Election.get_by_id(election_id)
    if not election:
        abort(404)
    voter_list = Vote.get_voters_by_election(election_id)
    return render_template(
        "admin/voters.html",
        election=election,
        voters=voter_list,
    )


# ── Export Excel ───────────────────────────────────────────

def _make_xlsx(ws_title: str, headers: list, rows: list, col_widths: list) -> io.BytesIO:
    """Helper สร้าง Excel workbook และคืน BytesIO"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = ws_title

    header_fill = PatternFill("solid", fgColor="1F3A5F")
    header_font = Font(color="FFFFFF", bold=True)

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill      = header_fill
        cell.font      = header_font
        cell.alignment = Alignment(horizontal="center")

    for r_idx, row in enumerate(rows, 2):
        for c_idx, val in enumerate(row, 1):
            ws.cell(row=r_idx, column=c_idx, value=val)

    from openpyxl.utils import get_column_letter
    for i, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


@admin_bp.route("/elections/<int:election_id>/voters/export")
@admin_required
def export_voters(election_id: int):
    election = Election.get_by_id(election_id)
    if not election:
        abort(404)

    voter_list = Vote.get_voters_by_election(election_id)
    rows = [
        (i + 1, v["full_name"], v["username"], v["voted_at"].strftime("%d/%m/%Y %H:%M:%S"))
        for i, v in enumerate(voter_list)
    ]

    buf = _make_xlsx(
        ws_title="ผู้ลงคะแนน",
        headers=["ลำดับ", "ชื่อ-นามสกุล", "ชื่อผู้ใช้", "เวลาที่ลงคะแนน"],
        rows=rows,
        col_widths=[8, 30, 20, 22],
    )
    filename = f"voters_{election_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@admin_bp.route("/elections/<int:election_id>/results/export")
@admin_required
def export_results(election_id: int):
    election = Election.get_by_id(election_id)
    if not election:
        abort(404)

    candidates  = Candidate.get_by_election_with_votes(election_id)
    total_votes = sum(c.vote_count for c in candidates)

    rows = [
        (
            c.number,
            c.name,
            c.party or "",
            c.vote_count,
            f"{round(c.vote_count / total_votes * 100, 1)}%" if total_votes else "0%",
        )
        for c in candidates
    ]

    buf = _make_xlsx(
        ws_title="ผลคะแนน",
        headers=["หมายเลข", "ชื่อ", "พรรค/กลุ่ม", "คะแนน", "เปอร์เซ็นต์"],
        rows=rows,
        col_widths=[10, 30, 25, 12, 12],
    )
    filename = f"results_{election_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


# ── 403 handler ────────────────────────────────────────────

@admin_bp.errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403
