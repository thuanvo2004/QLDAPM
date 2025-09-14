from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Job, Application
from app.extensions import db
from app.forms import JobForm

employer_bp = Blueprint("employer", __name__, url_prefix="/employer")

@employer_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng mới xem dashboard", "danger")
        return redirect(url_for("job.list_jobs"))
    jobs = current_user.employer_profile.jobs
    return render_template("employer/dashboard.html")

@employer_bp.route("/job/<int:job_id>/applications")
@login_required
def view_applicants(job_id):
    job = Job.query.get_or_404(job_id)
    if current_user.role != "employer" or job.employer_id != current_user.employer_profile.id:
        flash("Không có quyền truy cập", "danger")
        return redirect(url_for("employer.dashboard"))
    applications = job.applications
    return render_template("employer/view_applications.html", job=job, applications=applications)

# ======================================================
# Sửa tin tuyển dụng
# ======================================================
@employer_bp.route("/job/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)

    # Chỉ owner mới sửa được
    if job.employer_id != current_user.employer_profile.id:
        flash("Bạn không có quyền sửa công việc này", "danger")
        return redirect(url_for("employer.dashboard"))

    form = JobForm(obj=job)  # load dữ liệu sẵn vào form
    if form.validate_on_submit():
        # cập nhật dữ liệu từ form
        job.title = form.title.data
        job.description = form.description.data
        job.requirements = form.requirements.data
        job.benefits = form.benefits.data
        job.job_type = form.job_type.data
        job.salary_min = form.salary_min.data
        job.salary_max = form.salary_max.data
        job.currency = form.currency.data
        job.city = form.city.data
        job.district = form.district.data
        job.street_address = form.street_address.data
        job.work_start_time = form.work_start_time.data
        job.work_end_time = form.work_end_time.data
        job.working_days = form.working_days.data
        job.deadline = form.deadline.data
        job.remote_option = form.remote_option.data
        job.interview_date = form.interview_date.data

        db.session.commit()
        flash("Cập nhật công việc thành công", "success")
        return redirect(url_for("employer.dashboard"))

    return render_template("jobs/edit_job.html", form=form, job=job)


# ======================================================
# Xóa tin tuyển dụng
# ======================================================
@employer_bp.route("/job/<int:job_id>/delete", methods=["POST"])
@login_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)

    # Chỉ owner mới xóa được
    if job.employer_id != current_user.employer_profile.id:
        flash("Bạn không có quyền xóa công việc này", "danger")
        return redirect(url_for("employer.dashboard"))

    db.session.delete(job)
    db.session.commit()
    flash("Xóa công việc thành công", "success")
    return redirect(url_for("employer.dashboard"))