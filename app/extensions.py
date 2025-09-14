from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
# from flask_bcrypt import Bcrypt  # Temporarily commented out
# from flask_mail import Mail  # Temporarily commented out

# Khởi tạo extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
# bcrypt = Bcrypt()  # Temporarily commented out
# mail = Mail()  # Temporarily commented out

# Cấu hình login manager
login_manager.login_view = "auth.login"   # nếu chưa login thì redirect về /auth/login
login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
login_manager.login_message_category = "info"