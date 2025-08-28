from string import digits
import re
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt

# ============================
# Hàm trích xuất số nguyên từ chuỗi, trả về None nếu không có số
# ============================
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

# ============================
# Hàm lọc và sắp xếp việc làm dựa trên các tiêu chí
# ============================
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

# ============================
# Khởi tạo Flask app
# ============================
app = Flask(__name__)
app.secret_key = "jobportal_secret"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
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

# ============================
# Quản lý login
# ============================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ============================
# Bảng User
# ============================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# ============================
# Bảng Job
# ============================
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    salary = db.Column(db.Integer, nullable=True)
    job_type = db.Column(db.String(50), nullable=True)
    featured = db.Column(db.Boolean, default=False)

# ============================
# Tải user
# ============================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================
# Trang chủ
# ============================
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

# ============================
# Đăng ký
# ============================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        if User.query.filter_by(username=username).first():
            flash("⚠️ Tên đăng nhập đã tồn tại!")
            return redirect(url_for('register'))

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("✅ Đăng ký thành công, mời bạn đăng nhập!")
        return redirect(url_for('login'))

    return render_template('register.html')

# ============================
# Đăng nhập
# ============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("✅ Đăng nhập thành công!")
            return redirect(url_for('index'))
        else:
            flash("❌ Sai tài khoản hoặc mật khẩu!")

    return render_template('login.html')

# ============================
# Đăng xuất
# ============================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("🚪 Bạn đã đăng xuất!")
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

# ============================
# Xem chi tiết việc làm
# ============================
@app.route('/jobs/<int:id>')
def job_detail(id):
    job = Job.query.get_or_404(id)
    return render_template('jobs.html', job=job)

# ============================
# Chạy server
# ============================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)