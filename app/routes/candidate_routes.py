from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Job, Application, SavedJob
from werkzeug.utils import secure_filename
candidate_bp = Blueprint("candidate", __name__, url_prefix="/candidate")
import os

@candidate_bp.route("/profile")
@login_required
def profile():
    if current_user.role != "candidate":
        flash("Chỉ ứng viên mới xem profile này", "danger")
        return redirect(url_for("job.list_jobs"))
    return render_template("candidate/profile.html", candidate=current_user.candidate_profile)

@candidate_bp.route("/apply/<int:job_id>")
@login_required
def apply_job(job_id):
    job = Job.query.get_or_404(job_id)
    if current_user.role != "candidate":
        flash("Chỉ ứng viên mới nộp hồ sơ", "danger")
        return redirect(url_for("job.list_jobs"))
    existing = Application.query.filter_by(candidate_id=current_user.candidate_profile.id, job_id=job.id).first()
    if existing:
        flash("Bạn đã nộp hồ sơ trước đó", "warning")
        return redirect(url_for("job.job_detail", job_id=job.id))
    application = Application(candidate_id=current_user.candidate_profile.id, job_id=job.id)
    db.session.add(application)
    db.session.commit()
    flash("Ứng tuyển thành công", "success")
    return redirect(url_for("candidate.profile"))

@candidate_bp.route("/saved_jobs")
@login_required
def saved_jobs():
    if current_user.role != "candidate":
        flash("Chỉ ứng viên mới xem công việc đã lưu", "danger")
        return redirect(url_for("job.list_jobs"))

    # saved_jobs = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id).order_by(SavedJob.saved_at.desc()).all()
    # jobs = [sj.job for sj in current_user.candidate_profile.saved_jobs]

    saved_jobs = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id) \
        .order_by(SavedJob.saved_at.desc()).all()

    return render_template("candidate/saved_jobs.html", saved_jobs=saved_jobs)

@candidate_bp.route("/applications")
@login_required
def applications():
    apps = Application.query.filter_by(candidate_id=current_user.candidate_profile.id).all()
    return render_template("candidate/applications.html", applications=apps)

# Chỉnh sửa hồ sơ
@candidate_bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    candidate = current_user.candidate_profile

    if request.method == "POST":
        # Cập nhật thông tin cơ bản
        candidate.name = request.form.get("name")
        candidate.phone = request.form.get("phone")
        candidate.address = request.form.get("address")
        candidate.skills = request.form.get("skills")
        candidate.experience = request.form.get("experience")
        candidate.bio = request.form.get("bio")

        # Upload avatar nếu có
        if "avatar" in request.files:
            file = request.files["avatar"]
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                upload_path = os.path.join("app", "static", "uploads", filename)
                file.save(upload_path)
                candidate.avatar = filename

        db.session.commit()
        flash("Cập nhật hồ sơ thành công!", "success")
        return redirect(url_for("candidate.profile"))

    return render_template("candidate/edit_profile.html", candidate=candidate)

@candidate_bp.route("/save_job/<int:job_id>", methods=["POST"])
@login_required
def save_job(job_id):
    if current_user.role != "candidate":
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Chỉ ứng viên mới lưu công việc'}), 403
        flash("Chỉ ứng viên mới lưu công việc", "danger")
        return redirect(url_for("job.list_jobs"))

    job = Job.query.get_or_404(job_id)
    existing = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id, job_id=job.id).first()
    if existing:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Công việc đã được lưu trước đó'}), 400
        flash("Công việc đã được lưu trước đó", "warning")
        return redirect(request.referrer or url_for("main.index"))

    saved_job = SavedJob(candidate_id=current_user.candidate_profile.id, job_id=job.id)
    db.session.add(saved_job)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True,
                        'message': 'Lưu công việc thành công',
                        'action': 'saved'
        })
    flash("Lưu công việc thành công", "success")
    return redirect(request.referrer or url_for("main.index"))

@candidate_bp.route("/unsave_job/<int:job_id>", methods=["POST"])
@login_required
def unsave_job(job_id):
    if current_user.role != "candidate":
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Chỉ ứng viên mới bỏ lưu công việc'}), 403
        flash("Chỉ ứng viên mới bỏ lưu công việc", "danger")
        return redirect(url_for("job.list_jobs"))

    saved_job = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id, job_id=job_id).first()
    if not saved_job:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Công việc không được lưu trước đó'}), 400
        flash("Công việc không được lưu trước đó", "warning")
        return redirect(url_for("candidate.saved_jobs"))

    db.session.delete(saved_job)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True,
                        'message': 'Bỏ lưu công việc thành công',
                        'action': 'unsaved'})
    flash("Bỏ lưu công việc thành công", "success")
    return redirect(url_for("candidate.saved_jobs"))



@candidate_bp.route("/check_saved/<int:job_id>", methods=["GET"])
@login_required
def check_saved(job_id):
    if current_user.role != "candidate":
        return jsonify({"success": False, "is_saved": False, "message": "Chỉ ứng viên mới dùng chức năng này"}), 403

    saved = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id, job_id=job_id).first()
    return jsonify({"success": True, "is_saved": bool(saved)})