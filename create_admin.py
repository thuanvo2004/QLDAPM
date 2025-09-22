from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # Kiểm tra đã có admin chưa
    admin = User.query.filter_by(email="admin@example.com").first()
    if not admin:
        admin = User(
            email="admin@admin.com",
            role="admin"
        )
        admin.set_password("123456")  # Đặt mật khẩu
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin account created!")
    else:
        print("⚠️ Admin already exists")
