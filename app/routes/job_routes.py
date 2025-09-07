from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.forms import JobForm
from app.models import Job
from app.extensions import db

job_bp = Blueprint("job", __name__, url_prefix="/jobs")

# Đăng tin
@job_bp.route("/post", methods=["GET", "POST"])
@login_required
def post_job():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng được tạo job", "danger")
        return redirect(url_for("job.list_jobs"))

    form = JobForm()

    if form.validate_on_submit():
        try:
            job = Job(
                employer_id=current_user.employer_profile.id,
                title=form.title.data,
                description=form.description.data,
                requirements=form.requirements.data,
                benefits=form.benefits.data,
                job_type=form.job_type.data,
                salary_min=form.salary_min.data,
                salary_max=form.salary_max.data,
                currency=form.currency.data,
                city=form.city.data,
                district=form.district.data,
                street_address=form.street_address.data,
                work_start_time=form.work_start_time.data,
                work_end_time=form.work_end_time.data,
                working_days=form.working_days.data,
                deadline=form.deadline.data,
                remote_option=form.remote_option.data,
                interview_date=form.interview_date.data
            )
            db.session.add(job)
            db.session.commit()
            flash("Tin tuyển dụng đã được tạo thành công!", "success")
            return redirect(url_for("job.manage_jobs"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Lỗi khi lưu job")
            flash("Lỗi khi lưu dữ liệu: " + str(e), "danger")
    else:
        if request.method == "POST":
            for field, errs in form.errors.items():
                for err in errs:
                    flash(f"{field}: {err}", "danger")

    return render_template("jobs/post_job.html", form=form)

# Danh sách job (cho ứng viên)
@job_bp.route("/")
def list_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template("jobs/list_jobs.html", jobs=jobs)

# Chi tiết job
@job_bp.route("/<int:job_id>")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template("jobs/job_detail.html", job=job)

# Quản lý job của employer
@job_bp.route("/manage")
@login_required
def manage_jobs():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng được quản lý job", "danger")
        return redirect(url_for("job.list_jobs"))

    jobs = Job.query.filter_by(employer_id=current_user.employer_profile.id).all()
    return render_template("jobs/manage_jobs.html", jobs=jobs)
