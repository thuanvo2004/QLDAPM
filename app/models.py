from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash

# ======================================================
# Bảng User (tài khoản đăng nhập chung cho Candidate/Employer)
# ======================================================
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "candidate" | "employer" | "admin"
    isPremiumActive = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Liên kết One-to-One với Candidate/Employer
    candidate_profile = db.relationship("Candidate", back_populates="user", uselist=False)
    employer_profile = db.relationship("Employer", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User {self.email} - {self.role}>"

    # helper
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ======================================================
# Bảng Candidate (Ứng viên)
# ======================================================
class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    education = db.Column(db.String(200))  # học vấn cao nhất
    major = db.Column(db.String(200))      # ngành học
    experience_years = db.Column(db.Integer, default=0)
    experience_months = db.Column(db.Integer, default=0)
    current_position = db.Column(db.String(200))
    expected_position = db.Column(db.String(200))
    expected_salary = db.Column(db.Integer)
    skills = db.Column(db.Text)            # list hoặc JSON
    languages = db.Column(db.Text)         # list hoặc JSON
    career_objective = db.Column(db.Text)
    cv_file = db.Column(db.String(255))
    avatar = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="candidate_profile")
    applications = db.relationship("Application", back_populates="candidate")
    saved_jobs = db.relationship("SavedJob", back_populates="candidate")
    notifications = db.relationship("Notification", back_populates="candidate")

    @property
    def experience_str(self):
        """Trả về chuỗi kinh nghiệm dạng 'X năm Y tháng'"""
        years = self.experience_years or 0
        months = self.experience_months or 0
        parts = []
        if years > 0:
            parts.append(f"{years} năm")
        if months > 0:
            parts.append(f"{months} tháng")
        return " ".join(parts) if parts else "-"

    def __repr__(self):
        return f"<Candidate {self.full_name}>"


# ======================================================
# Bảng Employer (Nhà tuyển dụng)
# ======================================================
class Employer(db.Model):
    __tablename__ = "employers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    company_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    industry = db.Column(db.String(200))
    company_size = db.Column(db.String(50))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    logo = db.Column(db.String(255))
    founded_year = db.Column(db.Integer)
    tax_code = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="employer_profile")
    jobs = db.relationship("Job", back_populates="employer")
    notifications = db.relationship("Notification", back_populates="employer")

    def __repr__(self):
        return f"<Employer {self.company_name}>"


# ======================================================
# Bảng Job (Tin tuyển dụng)
# ======================================================
class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employers.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    benefits = db.Column(db.Text)
    job_type = db.Column(db.String(50))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    currency = db.Column(db.String(10), default="VND")

    # Địa chỉ chi tiết
    city = db.Column(db.String(100))          # thành phố
    district = db.Column(db.String(100))      # quận/huyện
    street_address = db.Column(db.String(200)) # số nhà, đường

    # Thời gian làm việc
    work_start_time = db.Column(db.Time)      # giờ bắt đầu làm việc
    work_end_time = db.Column(db.Time)        # giờ kết thúc làm việc
    working_days = db.Column(db.String(50))   # ví dụ: "T2-T6", "T2-T7"

    deadline = db.Column(db.Date)             # hạn nộp hồ sơ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    remote_option = db.Column(db.String(20))  # Onsite | Remote | Hybrid
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    interview_date = db.Column(db.DateTime)

    employer = db.relationship("Employer", back_populates="jobs")
    applications = db.relationship("Application", back_populates="job")
    saved_jobs = db.relationship("SavedJob", back_populates="job")
    categories = db.relationship("JobCategory", secondary="job_category_association", back_populates="jobs")

    def __repr__(self):
        return f"<Job {self.title}>"

# ======================================================
# Bảng Application (Hồ sơ ứng tuyển)
# ======================================================
class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    cv_id = db.Column(db.Integer, db.ForeignKey('cv_history.id'), nullable=True)

    status = db.Column(db.String(20), default="pending")  # pending, reviewed, accepted, rejected
    cover_letter = db.Column(db.Text)

    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    feedback = db.Column(db.Text)
    interview_scheduled_at = db.Column(db.DateTime)

    candidate = db.relationship("Candidate", back_populates="applications")
    job = db.relationship("Job", back_populates="applications")

    def __repr__(self):
        return f"<Application Candidate={self.candidate_id} Job={self.job_id}>"


# ======================================================
# Bảng SavedJob (ứng viên lưu tin tuyển dụng)
# ======================================================
class SavedJob(db.Model):
    __tablename__ = "saved_jobs"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    candidate = db.relationship("Candidate", back_populates="saved_jobs")
    job = db.relationship("Job", back_populates="saved_jobs")


# ======================================================
# Bảng JobCategory (ngành nghề)
# ======================================================
class JobCategory(db.Model):
    __tablename__ = "job_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    jobs = db.relationship("Job", secondary="job_category_association", back_populates="categories")


# Bảng phụ many-to-many Job <-> JobCategory
job_category_association = db.Table(
    "job_category_association",
    db.Column("job_id", db.Integer, db.ForeignKey("jobs.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("job_categories.id"), primary_key=True)
)

# ======================================================
# Bảng Notification (thông báo)
# ======================================================
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(50), default="system")

    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"))
    employer_id = db.Column(db.Integer, db.ForeignKey("employers.id"))

    candidate = db.relationship("Candidate", back_populates="notifications")
    employer = db.relationship("Employer", back_populates="notifications")


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user1 = db.relationship("User", foreign_keys=[user1_id])
    user2 = db.relationship("User", foreign_keys=[user2_id])
    messages = db.relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)  # <-- thêm
    content = db.Column(db.Text, nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attachment_url = db.Column(db.String(255))

    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="received_messages")
    conversation = db.relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.sender_id} → {self.receiver_id}>"

# ======================================================
# Bảng Payment (thanh toán)
# ======================================================
class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gateway = db.Column(db.String(100), nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    account_number = db.Column(db.String(100), nullable=True)
    sub_account = db.Column(db.String(250), nullable=True)
    amount_in = db.Column(db.Numeric(20, 2), nullable=False, default=0.00)
    amount_out = db.Column(db.Numeric(20, 2), nullable=False, default=0.00)
    accumulated = db.Column(db.Numeric(20, 2), nullable=False, default=0.00)
    code = db.Column(db.String(250), nullable=True)
    transaction_content = db.Column(db.Text, nullable=True)
    reference_number = db.Column(db.String(255), nullable=True)
    body = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Foreign key to link payment with user (employer)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", backref="payments")

    def __repr__(self):
        return f"<Payment {self.id} - {self.gateway} - {self.amount_in}>"

# bảng Skills
class Skill(db.Model):
    __tablename__ = "skills"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

# bảng Languages
class Language(db.Model):
    __tablename__ = "languages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

# bảng phụ Candidate <-> Skill
candidate_skill = db.Table(
    "candidate_skill",
    db.Column("candidate_id", db.Integer, db.ForeignKey("candidates.id"), primary_key=True),
    db.Column("skill_id", db.Integer, db.ForeignKey("skills.id"), primary_key=True)
)

# bảng phụ Candidate <-> Language
candidate_language = db.Table(
    "candidate_language",
    db.Column("candidate_id", db.Integer, db.ForeignKey("candidates.id"), primary_key=True),
    db.Column("language_id", db.Integer, db.ForeignKey("languages.id"), primary_key=True)
)



