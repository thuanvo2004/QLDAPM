from app import app, db  # import app Flask và db SQLAlchemy

with app.app_context():  # mở context của app
    # XÓA hết bảng
    db.drop_all()

    # TẠO lại bảng
    db.create_all()

    print("✅ Đã xóa và tạo lại toàn bộ bảng!")
