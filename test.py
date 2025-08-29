from app import app, db

with app.app_context():
    # Xóa tất cả bảng cũ
    db.drop_all()

    # Tạo lại bảng từ models
    db.create_all()

    print("Đã drop và create tất cả bảng thành công!")
