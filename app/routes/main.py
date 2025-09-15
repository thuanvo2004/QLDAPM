import json
import os
import re
from flask import Blueprint, render_template, request, send_from_directory, current_app
from flask_login import current_user
from app.models import Job, Employer, db
from sqlalchemy import or_, and_, func, desc, asc, case

# ============================
# Blueprint
# ============================
main_bp = Blueprint("main", __name__)

from flask import jsonify

_json_cache = {}

def load_json_file(filename):
    # key by absolute path
    app_root = current_app.root_path
    path = os.path.join(app_root, 'static', 'data', filename)
    # cache by path
    if path in _json_cache:
        return _json_cache[path]
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    _json_cache[path] = data
    return data

@main_bp.route('/provinces')
def provinces_json():
    data = load_json_file('provinces.json')
    if data is None:
        return jsonify({'provinces': []}), 200
    # ensure response shape { provinces: [...] }
    if isinstance(data, list):
        return jsonify({'provinces': data})
    return jsonify(data)

@main_bp.route('/industries')
def industries_json():
    data = load_json_file('industries.json')
    if data is None:
        return jsonify({'industries': []}), 200
    if isinstance(data, list):
        return jsonify({'industries': data})
    return jsonify(data)


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

@main_bp.route("/")
def index():
    # pagination params
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 9, type=int)

    keyword = (request.args.get("keyword", "") or "").strip()

    location_raw = request.args.get("city", "")
    job_type_raw = (request.args.get("job_type", "") or "").strip()  # Single value
    work_type_raw = (request.args.get("work_type", "") or "").strip()
    sort_by = request.args.get("sort_by", "")

    min_salary_raw = request.args.get("salary_min") or request.args.get("min_salary") or request.args.get("min")
    max_salary_raw = request.args.get("salary_max") or request.args.get("max_salary") or request.args.get("max")

    min_salary = parse_int_from_str(min_salary_raw)
    max_salary = parse_int_from_str(max_salary_raw)

    q = Job.query.outerjoin(Employer)

    # --- KEYWORD---
    if keyword:
        kw_like = f"%{keyword}%"
        q = q.filter(or_(
            Job.title.ilike(kw_like),
            Job.description.ilike(kw_like),
            Employer.company_name.ilike(kw_like)
        ))

    # --- LOCATION ---
    if location_raw:
        locs = [s.strip() for s in location_raw.split(",") if s.strip()]
        if locs:
            locs_lower = [l.lower() for l in locs]
            q = q.filter(func.lower(Job.city).in_(locs_lower))

    # --- JOB TYPE ---
    if job_type_raw and job_type_raw.lower() != "all":
        q = q.filter(func.lower(Job.job_type) == job_type_raw.lower())

    # --- WORK TYPE ---
    if work_type_raw:
        work_types = [s.strip().lower() for s in work_type_raw.split(",") if s.strip()]
        if work_types and "all" not in work_types:
            q = q.filter(func.lower(Job.remote_option).in_(work_types))

    # --- SALARY FILTER ---
    if min_salary is not None and max_salary is not None:
        q = q.filter(
            and_(
                Job.salary_max >= min_salary,
                Job.salary_min <= max_salary
            )
        )
    else:
        if min_salary is not None:
            q = q.filter(Job.salary_min >= min_salary)
        if max_salary is not None:
            q = q.filter(Job.salary_max <= max_salary)

    # --- SORT ---
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

    search_params = {
        "keyword": keyword,
        "city": location_raw,
        "job_type": job_type_raw,
        "work_types": work_type_raw.split(",") if work_type_raw else [],
        "job_types": [job_type_raw] if job_type_raw else [],  # Đảm bảo là list
        "sort_by": sort_by,
        "min_salary": min_salary_raw or "",
        "max_salary": max_salary_raw or "",
        "per_page": per_page
    }

    logo = None
    if current_user.is_authenticated and current_user.role == "employer":
        logo = current_user.employer_profile.logo

    return render_template(
        "index.html",
        jobs=jobs_page,
        search=search_params,
        total_pages=pagination.pages,
        page=pagination.page,
        user=current_user,
        logo=logo
    )

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

