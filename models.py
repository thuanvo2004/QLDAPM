from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

# Khởi tạo SQLAlchemy
db = SQLAlchemy()


# =========================
# Hồ sơ ứng viên (1-1 với Candidate)
# =========================
class CandidateProfile(db.Model):
    __tablename__ = "candidate_profile"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidate.id"), nullable=False)
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    cv_file = db.Column(db.String(200))  # đường dẫn file CV

    def __repr__(self):
        return f"<CandidateProfile {self.id} - {self.phone}>"


# =========================
# Ứng viên (user login loại candidate)
# =========================
class Candidate(db.Model, UserMixin):
    __tablename__ = "candidate"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Quan hệ 1-1 với CandidateProfile
    profile = db.relationship("CandidateProfile", backref="candidate", uselist=False)

    # Quan hệ nhiều: ứng tuyển và lưu job
    applications = db.relationship("Application", backref="candidate", lazy=True)
    saved_jobs = db.relationship("SavedJob", backref="candidate", lazy=True)

    def __repr__(self):
        return f"<Candidate {self.id} - {self.name}>"


# =========================
# Nhà tuyển dụng (Employer)
# =========================
class Employer(db.Model, UserMixin):
    __tablename__ = "employer"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # tài khoản login
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Thông tin công ty
    company_name = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))

    # Quan hệ 1-n với Job
    jobs = db.relationship("Job", backref="employer", lazy=True)

    def __repr__(self):
        return f"<Employer {self.id} - {self.company_name}>"


# =========================
# Tin tuyển dụng (Job)
# =========================
class Job(db.Model):
    __tablename__ = "job"

    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employer.id"), nullable=False)

    # Thông tin chính
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(150))
    category = db.Column(db.String(150))
    level = db.Column(db.String(100))
    job_type = db.Column(db.String(50))  # Full-time, Part-time

    # Thời gian
    working_time = db.Column(db.Text)
    deadline = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Nội dung
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    benefits = db.Column(db.Text)

    # Lương
    salary = db.Column(db.String(100))
    base_salary = db.Column(db.String(100))

    # Thông tin thêm
    address = db.Column(db.String(300))
    degree = db.Column(db.String(100))
    age = db.Column(db.String(50))

    # Trạng thái
    status = db.Column(db.String(50), default="active")

    # Quan hệ
    applications = db.relationship("Application", backref="job", lazy=True)
    saved_by = db.relationship("SavedJob", backref="job", lazy=True)

    def __repr__(self):
        return f"<Job {self.id} - {self.title}>"

    @property
    def company_name(self):
        """Lấy tên công ty từ employer"""
        return self.employer.company_name if self.employer else ""


# =========================
# Hồ sơ ứng tuyển
# =========================
class Application(db.Model):
    __tablename__ = "application"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidate.id"), nullable=False)

    cv_file = db.Column(db.String(200))
    status = db.Column(db.String(50), default="pending")  # pending, accepted, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Application {self.id} - Job {self.job_id} - Candidate {self.candidate_id}>"


# =========================
# Tin đã lưu
# =========================
class SavedJob(db.Model):
    __tablename__ = "saved_job"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidate.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SavedJob {self.id} - Candidate {self.candidate_id} - Job {self.job_id}>"
