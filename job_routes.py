from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models import db, Job, Application, SavedJob, Candidate, Employer

job_bp = Blueprint("job", __name__)
UPLOAD_FOLDER = "uploads/cv"


# =========================
# Danh sách việc làm
# =========================
@job_bp.route("/jobs")
def list_jobs():
    jobs = Job.query.filter_by(status="active").order_by(Job.id.desc()).all()
    return render_template("jobs.html", jobs=jobs)


# =========================
# Chi tiết việc làm
# =========================
@job_bp.route("/job/<int:id>")
def job_detail(id):
    job = Job.query.get_or_404(id)
    return render_template("job_detail.html", job=job)


# =========================
# Nhà tuyển dụng đăng tin
# =========================
@job_bp.route("/post_job", methods=["GET", "POST"])
@login_required
def post_job():
    if not isinstance(current_user, Employer):
        flash("❌ Chỉ nhà tuyển dụng mới có thể đăng tin.", "danger")
        return redirect(url_for("job.list_jobs"))

    if request.method == "POST":
        new_job = Job(
            employer_id=current_user.id,
            title=request.form["title"],
            location=request.form["location"],
            description=request.form["description"],
            salary=request.form["salary"],
            job_type=request.form["job_type"],
            status="active"  # mặc định active
        )
        db.session.add(new_job)
        db.session.commit()

        flash("✅ Tin tuyển dụng đã được đăng thành công!", "success")
        return redirect(url_for("job.list_jobs"))

    return render_template("post_job.html")


# =========================
# Ứng viên lưu tin
# =========================
@job_bp.route("/jobs/<int:job_id>/save")
@login_required
def save_job(job_id):
    if not isinstance(current_user, Candidate):
        flash("❌ Chỉ ứng viên mới có thể lưu tin.", "danger")
        return redirect(url_for("job.job_detail", id=job_id))

    saved = SavedJob.query.filter_by(candidate_id=current_user.id, job_id=job_id).first()
    if not saved:
        saved = SavedJob(candidate_id=current_user.id, job_id=job_id)
        db.session.add(saved)
        db.session.commit()
        flash("💾 Tin đã được lưu!", "success")
    else:
        flash("⚠️ Bạn đã lưu tin này rồi.", "warning")
    return redirect(url_for("job.job_detail", id=job_id))


# =========================
# Ứng viên ứng tuyển
# =========================
@job_bp.route("/jobs/<int:job_id>/apply", methods=["GET", "POST"])
@login_required
def apply_job(job_id):
    if not isinstance(current_user, Candidate):
        flash("❌ Chỉ ứng viên mới có thể ứng tuyển.", "danger")
        return redirect(url_for("job.job_detail", id=job_id))

    job = Job.query.get_or_404(job_id)

    if request.method == "POST":
        cv = request.files.get("cv_file")

        filename = None
        if cv:
            filename = secure_filename(cv.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            cv.save(os.path.join(UPLOAD_FOLDER, filename))

        application = Application(
            job_id=job.id,
            candidate_id=current_user.id,
            cv_file=filename
        )
        db.session.add(application)
        db.session.commit()
        flash("✅ Ứng tuyển thành công!", "success")
        return redirect(url_for("job.job_detail", id=job.id))

    return render_template("apply_job.html", job=job)
