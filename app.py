import re, os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, Candidate, Employer, Job, CandidateProfile, Application, SavedJob

# ==================================
# Hàm tiện ích
# ==================================
def parse_int_from_str(s):
    """Chuyển chuỗi lương thành số int (VNĐ)"""
    if not s:
        return None
    if isinstance(s, int):
        return s
    s = str(s).strip().lower()
    if s == "":
        return None

    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(triệu|tr)\b', s, flags=re.IGNORECASE)
    if m:
        try:
            num = float(m.group(1).replace(',', '.'))
            return int(num * 1_000_000)
        except Exception:
            pass

    digits = re.sub(r'[^\d]', '', s)
    if digits:
        try:
            return int(digits)
        except Exception:
            return None
    return None


def format_salary_for_template(value):
    """Định dạng hiển thị lương"""
    if value is None or value == "":
        return "Thương lượng"
    try:
        num = int(value)
        return "{:,}".format(num).replace(",", ".")
    except Exception:
        return str(value)


# ==================================
# Cấu hình Flask
# ==================================
app = Flask(__name__)
app.secret_key = "secret-key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:admin@localhost/db1?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.jinja_env.filters['fmt_salary'] = format_salary_for_template


# ==================================
# Quản lý login
# ==================================
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith("C-"):
        return Candidate.query.get(int(user_id.split("-")[1]))
    elif user_id.startswith("E-"):
        return Employer.query.get(int(user_id.split("-")[1]))
    return None


Candidate.get_id = lambda self: f"C-{self.id}"
Employer.get_id = lambda self: f"E-{self.id}"


# ==================================
# Trang chính
# ==================================
@app.route("/")
def index():
    keyword = request.args.get("keyword", "")
    location = request.args.get("location", "")
    min_salary = request.args.get("min_salary", "")
    max_salary = request.args.get("max_salary", "")
    job_type = request.args.get("job_type", "")
    sort_by = request.args.get("sort_by", "")
    page = int(request.args.get("page", 1))

    # Lọc dữ liệu (demo: chưa viết query filter chi tiết)
    jobs = Job.query.all()

    # Gói thông tin search để truyền xuống template
    search = {
        "keyword": keyword,
        "location": location,
        "min_salary": min_salary,
        "max_salary": max_salary,
        "job_type": job_type,
        "sort_by": sort_by,
    }

    return render_template(
        "index.html",
        jobs=jobs,
        hot_jobs=jobs[:3],       # ví dụ: 3 job hot
        other_jobs=jobs[3:],     # còn lại
        total_pages=1,           # chưa phân trang thật
        page=page,
        search=search,           # ✅ thêm dòng này
        user=current_user,
    )
@app.route("/provinces")
def provinces():
    return send_from_directory("static/data", "provinces.json")


# ==================================
# Đăng ký / Đăng nhập
# ==================================
@app.route("/login")
def login():
    return render_template("choose_login.html")


@app.route("/register")
def register():
    return render_template("choose_register.html")


@app.route("/register/candidate", methods=["GET", "POST"])
def register_candidate():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        if Candidate.query.filter_by(email=email).first():
            flash("Email đã tồn tại!", "danger")
            return redirect(url_for("register_candidate"))

        new_user = Candidate(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Đăng ký thành công, vui lòng đăng nhập!", "success")
        return redirect(url_for("login_candidate"))

    return render_template("register_candidate.html", title="Đăng ký Ứng viên")


@app.route("/login/candidate", methods=["GET", "POST"])
def login_candidate():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = Candidate.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Sai email hoặc mật khẩu!", "danger")
    return render_template("login_candidate.html", title="Đăng nhập Ứng viên")



@app.route("/register_employer", methods=["GET", "POST"])
def register_employer():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        company_name = request.form.get("company_name")
        phone = request.form.get("phone")
        location = request.form.get("location")

        hashed_pw = generate_password_hash(password)

        new_emp = Employer(
            name=name,
            email=email,
            password=hashed_pw,
            company_name=company_name,
            phone=phone,
            location=location
        )
        db.session.add(new_emp)
        db.session.commit()
        flash("Đăng ký nhà tuyển dụng thành công!", "success")
        return redirect(url_for("index"))

    return render_template("register_employer.html")

@app.route("/login/employer", methods=["GET", "POST"])
def login_employer():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = Employer.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("employer_dashboard"))
        flash("Sai email hoặc mật khẩu!", "danger")
    return render_template("login_employer.html", title="Đăng nhập Nhà tuyển dụng")


@app.route("/dashboard/employer")
@login_required
def employer_dashboard():
    if not isinstance(current_user, Employer):
        flash("Bạn không có quyền vào trang này!", "danger")
        return redirect("/")
    return render_template("employer_dashboard.html", user=current_user)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất!", "info")
    return redirect(url_for("index"))


# ==================================
# Tin tuyển dụng
# ==================================
@app.route("/post_job", methods=["GET", "POST"])
@login_required
def post_job():
    if not isinstance(current_user, Employer):
        flash("Chỉ nhà tuyển dụng mới có thể đăng tin.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        new_job = Job(
            employer_id=current_user.id,
            title=request.form["title"],
            location=request.form["location"],
            description=request.form["description"],
            salary=request.form["salary"],
            job_type=request.form["job_type"],
            status="active"
        )
        db.session.add(new_job)
        db.session.commit()

        flash("✅ Tin tuyển dụng đã được đăng thành công!", "success")
        return redirect(url_for("list_jobs"))

    return render_template("post_job.html")


@app.route("/jobs")
def list_jobs():
    jobs = Job.query.filter_by(status="active").order_by(Job.id.desc()).all()
    return render_template("jobs.html", jobs=jobs)


@app.route("/job/<int:id>")
def job_detail(id):
    job = Job.query.get_or_404(id)
    return render_template("job_detail.html", job=job)


# ==================================
# Ứng viên lưu tin & ứng tuyển
# ==================================
UPLOAD_FOLDER = "uploads/cv"


@app.route("/jobs/<int:job_id>/save")
@login_required
def save_job(job_id):
    if not isinstance(current_user, Candidate):
        flash("Chỉ ứng viên mới có thể lưu tin.", "danger")
        return redirect(url_for("job_detail", id=job_id))

    saved = SavedJob.query.filter_by(candidate_id=current_user.id, job_id=job_id).first()
    if not saved:
        saved = SavedJob(candidate_id=current_user.id, job_id=job_id)
        db.session.add(saved)
        db.session.commit()
        flash("Tin đã được lưu!", "success")
    else:
        flash("Bạn đã lưu tin này rồi.", "warning")
    return redirect(url_for("job_detail", id=job_id))


@app.route("/jobs/<int:job_id>/apply", methods=["GET", "POST"])
@login_required
def apply_job(job_id):
    if not isinstance(current_user, Candidate):
        flash("Chỉ ứng viên mới có thể ứng tuyển.", "danger")
        return redirect(url_for("job_detail", id=job_id))

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
        return redirect(url_for("job_detail", id=job.id))

    return render_template("apply_job.html", job=job)


@app.route("/saved_jobs")
@login_required
def saved_jobs():
    if not hasattr(current_user, "saved_jobs"):
        flash("Chỉ ứng viên mới có thể xem tin đã lưu!", "warning")
        return redirect(url_for("index"))

    jobs = [s.job for s in current_user.saved_jobs]
    return render_template("saved_jobs.html", jobs=jobs)


# ============================
# Xem & cập nhật hồ sơ ứng viên
# ============================
@app.route("/profile")
@login_required
def profile():
    if not hasattr(current_user, "profile"):
        flash("Bạn chưa có hồ sơ. Hãy tạo ngay!", "info")
        return redirect(url_for("create_profile"))

    return render_template("profile.html", profile=current_user.profile)


@app.route("/create_profile", methods=["GET", "POST"])
@login_required
def create_profile():
    if request.method == "POST":
        phone = request.form["phone"]
        location = request.form["location"]
        cv_file = request.form["cv_file"]

        profile = CandidateProfile(
            candidate_id=current_user.id,
            phone=phone,
            location=location,
            cv_file=cv_file
        )
        db.session.add(profile)
        db.session.commit()
        flash("Hồ sơ đã được tạo thành công!", "success")
        return redirect(url_for("profile"))

    return render_template("create_profile.html")

@app.route("/search_jobs")
def search_jobs():
    jobs = Job.query.filter_by(status="active").all()
    return render_template("search_jobs.html", jobs=jobs)

@app.route("/candidate/dashboard")
def candidate_dashboard():
    # Lấy danh sách job từ DB (ví dụ query theo user_id)
    applied_jobs = Job.query.join(Application).filter(Application.user_id == current_user.id).all()
    saved_jobs = Job.query.join(SavedJob).filter(SavedJob.user_id == current_user.id).all()

    return render_template(
        "candidate_dashboard.html",
        applied_jobs=applied_jobs,
        saved_jobs=saved_jobs
    )

# ==================================
# Run App
# ==================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
