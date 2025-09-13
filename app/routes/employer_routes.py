import os

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from flask_login import login_required, current_user
from sqlalchemy import func, case, or_, and_
from werkzeug.utils import secure_filename

from app.models import Job, Application, Employer
from app.extensions import db
from app.forms import JobForm,EmployerProfileForm
from datetime import datetime, date, time
from cloudinary.uploader import upload

employer_bp = Blueprint("employer", __name__, url_prefix="/employer")

@employer_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng mới xem dashboard", "danger")
        return redirect(url_for("job.list_jobs"))

    employer = current_user.employer_profile
    if not employer:
        return "No employer profile", 404

    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 9

    base = Job.query.filter(Job.employer_id == employer.id)

    if q:
        like = f"%{q}%"
        base = base.filter(or_(Job.title.ilike(like),
                               Job.description.ilike(like),
                               Job.city.ilike(like)))

    now = date.today()
    if status_filter == 'active':
        base = base.filter(
            or_(
                Job.deadline == None,
                Job.deadline >= now
            )
        )
    elif status_filter == 'expired':
        base = base.filter(
            and_(
                Job.deadline != None,
                Job.deadline < now
            )
        )

    # Subquery to count applications and pending applications
    subq = db.session.query(
        Application.job_id.label('job_id'),
        func.count(Application.id).label('cnt'),
        func.sum(case((Application.status == 'pending', 1), else_=0)).label('pending_cnt')
    ).group_by(Application.job_id).subquery()

    jobs_query = base.outerjoin(subq, Job.id == subq.c.job_id) \
        .with_entities(Job, subq.c.cnt, subq.c.pending_cnt) \
        .order_by(Job.created_at.desc())

    pagination = jobs_query.paginate(page=page, per_page=per_page, error_out=False)

    # Convert rows to job objects with attributes
    items = []
    for row in pagination.items:
        job = row[0]
        cnt = row[1] or 0  # Total applicants
        pending_cnt = row[2] or 0  # Pending applicants
        job.applicants_count = cnt
        job.pending_applicants = pending_cnt
        job.is_active = (job.deadline is None) or (job.deadline >= now)
        items.append(job)

    pagination.items = items

    # Stats
    total_jobs = Job.query.filter(Job.employer_id == employer.id).count()
    active_jobs = Job.query.filter(
        Job.employer_id == employer.id,
        or_(Job.deadline == None, Job.deadline >= now)
    ).count()
    pending_applicants = db.session.query(func.count(Application.id)).join(Job, Application.job_id == Job.id).filter(
        Job.employer_id == employer.id,
        Application.status == 'pending'
    ).scalar() or 0

    # Debugging output (remove in production)
    print(f"Total Jobs: {total_jobs}")
    print(f"Active Jobs: {active_jobs}")
    print(f"Pending Applicants: {pending_applicants}")

    return render_template('employer/dashboard.html',
                           jobs=pagination,
                           total_jobs=total_jobs,
                           is_active=active_jobs,  # Renamed to match template
                           pending_applicants=pending_applicants,
                           now=now)

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
            result = upload(form.logo.data, folder="jobnest/logos")
            employer.logo = result.get("secure_url")  # lưu URL vào DB

        db.session.commit()
        flash("Cập nhật hồ sơ thành công!", "success")
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

@employer_bp.route('/employers')
def list_employers():
    # Lấy tham số tìm kiếm và phân trang
    keyword = request.args.get('keyword', '').strip()
    city = request.args.get('city', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 9

    # Xây dựng truy vấn cơ bản
    base_query = Employer.query

    # Tìm kiếm theo tên công ty và địa điểm
    if keyword:
        like = f"%{keyword}%"
        base_query = base_query.filter(or_(
            Employer.company_name.ilike(like),
            Employer.city.ilike(like)
        ))

    if city:
        base_query = base_query.filter(Employer.city.ilike(f"%{city}%"))

    # Subquery để đếm số công việc đang mở
    now = date.today()
    subquery = db.session.query(
        Job.employer_id.label('employer_id'),
        func.count(Job.id).label('active_jobs_count')
    ).filter(
        or_(Job.deadline == None, Job.deadline >= now)
    ).group_by(Job.employer_id).subquery()

    # Join với subquery để lấy số công việc đang mở
    employers_query = base_query.outerjoin(
        subquery, Employer.id == subquery.c.employer_id
    ).with_entities(
        Employer, subquery.c.active_jobs_count
    ).order_by(Employer.company_name.asc())

    # Phân trang
    pagination = employers_query.paginate(page=page, per_page=per_page, error_out=False)

    # Xử lý items để thêm active_jobs_count
    items = []
    for row in pagination.items:
        employer = row[0]
        employer.active_jobs_count = row[1] or 0
        items.append(employer)

    pagination.items = items

    # Chuẩn bị dữ liệu tìm kiếm cho template
    search = {
        'keyword': keyword,
        'city': city
    }

    return render_template(
        'employer/list_employers.html',
        employers=pagination,
        total_pages=pagination.pages,
        page=page,
        search=search,
        now=now
    )

@employer_bp.route('/employers/<int:employer_id>')
def employer_detail(employer_id):
    employer = Employer.query.get_or_404(employer_id)
    now = date.today()  # Current date: 2025-09-13

    # Fetch active jobs for the employer
    jobs = Job.query.filter(
        Job.employer_id == employer_id,
        or_(Job.deadline == None, Job.deadline >= now)
    ).all()

    return render_template(
        'employer/detail.html',  # Template to display employer details
        employer=employer,
        jobs=jobs,
        now=now
    )