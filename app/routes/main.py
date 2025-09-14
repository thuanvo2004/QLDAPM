import re
from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory
from flask_login import current_user
from app.models import Job, db   # nhớ import db nếu cần

# ============================
# Blueprint
# ============================
main_bp = Blueprint("main", __name__)

# ============================
# Trang chủ
# ============================
@main_bp.route("/")
def index():
    # phân trang
    page = request.args.get("page", 1, type=int)
    per_page = 12
    jobs_query = Job.query.paginate(page=page, per_page=per_page)

    # lọc
    keyword = request.args.get("keyword", "")
    location = request.args.get("location", "")
    job_type = request.args.get("job_type", "")
    sort_by = request.args.get("sort_by", "")
    min_salary_raw = request.args.get("min_salary", "")
    max_salary_raw = request.args.get("max_salary", "")

    min_salary = parse_int_from_str(min_salary_raw)
    max_salary = parse_int_from_str(max_salary_raw)

    # lọc + sắp xếp từ jobs_query.items (list các Job)
    filtered = filter_jobs(
        jobs_query.items,
        keyword=keyword,
        location=location,
        min_salary=min_salary,
        max_salary=max_salary,
        job_type=job_type,
        sort_by=sort_by,
    )

    hot_jobs = [j for j in filtered if getattr(j, "featured", False)]
    other_jobs = [j for j in filtered if not getattr(j, "featured", False)]

    search_params = {
        "keyword": keyword,
        "location": location,
        "job_type": job_type,
        "sort_by": sort_by,
        "min_salary": min_salary_raw,
        "max_salary": max_salary_raw
    }

    return render_template(
        "index.html",
        hot_jobs=hot_jobs,
        other_jobs=other_jobs,
        jobs=filtered,
        search=search_params,
        total_pages=jobs_query.pages,
        page=jobs_query.page,
        user=current_user
    )

# ============================
# Hàm trích xuất số nguyên từ chuỗi
# ============================
def parse_int_from_str(s):
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    if digits == "":
        return None
    return int(digits)

# ============================
# Hàm lọc và sắp xếp Job
# ============================
def filter_jobs(job_list, keyword=None, location=None,
                min_salary=None, max_salary=None,
                job_type=None, sort_by=None):

    k = (keyword or "").strip().lower()
    filtered = []

    for j in job_list:
        # tìm theo từ khóa
        if k:
            title = (j.title or "").lower()
            company = (j.company or "").lower()
            if k not in title and k not in company:
                continue

        # location
        if location and location.strip():
            if (j.location or "").lower() != location.strip().lower():
                continue

        # job type
        if job_type and job_type.strip():
            if not j.job_type or j.job_type.lower() != job_type.strip().lower():
                continue

        # min_salary
        if min_salary is not None:
            if not getattr(j, "salary", None) or j.salary < min_salary:
                continue

        # max_salary
        if max_salary is not None:
            if not getattr(j, "salary", None) or j.salary > max_salary:
                continue

        filtered.append(j)

    # sắp xếp
    if sort_by == "salary_desc":
        filtered.sort(key=lambda x: (x.salary or 0), reverse=True)
    elif sort_by == "salary_asc":
        filtered.sort(key=lambda x: (x.salary or 0))
    elif sort_by == "newest":
        filtered.sort(key=lambda x: x.id, reverse=True)

    return filtered

# ============================
# Định dạng lương cho template
# ============================
def format_salary_for_template(value):
    if value is None or value == "":
        return "Thương lượng"
    try:
        if isinstance(value, int):
            return "{:,}".format(value)
        s = str(value).strip()
        digits = re.sub(r"[^\d]", "", s)
        if digits:
            return "{:,}".format(int(digits))
        return s
    except Exception:
        return str(value)

# ============================
# File JSON tỉnh thành
# ============================
@main_bp.route("/provinces")
def provinces():
    return send_from_directory("static/data", "provinces.json")

# ============================
# Định dạng lương dạng "triệu"
# ============================
@main_bp.app_template_global()
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

