# file: app/__init__.py
from flask import Flask
from flask_login import LoginManager
from .extensions import db, login_manager
from .routes.auth_routes import auth_bp
from .routes.job_routes import job_bp
from .routes.candidate_routes import candidate_bp
from .routes.employer_routes import employer_bp
from .models import User
from .routes.main import main_bp



def create_app():
    """Tạo và cấu hình Flask app"""
    app = Flask(__name__)

    # Cấu hình cơ bản
    app.config['SECRET_KEY'] ="423a03ab3b1aaedc668243332aec4eb92b1fcbcd032702a4fa60f3bfe0f53fba"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:admin@localhost:3306/job?charset=utf8mb4'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Khởi tạo extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Cấu hình Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def format_salary(value):
        if not value:
            return "Thỏa thuận"
        # Giả sử value là số nguyên
        return f"{value:,.0f} VNĐ"

    # Đăng ký filter
    app.jinja_env.filters['fmt_salary'] = format_salary

    # Đăng ký blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(job_bp, url_prefix='/jobs')
    app.register_blueprint(candidate_bp, url_prefix='/candidate')
    app.register_blueprint(employer_bp, url_prefix='/employer')
    app.register_blueprint(main_bp,url_prefix='/')

    # Tạo bảng nếu chưa có (chỉ dùng dev, không dùng production)
    with app.app_context():
        db.create_all()

    return app



