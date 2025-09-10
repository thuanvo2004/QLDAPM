from flask import Blueprint, render_template, redirect, url_for, flash,current_app
from flask_login import login_required, current_user
from app.models import Job, Application
from app.extensions import db
from app.forms import JobForm,EmployerProfileForm
from datetime import datetime

employer_bp = Blueprint("employer", __name__, url_prefix="/employer")

@employer_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng mới xem dashboard", "danger")
        return redirect(url_for("job.list_jobs"))
    jobs = current_user.employer_profile.jobs
    return render_template("employer/dashboard.html", jobs=jobs)

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


def _save_logo_file(file_storage, employer_id):
    """Lưu file logo vào static/uploads/employers/<employer_id>/"""
    filename = f"{int(time.time())}_{secure_filename(file_storage.filename)}"
    upload_folder = os.path.join(current_app.root_path, "static", "uploads", "employers", str(employer_id))
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file_storage.save(filepath)
    return f"/static/uploads/employers/{employer_id}/{filename}"


# ----------------------
# Xem profile
# ----------------------
@employer_bp.route("/profile")
@login_required
def profile():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng mới truy cập hồ sơ này", "danger")
        return redirect(url_for("main.index"))

    employer = current_user.employer_profile
    if not employer:
        flash("Bạn chưa có hồ sơ công ty. Vui lòng tạo hồ sơ.", "warning")
        return redirect(url_for("employer.edit_profile"))

    return render_template("employer/profile.html", employer=employer)


# ----------------------
# Chỉnh sửa profile
# ----------------------
@employer_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng mới truy cập hồ sơ này", "danger")
        return redirect(url_for("main.index"))

    employer = current_user.employer_profile
    if not employer:
        # tạo mới profile nếu chưa có
        employer = Employer(user_id=current_user.id, company_name="")
        db.session.add(employer)
        db.session.commit()  # để có employer.id cho lưu logo

    form = EmployerProfileForm(obj=employer)

    if form.validate_on_submit():
        # cập nhật thông tin
        employer.company_name = form.company_name.data
        employer.phone = form.phone.data
        employer.industry = form.industry.data
        employer.company_size = form.company_size.data
        employer.address = form.address.data
        employer.city = form.city.data
        employer.website = form.website.data
        employer.description = form.description.data
        employer.founded_year = form.founded_year.data
        employer.tax_code = form.tax_code.data
        employer.updated_at = datetime.utcnow()

        # xử lý logo nếu upload
        if form.logo.data:
            try:
                logo_path = _save_logo_file(form.logo.data, employer.id)
                employer.logo = logo_path
            except Exception as e:
                current_app.logger.exception("Lỗi khi lưu logo")
                flash("Lưu logo thất bại.", "warning")

        db.session.commit()
        flash("Cập nhật hồ sơ công ty thành công.", "success")
        return redirect(url_for("employer.profile"))

    return render_template("employer/edit_profile.html", form=form, employer=employer)

@employer_bp.route("/application/<int:app_id>/<action>")
@login_required
def change_application_status(app_id, action):
    application = Application.query.get_or_404(app_id)
    job = application.job

    if current_user.role != "employer" or job.employer_id != current_user.employer_profile.id:
        flash("Không có quyền thực hiện hành động này.", "danger")
        return redirect(url_for("employer.dashboard"))

    if action == "accept":
        application.status = "accepted"
        flash("Đã duyệt ứng viên.", "success")
    elif action == "reject":
        application.status = "rejected"
        flash("Đã từ chối ứng viên.", "warning")
    else:
        flash("Hành động không hợp lệ.", "danger")
        return redirect(url_for("employer.view_applicants", job_id=job.id))

    db.session.commit()
    return redirect(url_for("employer.view_applicants", job_id=job.id))