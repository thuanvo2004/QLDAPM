import uuid
from datetime import date

import cloudinary
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models import Job, Application, SavedJob, Candidate
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
import os

from app.routes.cv_routes import CVHistory

candidate_bp = Blueprint("candidate", __name__, url_prefix="/candidate")


class CsrfForm(FlaskForm):
    pass


@candidate_bp.route("/profile")
@login_required
def profile():
    if current_user.role != "candidate":
        flash("Chỉ ứng viên mới xem profile này", "danger")
        return redirect(url_for("job.list_jobs"))

    candidate = (
        Candidate.query
        .options(joinedload(Candidate.cvs))
        .filter_by(id=current_user.candidate_profile.id)
        .first()
    )
    form = CsrfForm()  # Instantiate CSRF form
    return render_template("candidate/profile.html", candidate=candidate, users=current_user, form=form)

@candidate_bp.route("/apply/<int:job_id>", methods=["GET", "POST"])
@login_required
def apply_job(job_id):
    job = Job.query.get_or_404(job_id)
    now = date.today()
    job.is_active = (job.deadline is None) or (job.deadline >= now)

    if current_user.role != "candidate":
        flash("Chỉ ứng viên mới nộp hồ sơ", "danger")
        return redirect(url_for("job.list_jobs"))

    if not job.is_active:
        flash("Công việc này đã hết hạn, không thể ứng tuyển.", "danger")
        return redirect(url_for("job.list_jobs"))

    existing = Application.query.filter_by(candidate_id=current_user.candidate_profile.id, job_id=job.id).first()
    if existing:
        flash("Bạn đã nộp hồ sơ trước đó", "warning")
        return redirect(url_for("job.job_detail", job_id=job.id))

    if request.method == "GET":
        cvs = CVHistory.query.filter_by(candidate_id=current_user.candidate_profile.id).all()
        return render_template("candidate/apply_job.html", job=job, cvs=cvs)

    cv_id = request.form.get("cv_id")
    uploaded_cv = request.files.get("cv_upload")

    if not cv_id and not uploaded_cv:
        flash("Vui lòng chọn hoặc tải lên CV", "danger")
        return redirect(url_for("candidate.apply_job", job_id=job.id))

    cv = None
    if cv_id:
        cv = CVHistory.query.get_or_404(cv_id)
        if cv.candidate_id != current_user.candidate_profile.id:
            flash("Không có quyền sử dụng CV này", "danger")
            return redirect(url_for("candidate.apply_job", job_id=job.id))
    elif uploaded_cv and uploaded_cv.filename:
        filename = secure_filename(uploaded_cv.filename)
        try:
            result = cloudinary.uploader.upload(
                uploaded_cv,
                resource_type="raw",
                public_id=f'cv_{current_user.id}_{uuid.uuid4().hex}',
            )
            cv = CVHistory(
                candidate_id=current_user.candidate_profile.id,
                cv_name=filename.rsplit('.', 1)[0],
                filename=result['public_id'],
                public_url=result['secure_url'],
                template=None
            )
            db.session.add(cv)
            db.session.commit()
        except Exception as e:
            current_app.logger.exception("CV upload failed: %s", str(e))
            flash(f"Tải CV thất bại: {str(e)}", "danger")
            return redirect(url_for("candidate.apply_job", job_id=job.id))

    application = Application(
        candidate_id=current_user.candidate_profile.id,
        job_id=job.id,
        cv_id=cv.id if cv else None
    )
    db.session.add(application)
    db.session.commit()
    flash("Ứng tuyển thành công", "success")
    return redirect(url_for("candidate.applications"))

@candidate_bp.route("/saved_jobs")
@login_required
def saved_jobs():
    if current_user.role != "candidate":
        flash("Chỉ ứng viên mới xem công việc đã lưu", "danger")
        return redirect(url_for("job.list_jobs"))

    saved_jobs = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id) \
        .order_by(SavedJob.saved_at.desc()).all()
    return render_template("candidate/saved_jobs.html", saved_jobs=saved_jobs)


@candidate_bp.route("/applications")
@login_required
def applications():
    apps = Application.query.filter_by(candidate_id=current_user.candidate_profile.id).all()
    return render_template("candidate/applications.html", applications=apps)


@candidate_bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    candidate = current_user.candidate_profile

    if request.method == "POST":
        candidate.name = request.form.get("name")
        candidate.phone = request.form.get("phone")
        candidate.address = request.form.get("address")
        candidate.skills = request.form.get("skills")
        candidate.experience = request.form.get("experience")
        candidate.bio = request.form.get("bio")

        if "avatar" in request.files:
            file = request.files["avatar"]
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                upload_path = os.path.join("app", "static", "Uploads", filename)
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
        return jsonify({'success': True, 'message': 'Lưu công việc thành công', 'action': 'saved'})
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
        return jsonify({'success': True, 'message': 'Bỏ lưu công việc thành công', 'action': 'unsaved'})
    flash("Bỏ lưu công việc thành công", "success")
    return redirect(url_for("candidate.saved_jobs"))


@candidate_bp.route("/check_saved/<int:job_id>", methods=["GET"])
@login_required
def check_saved(job_id):
    if current_user.role != "candidate":
        return jsonify({"success": False, "is_saved": False, "message": "Chỉ ứng viên mới dùng chức năng này"}), 403

    saved = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id, job_id=job_id).first()
    return jsonify({"success": True, "is_saved": bool(saved)})


@candidate_bp.route("/upload_avatar", methods=["POST"])
@login_required
def upload_avatar():
    if current_user.role != "candidate":
        return jsonify({"success": False, "message": "Chỉ ứng viên mới upload ảnh"}), 403

    if "avatar" not in request.files:
        return jsonify({"success": False, "message": "Không tìm thấy file"}), 400

    file = request.files["avatar"]
    if file.filename == "":
        return jsonify({"success": False, "message": "Tên file trống"}), 400

    filename = secure_filename(file.filename)
    upload_path = os.path.join("app", "static", "Uploads", filename)
    file.save(upload_path)

    candidate = current_user.candidate_profile
    candidate.avatar = filename
    db.session.commit()

    return jsonify({"success": True, "message": "Upload thành công", "filename": filename})