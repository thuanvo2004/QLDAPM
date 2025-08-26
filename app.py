# ============================
# Import các thư viện
# ============================
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt

# ============================
# Khởi tạo Flask app
# ============================
app = Flask(__name__)
app.secret_key = "jobportal_secret"   # Khóa bí mật session

# ============================
# Cấu hình database
# ============================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

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
    jobs = Job.query.all()
    return render_template('index.html', jobs=jobs, user=current_user)

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
# Trang thêm việc làm (chỉ cho user đã login)
# ============================
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_job():
    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        location = request.form['location']
        description = request.form['description']

        new_job = Job(title=title, company=company, location=location, description=description)
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
