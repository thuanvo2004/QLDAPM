from string import digits
import re
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory,session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from models import db, Candidate, Employer,Job, CandidateProfile,Application
from werkzeug.security import generate_password_hash, check_password_hash

# Hàm trích xuất số nguyên từ chuỗi, trả về None nếu không có số
def parse_int_from_str(s):
    if not s:
        return None
    if isinstance(s, int):
        return s
    s = str(s).strip().lower()
    if s == "":
        return None

    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(triỆu|triệu|tr)\b', s, flags=re.IGNORECASE)
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

def get_job_salary(job):
    raw = getattr(job, "salary", None)
    return parse_int_from_str(raw)


# Hàm lọc và sắp xếp việc làm dựa trên các tiêu chí
def filter_jobs(job_list, keyword=None, location=None, min_salary=None, max_salary=None, job_type=None, sort_by=None):
    k = (keyword or "").strip().lower()
    location_list = [loc.strip().lower() for loc in (location or "").split(',') if loc.strip()]
    filtered = []

    for j in job_list:
        if k:
            title = (j.title or "").lower()
            company = (j.company or "").lower()
            if k not in title and k not in company:
                continue

        if location_list:
            job_loc = (j.location or "").strip().lower()
            if job_loc not in location_list:
                continue

        if job_type and job_type.strip():
            if not j.job_type or j.job_type.strip().lower() != job_type.strip().lower():
                continue

        job_sal = get_job_salary(j)
        if min_salary is not None:
            if job_sal is None or job_sal < min_salary:
                continue
        if max_salary is not None:
            if job_sal is None or job_sal > max_salary:
                continue

        filtered.append(j)

    if sort_by == "salary_desc":
        filtered.sort(key=lambda x: (get_job_salary(x) or 0), reverse=True)
    elif sort_by == "salary_asc":
        filtered.sort(key=lambda x: (get_job_salary(x) or 0))
    elif sort_by == "newest":
        filtered.sort(key=lambda x: x.id, reverse=True)

    return filtered

app = Flask(__name__)
app.secret_key = "secret-key"

# nhớ thay thế: root:admin@localhost/db1
#root: là tài khoản kết nối db
#admin: là pass đăng nhập db
# db1 là tên db cần kết nối
app.config["SECRET_KEY"] = "secret123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:admin@localhost/db1?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)



# ============================
# Hàm định dạng lương cho template
# ============================
def format_salary_for_template(value):
    if value is None or value == "":
        return "Thương lượng"
    try:
        num = int(value)
        return "{:,}".format(num).replace(",", ".")
    except Exception:
        return str(value)

app.jinja_env.filters['fmt_salary'] = format_salary_for_template


# Quản lý login
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # Candidate và Employer có ID riêng
    # Để phân biệt, ta truyền "C-{id}" hoặc "E-{id}"
    if user_id.startswith("C-"):
        return Candidate.query.get(int(user_id.split("-")[1]))
    elif user_id.startswith("E-"):
        return Employer.query.get(int(user_id.split("-")[1]))
    return None

# Custom get_id để phân biệt
Candidate.get_id = lambda self: f"C-{self.id}"
Employer.get_id = lambda self: f"E-{self.id}"



# Trang chủ

@app.route('/')
def index():
    # Lấy tham số phân trang
    page = request.args.get('page', 1, type=int)
    per_page = 15

    # Lấy các tham số lọc
    keyword = request.args.get("keyword", "")
    location_raw = request.args.get("location", "")
    job_type = request.args.get("job_type", "")
    sort_by = request.args.get("sort_by", "")
    min_salary_raw = request.args.get("min_salary", "")
    max_salary_raw = request.args.get("max_salary", "")

    min_salary = parse_int_from_str(min_salary_raw)
    max_salary = parse_int_from_str(max_salary_raw)

    # Lấy tất cả công việc và lọc
    jobs_query = Job.query
    jobs = jobs_query.all()
    filtered_jobs = filter_jobs(
        jobs,
        keyword=keyword,
        location=location_raw,
        min_salary=min_salary,
        max_salary=max_salary,
        job_type=job_type,
        sort_by=sort_by
    )

    # Phân trang
    total_jobs = len(filtered_jobs)
    total_pages = (total_jobs + per_page - 1) // per_page  # Tính tổng số trang
    start = (page - 1) * per_page
    end = start + per_page
    paginated_jobs = filtered_jobs[start:end]

    # Tách công việc nổi bật và không nổi bật
    hot_jobs = [j for j in paginated_jobs if getattr(j, "featured", False)]
    other_jobs = [j for j in paginated_jobs if not getattr(j, "featured", False)]

    # Lưu các tham số tìm kiếm
    search_params = {
        "keyword": keyword,
        "location": location_raw,
        "job_type": job_type,
        "sort_by": sort_by,
        "min_salary": min_salary_raw,
        "max_salary": max_salary_raw
    }

    return render_template(
        'index.html',
        hot_jobs=hot_jobs,
        other_jobs=other_jobs,
        search=search_params,
        jobs=jobs,
        user=current_user,
        page=page,
        total_pages=total_pages  # Đảm bảo truyền total_pages
    )

# ============================
# Phục vụ file JSON tỉnh thành
# ============================
@app.route('/provinces')
def provinces():
    return send_from_directory('static/data', 'provinces.json')



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
            return redirect(url_for("candidate_dashboard"))
        flash("Sai email hoặc mật khẩu!", "danger")
    return render_template("login_candidate.html", title="Đăng nhập Ứng viên")
@app.route("/dashboard/candidate")
@login_required
def candidate_dashboard():
    if not isinstance(current_user, Candidate):
        flash("Bạn không có quyền vào trang này!", "danger")
        return redirect("/")
    return render_template("candidate_dashboard.html", user=current_user)
@app.route("/register/employer", methods=["GET", "POST"])
def register_employer():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        company = request.form["company"]
        phone = request.form["phone"]
        location = request.form["location"]

        # Kiểm tra email trùng
        if Employer.query.filter_by(email=email).first():
            flash("Email đã tồn tại!", "danger")
            return redirect(url_for("register_employer"))

        new_emp = Employer(
            name=name,
            email=email,
            password=password,
            company=company,
            phone=phone,
            location=location
        )
        db.session.add(new_emp)
        db.session.commit()
        flash("Đăng ký thành công, vui lòng đăng nhập!", "success")
        return redirect(url_for("login_employer"))

    return render_template("register_employer.html", title="Đăng ký Nhà tuyển dụng")

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



@app.route("/candidate/manage_cv")
@login_required
def manage_cv():
    return "Trang quản lý CV (chưa code)"

@app.route("/candidate/search_jobs")
@login_required
def search_jobs():
    return "Trang tìm kiếm việc làm (chưa code)"

@app.route("/candidate/apply_jobs")
@login_required
def apply_jobs():
    return "Trang nộp hồ sơ (chưa code)"







# Đăng xuất
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất!", "info")
    return redirect(url_for("index"))



# ============================
# Trang thêm việc làm
# ============================
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_job():
    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        location = request.form.get('location', '')
        description = request.form['description']
        salary_raw = request.form.get('salary', '').strip()
        salary = parse_int_from_str(salary_raw)
        job_type = request.form.get('job_type', '').strip()
        featured = bool(request.form.get('featured'))

        new_job = Job(title=title, company=company, location=location, description=description,
                      salary=salary, job_type=job_type, featured=featured)
        db.session.add(new_job)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('add_job.html')


@app.route('/application/<int:app_id>/<status>')
@login_required
def update_application_status(app_id, status):
    if current_user.role != 'employer':
        flash("Bạn không có quyền!", "danger")
        return redirect(url_for('login_employer'))

    application = JobApplication.query.get_or_404(app_id)

    # Chỉ cho phép employer quản lý các job của họ
    if application.job.employer_id != current_user.id:
        flash("Bạn không có quyền chỉnh sửa hồ sơ này!", "danger")
        return redirect(url_for('employer_dashboard'))

    application.status = status
    db.session.commit()
    flash(f"Hồ sơ đã được cập nhật: {status}", "success")
    return redirect(url_for('employer_dashboard'))



# ============================
# Chạy server
# ============================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)