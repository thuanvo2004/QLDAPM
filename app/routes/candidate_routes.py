from flask import Blueprint, render_template, redirect, url_for, flash, request
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
    jobs = [sj.job for sj in current_user.candidate_profile.saved_jobs]
    return render_template("candidate/saved_jobs.html", jobs=jobs)



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