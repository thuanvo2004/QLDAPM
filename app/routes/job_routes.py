import re

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, \
    jsonify
from flask_login import login_required, current_user
from sqlalchemy import case, or_, func, and_

from app.forms import JobForm
from app.models import Job, Employer
from app.extensions import db
from datetime import datetime, date

from app.routes.main import load_json_file

job_bp = Blueprint("job", __name__, url_prefix="/jobs")

# Đăng tin
@job_bp.route("/post", methods=["GET", "POST"])
@login_required
def post_job():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng được tạo job", "danger")
        return redirect(url_for("main.index"))

        # Check if employer has more than 1 post and is not premium
    employer_jobs_count = Job.query.filter_by(employer_id=current_user.employer_profile.id).count()
    if employer_jobs_count >= 1 and not current_user.isPremiumActive:
        flash("Bạn cần nâng cấp tài khoản Premium để đăng thêm tin tuyển dụng", "warning")
        return redirect(url_for("payment.payment_view"))

    form = JobForm()
    print(f"Form fields: {form._fields.keys()}")
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

def parse_int_from_str(s):
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    if digits == "":
        return None
    return int(digits)

# Danh sách job (cho ứng viên)
@job_bp.route("/")
def list_jobs():
    # pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 6, type=int)

    keyword = (request.args.get("keyword", "") or "").strip()
    location_raw = request.args.get("city", "")
    job_type_raw = (request.args.get("job_type", "") or "").strip()
    work_type_raw = (request.args.get("work_type", "") or "").strip()
    sort_by = request.args.get("sort_by", "")

    min_salary_raw = request.args.get("salary_min") or request.args.get("min_salary") or request.args.get("min")
    max_salary_raw = request.args.get("salary_max") or request.args.get("max_salary") or request.args.get("max")

    min_salary = parse_int_from_str(min_salary_raw)
    max_salary = parse_int_from_str(max_salary_raw)

    q = Job.query.outerjoin(Employer)

    # --- keyword ---
    if keyword:
        kw_like = f"%{keyword}%"
        q = q.filter(or_(
            Job.title.ilike(kw_like),
            Job.description.ilike(kw_like),
            Employer.company_name.ilike(kw_like)
        ))

    # --- location ---
    if location_raw:
        locs = [s.strip() for s in location_raw.split(",") if s.strip()]
        if locs:
            locs_lower = [l.lower() for l in locs]
            q = q.filter(func.lower(Job.city).in_(locs_lower))

    # --- job type ---
    if job_type_raw and job_type_raw.lower() != "all":
        q = q.filter(func.lower(Job.job_type) == job_type_raw.lower())

    # --- work type ---
    if work_type_raw:
        work_types = [s.strip().lower() for s in work_type_raw.split(",") if s.strip()]
        if work_types and "all" not in work_types:
            q = q.filter(func.lower(Job.remote_option).in_(work_types))

    # --- salary filter ---
    if min_salary is not None and max_salary is not None:
        q = q.filter(and_(
            Job.salary_max >= min_salary,
            Job.salary_min <= max_salary
        ))
    else:
        if min_salary is not None:
            q = q.filter(Job.salary_min >= min_salary)
        if max_salary is not None:
            q = q.filter(Job.salary_max <= max_salary)

    # --- sort ---
    if sort_by == "salary_desc":
        q = q.order_by(
            case((Job.salary_max == None, 1), else_=0),
            Job.salary_max.desc()
        )
    elif sort_by == "salary_asc":
        q = q.order_by(
            case((Job.salary_min == None, 1), else_=0),
            Job.salary_min.asc()
        )
    elif sort_by == "newest":
        q = q.order_by(Job.created_at.desc())
    else:
        q = q.order_by(Job.created_at.desc())

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    jobs_page = pagination.items

    now = date.today()
    for job in pagination.items:
        job.is_active = (job.deadline is None) or (job.deadline >= now)

    search_params = {
        "keyword": keyword,
        "city": location_raw,
        "job_type": job_type_raw,
        "work_types": work_type_raw.split(",") if work_type_raw else [],
        "job_types": [job_type_raw] if job_type_raw else [],
        "sort_by": sort_by,
        "min_salary": min_salary_raw or "",
        "max_salary": max_salary_raw or "",
        "per_page": per_page
    }

    logo = None
    if current_user.is_authenticated and current_user.role == "employer":
        logo = current_user.employer_profile.logo

    return render_template(
        "jobs/list_jobs.html",
        jobs=jobs_page,
        search=search_params,
        total_pages=pagination.pages,
        page=pagination.page,
        user=current_user,
        logo=logo,
        now=now
    )

# Chi tiết job
@job_bp.route("/<int:job_id>")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    now = date.today()
    job.is_active = (job.deadline is None) or (job.deadline >= now)

    return render_template("jobs/job_detail.html", job=job, now=datetime.utcnow())

# Quản lý job của employer
@job_bp.route("/manage")
@login_required
def manage_jobs():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng được quản lý job", "danger")
        return redirect(url_for("job.list_jobs"))

    jobs = Job.query.filter_by(employer_id=current_user.employer_profile.id).all()
    return render_template("jobs/manage_jobs.html", jobs=jobs)


@job_bp.route("/provinces")
def provinces():
    return send_from_directory("static/data", "provinces.json")

@job_bp.app_template_global()
def format_salary_range(min_salary, max_salary):
    def to_mil(v):
        try:
            v = int(v)
            return v // 1_000_000
        except (TypeError, ValueError):
            return None

    a, b = to_mil(min_salary), to_mil(max_salary)
    if a and b:
        return f"{a}-{b} triệu"
    if a:
        return f"Từ {a} triệu"
    if b:
        return f"Đến {b} triệu"
    return "Thương lượng"

@job_bp.route('/industries')
def industries_json():
    data = load_json_file('industries.json')
    if data is None:
        return jsonify({'industries': []}), 200
    if isinstance(data, list):
        return jsonify({'industries': data})
    return jsonify(data)