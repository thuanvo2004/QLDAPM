from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Candidate, Employer
from app.extensions import db
from app.forms import RegisterForm, LoginForm, EmployerRegisterForm

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# =======================
# Login
# =======================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash("Bạn đã đăng nhập.", "info")
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Đăng nhập thành công", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        flash("Email hoặc mật khẩu sai", "danger")
    return render_template("auth/login.html", form=form)

# =======================
# Logout
# =======================
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đăng xuất thành công", "success")
    return redirect(url_for("main.index"))

# =======================
# Chọn vai trò đăng ký
# =======================
@auth_bp.route("/register")
def choose_role():
    return render_template("auth/choose_role.html")

# =======================
# Đăng ký Candidate
# =======================
@auth_bp.route("/register/candidate", methods=["GET", "POST"])
def register_candidate():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("Email đã được đăng ký!", "danger")
            return render_template("auth/register_candidate.html", form=form)

        user = User(email=form.email.data, role="candidate")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        candidate = Candidate(user_id=user.id, full_name=form.username.data)
        db.session.add(candidate)
        db.session.commit()

        flash("Đăng ký ứng viên thành công! Vui lòng đăng nhập.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register_candidate.html", form=form)

@auth_bp.route("/register/employer", methods=["GET", "POST"])
def register_employer():
    form = EmployerRegisterForm()
    if form.validate_on_submit():
        # 1. Tạo user với role employer
        user = User(email=form.email.data, role="employer")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # 2. Tạo employer profile liên kết với user
        employer = Employer(
            user_id=user.id,
            company_name=form.company_name.data,
            address=form.address.data,
            description=form.description.data
        )
        db.session.add(employer)
        db.session.commit()

        flash("Đăng ký nhà tuyển dụng thành công, vui lòng đăng nhập!", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register_employer.html", form=form)

@auth_bp.route('/register')
def register():
    return render_template('register_choice.html')  # Có 2 nút: Candidate / Employer
