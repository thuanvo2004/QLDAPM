from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, Candidate, Employer, Job, db
from sqlalchemy import extract, func
from datetime import datetime, timedelta


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ==============================
# Decorator kiểm tra quyền admin
# ==============================
def admin_required(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Bạn không có quyền truy cập!", "danger")
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    # ===== Thống kê tổng quan =====
    stats = {
        "users": User.query.count(),
        "jobs": Job.query.count(),
        "candidates": Candidate.query.count(),
        "employers": Employer.query.count(),
    }

    current_year = datetime.now().year
    labels = [f'T{i}' for i in range(1, 13)]

    # ===== Jobs theo tháng =====
    job_counts = db.session.query(
        extract('month', Job.created_at).label('month'),
        func.count(Job.id)
    ).filter(extract('year', Job.created_at) == current_year
    ).group_by('month').order_by('month').all()
    job_values = [next((count for m, count in job_counts if m == i), 0) for i in range(1, 13)]

    # ===== Candidates theo tháng =====
    candidate_counts = db.session.query(
        extract('month', Candidate.created_at).label('month'),
        func.count(Candidate.id)
    ).filter(extract('year', Candidate.created_at) == current_year
    ).group_by('month').order_by('month').all()
    candidate_values = [next((count for m, count in candidate_counts if m == i), 0) for i in range(1, 13)]

    # ===== Employers theo tháng =====
    employer_counts = db.session.query(
        extract('month', Employer.created_at).label('month'),
        func.count(Employer.id)
    ).filter(extract('year', Employer.created_at) == current_year
    ).group_by('month').order_by('month').all()
    employer_values = [next((count for m, count in employer_counts if m == i), 0) for i in range(1, 13)]

    # ===== Recent items =====
    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
    recent_candidates = Candidate.query.order_by(Candidate.created_at.desc()).limit(5).all()
    recent_employers = Employer.query.order_by(Employer.created_at.desc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        labels=labels,
        job_values=job_values,
        candidate_values=candidate_values,
        employer_values=employer_values,
        recent_jobs=recent_jobs,
        recent_candidates=recent_candidates,
        recent_employers=recent_employers
    )
# ==============================
# USER MANAGEMENT
# ==============================
@admin_bp.route("/users")
@login_required
@admin_required
def list_users():
    users = User.query.filter(User.role != "admin").all()

    return render_template("admin/users.html", users=users)
@admin_bp.route("/users/<int:user_id>")
@login_required
@admin_required
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Không thể xem chi tiết admin", "warning")
        return redirect(url_for("admin.list_users"))
    return render_template("admin/view_user.html", user=user)


@admin_bp.route("/users/<int:user_id>/toggle")
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.isPremiumActive = not user.isPremiumActive
    db.session.commit()
    flash("Đã thay đổi trạng thái user!", "success")
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/users/<int:user_id>/toggle_status", methods=["POST"])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Không thể khóa/mở khóa admin", "danger")
        return redirect(url_for("admin.list_users"))

    user.active = not user.active
    db.session.commit()
    flash(f"Trạng thái của {user.email} đã được cập nhật!", "success")
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Không thể xóa admin", "danger")
        return redirect(url_for("admin.list_users"))

    db.session.delete(user)
    db.session.commit()
    flash("Người dùng đã bị xóa!", "success")
    return redirect(url_for("admin.list_users"))


# ==============================
# CANDIDATE MANAGEMENT
# ==============================
@admin_bp.route("/candidates")
@login_required
@admin_required
def list_candidates():
    candidates = Candidate.query.all()
    return render_template("admin/candidates.html", candidates=candidates)


@admin_bp.route("/candidates/<int:candidate_id>")
@login_required
@admin_required
def candidate_detail(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    return render_template("admin/candidate_detail.html", candidate=candidate)


@admin_bp.route("/candidates/<int:candidate_id>/delete", methods=["POST", "GET"])
@login_required
@admin_required
def delete_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    db.session.delete(candidate)
    db.session.commit()
    flash("Đã xoá ứng viên thành công!", "success")
    return redirect(url_for("admin.list_candidates"))


# ==============================
# EMPLOYER MANAGEMENT
# ==============================
@admin_bp.route("/employers")
@login_required
@admin_required
def list_employers():
    employers = Employer.query.all()
    return render_template("admin/employers.html", employers=employers)


# Xem chi tiết employer (kèm jobs)
@admin_bp.route("/employers/<int:employer_id>")
@login_required
@admin_required
def employer_detail(employer_id):
    employer = Employer.query.get_or_404(employer_id)
    jobs = Job.query.filter_by(employer_id=employer_id).all()
    return render_template("admin/employer_detail.html", employer=employer, jobs=jobs)

# Trang riêng xem employer (nếu muốn khác detail thì dùng đường dẫn /view)
@admin_bp.route("/employers/<int:employer_id>/view")
@login_required
@admin_required
def view_employer(employer_id):
    employer = Employer.query.get_or_404(employer_id)
    return render_template("admin/view_employer.html", employer=employer)

@admin_bp.route("/employers/<int:employer_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_employer(employer_id):
    employer = Employer.query.get_or_404(employer_id)

    if request.method == "POST":
        employer.company_name = request.form.get("company_name")
        employer.email = request.form.get("email")
        employer.phone = request.form.get("phone")
        employer.address = request.form.get("address")

        db.session.commit()
        flash("Cập nhật thông tin nhà tuyển dụng thành công", "success")
        return redirect(url_for("admin.employer_detail", employer_id=employer.id))

    return render_template("admin/edit_employer.html", employer=employer)


@admin_bp.route("/employers/<int:employer_id>/delete", methods=["POST", "GET"])
@login_required
@admin_required
def delete_employer(employer_id):
    employer = Employer.query.get_or_404(employer_id)
    db.session.delete(employer)
    db.session.commit()
    flash("Đã xoá nhà tuyển dụng", "danger")
    return redirect(url_for("admin.list_employers"))


# ==============================
# JOB MANAGEMENT
# ==============================
@admin_bp.route("/jobs")
@login_required
@admin_required
def list_jobs():
    jobs = Job.query.all()
    return render_template("admin/jobs.html", jobs=jobs)


@admin_bp.route("/jobs/<int:job_id>/approve")
@login_required
@admin_required
def approve_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_approved = True
    db.session.commit()
    flash("Đã duyệt tin tuyển dụng!", "success")
    return redirect(url_for("admin.list_jobs"))


@admin_bp.route("/jobs/<int:job_id>/reject")
@login_required
@admin_required
def reject_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_approved = False
    db.session.commit()
    flash("Đã từ chối tin tuyển dụng!", "danger")
    return redirect(url_for("admin.list_jobs"))


@admin_bp.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)

    if request.method == "POST":
        job.title = request.form.get("title")
        job.description = request.form.get("description")
        job.salary = request.form.get("salary")
        db.session.commit()
        flash("Cập nhật công việc thành công!", "success")
        return redirect(url_for("admin.list_jobs"))

    return render_template("admin/edit_job.html", job=job)


@admin_bp.route("/jobs/<int:job_id>/delete", methods=["POST", "GET"])
@login_required
@admin_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash("Đã xoá công việc thành công!", "success")
    return redirect(url_for("admin.list_jobs"))


# --- Route danh sách Premium ---
@admin_bp.route('/premium', methods=['GET'])
@login_required
def list_premium():
    search_email = request.args.get('search_email', '').strip()
    search_name = request.args.get('search_name', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = User.query.filter(User.isPremiumActive == True)
    if search_email:
        query = query.filter(User.email.ilike(f"%{search_email}%"))
    if search_name:
        query = query.filter(User.fullname.ilike(f"%{search_name}%"))
    if status == "active":
        query = query.filter(User.active == True)
    elif status == "inactive":
        query = query.filter(User.active == False)

    premium_users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template("admin/premium.html", premium_users=premium_users)

# --- Route thêm Premium ---
@admin_bp.route('/premium/add', methods=['GET', 'POST'])
def add_premium():
    # Lấy tất cả employer chưa phải premium
    employers = User.query.filter_by(role='employer', isPremiumActive=False).all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        user = User.query.get(user_id)
        if not user:
            flash("Người dùng không tồn tại.", "danger")
            return redirect(url_for('admin.add_premium'))

        # Nâng cấp premium 1 năm
        user.isPremiumActive = True
        user.expiry_date = datetime.utcnow() + timedelta(days=365)
        db.session.commit()
        flash(f"{user.email} đã được nâng cấp Premium.", "success")
        return redirect(url_for('admin.list_premium'))

    return render_template('admin/add_premium.html', employers=employers)

# --- Route sửa Premium ---
@admin_bp.route('/premium/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_premium(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.fullname = request.form.get('fullname')
        user.expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d')
        user.active = request.form.get('active') == 'on'
        db.session.commit()
        flash("Cập nhật thành công.", "success")
        return redirect(url_for('admin.list_premium'))

    return render_template("admin/edit_premium.html", user=user)

# --- Route xóa Premium ---
@admin_bp.route('/premium/delete/<int:id>', methods=['POST', 'GET'])
@login_required
def delete_premium(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash("Xóa người dùng thành công.", "success")
    return redirect(url_for('admin.list_premium'))

@admin_bp.route('/premium/renew/<int:user_id>', methods=['POST'])
def renew_premium(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("Người dùng không tồn tại.", "danger")
        return redirect(url_for('admin.list_premium'))

    if not user.isPremiumActive:
        flash("Người dùng này chưa phải Premium.", "warning")
        return redirect(url_for('admin.list_premium'))

    # Nếu expiry_date None hoặc đã hết hạn, bắt đầu từ hôm nay
    if not user.expiry_date or user.expiry_date < datetime.utcnow():
        user.expiry_date = datetime.utcnow() + timedelta(days=365)
    else:
        user.expiry_date = user.expiry_date + timedelta(days=365)

    db.session.commit()
    flash(f"{user.email} đã được gia hạn Premium 1 năm.", "success")
    return redirect(url_for('admin.list_premium'))


@admin_bp.route("/premium/update/<int:user_id>", methods=["POST"])
@login_required
def update_premium(user_id):
    user = User.query.get_or_404(user_id)

    # Lấy dữ liệu từ form
    expiry_date_str = request.form.get("expiry_date")
    if expiry_date_str:
        user.expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")

    db.session.commit()
    flash("Cập nhật Premium thành công!", "success")
    return redirect(url_for("admin.list_premium"))
