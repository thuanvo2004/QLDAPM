import os
from datetime import datetime

from flask import current_app, app

import cloudinary
import cloudinary.uploader
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import exc

from app.models import User, Candidate, Employer, Message
from app.extensions import db, mail
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
        current_app.logger.debug("Form validated successfully. Processing employer registration.")
        if User.query.filter_by(email=form.email.data).first():
            flash("Email đã được đăng ký!", "danger")
            return render_template("auth/register_employer.html", form=form)

        user = User(email=form.email.data, role="employer")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        current_app.logger.debug("User created with ID: %s", user.id)

        logo_url = None
        if form.logo.data:
            current_app.logger.debug("Logo file detected: %s, filename: %s", type(form.logo.data), getattr(form.logo.data, 'filename', 'No filename'))
            try:
                upload_result = cloudinary.uploader.upload(
                    form.logo.data,
                    folder="jobnest",
                    resource_type="image"
                )
                logo_url = upload_result.get("secure_url")
                current_app.logger.debug("Cloudinary upload result: %s", upload_result)
                if not logo_url:
                    current_app.logger.error("Cloudinary upload succeeded but no secure_url in response.")
                    flash("Tải logo thất bại: Không nhận được URL từ Cloudinary.", "danger")
            except Exception as e:
                current_app.logger.exception("Cloudinary upload failed: %s", str(e))
                flash(f"Tải logo thất bại: {str(e)}", "danger")
        else:
            current_app.logger.debug("No logo file provided in form.")

        employer = Employer(
            user_id=user.id,
            company_name=form.company_name.data,
            phone=form.phone.data,
            industry=form.industry.data,
            company_size=form.company_size.data,
            address=form.address.data,
            city=form.city.data,
            website=form.website.data,
            description=form.description.data,
            founded_year=form.founded_year.data,
            tax_code=form.tax_code.data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            logo=logo_url
        )
        db.session.add(employer)
        db.session.commit()
        current_app.logger.debug("Employer profile created with ID: %s, logo: %s", employer.id, logo_url)

        flash("Đăng ký nhà tuyển dụng thành công, vui lòng đăng nhập!", "success")
        return redirect(url_for("auth.login"))

    current_app.logger.debug("Form not validated or GET request. Rendering form.")
    return render_template("auth/register_employer.html", form=form)


@auth_bp.route('/register')
def register():
    return render_template('register_choice.html')  # Có 2 nút: Candidate / Employer