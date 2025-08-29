from string import digits
import re
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory,session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from models import db, Candidate, Employer,Job, CandidateProfile,Application



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

# Khởi tạo Flask app

app = Flask(__name__)
app.secret_key = "jobportal_secret"

# nhớ thay thế: root:admin@localhost/db1
#root: là tài khoản kết nối db
#admin: là pass đăng nhập db
# db1 là tên db cần kết nối
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:admin@localhost/db1?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



db.init_app(app)
bcrypt = Bcrypt(app)

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
login_manager.init_app(app)
login_manager.login_view = "choose_role"


@login_manager.user_loader
def load_user(user_id):
    # Tìm trong cả Candidate và Employer
    user = Candidate.query.get(user_id)
    if not user:
        user = Employer.query.get(user_id)
    return user



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


# Trang chọn role
@app.route("/choose_role")
def choose_role():
    return render_template("choose_role.html")
@app.route('/register')
def register():
    return render_template('choose_role.html')

# Đăng ký ứng viên
@app.route("/register/candidate", methods=["GET", "POST"])
def register_candidate():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Mật khẩu không khớp!", "danger")
            return redirect(url_for('register_candidate'))

        existing_user = Candidate.query.filter_by(email=email).first()
        if existing_user:
            flash("Email đã tồn tại!", "danger")
            return redirect(url_for('register_candidate'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_candidate = Candidate(name=name, email=email, password=hashed_password)
        db.session.add(new_candidate)
        db.session.commit()
        flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
        return redirect(url_for('login_candidate'))

    return render_template("register_candidate.html")

# Đăng ký nhà tuyển dụng
@app.route("/register/employer", methods=["GET", "POST"])
def register_employer():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        company = request.form.get('company')
        phone = request.form.get('phone')
        location = request.form.get('location')
        gender = request.form.get('gender')

        if password != confirm_password:
            flash("Mật khẩu không khớp!", "danger")
            return redirect(url_for('register_employer'))

        existing_user = Employer.query.filter_by(email=email).first()
        if existing_user:
            flash("Email đã tồn tại!", "danger")
            return redirect(url_for('register_employer'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_employer = Employer(
            name=name, email=email, password=hashed_password,
            company=company, phone=phone, location=location
        )
        db.session.add(new_employer)
        db.session.commit()
        flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
        return redirect(url_for('login_employer'))

    return render_template("register_employer.html")

def process_login(email, password, role):
    if role == "employer":
        user = Employer.query.filter_by(email=email).first()
    else:
        user = Candidate.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password, password):
        # Lưu id và role vào session
        session["user_id"] = user.id
        session["role"] = role

        if role == "employer":
            return redirect(url_for("employer_dashboard"))
        else:
            return redirect(url_for("candidate_dashboard"))
    else:
        flash("Sai email hoặc mật khẩu!", "danger")
        return redirect(request.url)



# Đăng nhập ứng viên
@app.route("/login/candidate", methods=["GET", "POST"])
def login_candidate():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        return process_login(email, password, role="candidate")
    return render_template("login_candidate.html")

# Đăng nhập nhà tuyển dụng
@app.route("/login/employer", methods=["GET", "POST"])
def login_employer():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        return process_login(email, password, role="employer")
    return render_template("login_employer.html")


# Trang dashboard của nhà tuyển dụng
@app.route("/dashboard/employer")
def employer_dashboard():
    if session.get("role") != "employer":
        flash("Bạn không có quyền truy cập!", "danger")
        return redirect(url_for("login_employer"))

    employer_id = session["user_id"]
    applications = Application.query.join(Job).filter(Job.employer_id == employer_id).all()
    return render_template("employer_dashboard.html", applications=applications)


# ============================
# Đăng xuất
# ============================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

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