import cloudinary
from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from .extensions import db, login_manager
from .routes.auth_routes import auth_bp
from .routes.job_routes import job_bp
from .routes.candidate_routes import candidate_bp
from .routes.employer_routes import employer_bp
from .routes.cv_routes import cv_bp
from .routes.payment_routes import payment_bp
from .models import User
from .routes.main import main_bp
from .routes.message import messages_bp
from flask_migrate import Migrate
import os
import logging

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

migrate = Migrate()

def create_app():
    """Tạo và cấu hình Flask app"""
    app = Flask(__name__)

    # Cấu hình cơ bản
    app.config['SECRET_KEY'] = "423a03ab3b1aaedc668243332aec4eb92b1fcbcd032702a4fa60f3bfe0f53fba"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:admin@localhost:3306/job?charset=utf8mb4'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Khởi tạo extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Cấu hình Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def format_salary(value):
        if not value:
            return "Thỏa thuận"
        return f"{value:,.0f} VNĐ"

    # Đăng ký filter
    app.jinja_env.filters['fmt_salary'] = format_salary

    # Đăng ký blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(job_bp, url_prefix='/jobs')
    app.register_blueprint(candidate_bp, url_prefix='/candidate')
    app.register_blueprint(employer_bp, url_prefix='/employer')
    app.register_blueprint(cv_bp, url_prefix='/cv')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(messages_bp, url_prefix='/messages')
    app.register_blueprint(payment_bp, url_prefix='/payment')

    # Tạo bảng nếu chưa có (chỉ dùng dev, không dùng production)
    with app.app_context():
        db.create_all()

    return app