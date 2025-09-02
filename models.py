from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()


# Bảng hồ sơ ứng viên (thông tin chi tiết + CV)
class CandidateProfile(db.Model,UserMixin):
    __tablename__ = "candidate_profile"
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidate.id"), nullable=False)
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    cv_file = db.Column(db.String(200))  # đường dẫn file CV

# Bảng Ứng viên
class Candidate(db.Model,UserMixin):
    __tablename__ = "candidate"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Hồ sơ CV liên kết 1-1
    profile = db.relationship("CandidateProfile", backref="candidate", uselist=False)

    # Ứng tuyển nhiều công việc
    applications = db.relationship("Application", backref="candidate", lazy=True)


# Bảng nhà tuyển dụng
class Employer(db.Model,UserMixin):
    __tablename__ = "employer"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))

    # Nhà tuyển dụng đăng nhiều tin tuyển dụng
    jobs = db.relationship("Job", backref="employer", lazy=True)


# Bảng Job: tin tuyển dụng
class Job(db.Model):
    __tablename__ = "job"
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employer.id"), nullable=False)

    # Thông tin chung
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(150))
    experience_required = db.Column(db.String(100))
    deadline = db.Column(db.Date)

    # Nội dung chi tiết
    description = db.Column(db.Text, nullable=False)   # Mô tả công việc
    requirements = db.Column(db.Text)                  # Yêu cầu ứng viên
    benefits = db.Column(db.Text)                      # Quyền lợi
    working_time = db.Column(db.String(200))
    address = db.Column(db.String(300))

    # Thu nhập
    salary = db.Column(db.String(100))                 # 15-20 triệu
    base_salary = db.Column(db.String(100))            # 9-12 triệu
    job_type = db.Column(db.String(50))                # Full-time, Part-time, ...

    # Trạng thái
    status = db.Column(db.String(50), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Hồ sơ ứng tuyển
    applications = db.relationship("Application", backref="job", lazy=True)


# Bảng Application: hồ sơ ứng tuyển
class Application(db.Model,UserMixin):
    __tablename__ = "application"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidate.id"), nullable=False)
    cv_file = db.Column(db.String(200))
    status = db.Column(db.String(50), default="pending")  # pending, accepted, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
