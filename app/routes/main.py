from flask import Blueprint, render_template, request
from app.models import Job

main_bp = Blueprint("main", __name__)
@main_bp.route("/")
def index():
    # ví dụ query job từ DB
    page = request.args.get("page", 1, type=int)
    per_page = 10

    jobs = Job.query.paginate(page=page, per_page=per_page)

    return render_template(
        "index.html",
        jobs=jobs.items,
        total_pages=jobs.pages,
        current_page=jobs.page
    )
