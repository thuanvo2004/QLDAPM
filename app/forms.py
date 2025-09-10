from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField, DateField, TimeField, DateTimeField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional,URL,NumberRange
from flask_wtf.file import FileField, FileAllowed
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, Length, EqualTo


# Form đăng nhập
class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Mật khẩu", validators=[DataRequired()])
    submit = SubmitField("Đăng nhập")

# Form đăng ký chung (Candidate/Employer)
class RegisterForm(FlaskForm):
    username = StringField("Họ tên / Tên công ty", validators=[DataRequired(), Length(2, 200)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Mật khẩu", validators=[DataRequired(), Length(6, 128)])
    confirm_password = PasswordField("Xác nhận mật khẩu", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Đăng ký")


from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DateField, TimeField, SubmitField
from wtforms.validators import DataRequired, Optional

class JobForm(FlaskForm):
    title = StringField("Tiêu đề", validators=[DataRequired()])
    description = TextAreaField("Mô tả", validators=[DataRequired()])
    requirements = TextAreaField("Yêu cầu", validators=[Optional()])
    benefits = TextAreaField("Quyền lợi", validators=[Optional()])

    job_type = SelectField("Loại công việc", choices=[
        ("full-time","Full-time"),
        ("part-time","Part-time"),
        ("internship","Internship"),
        ("remote","Remote")
    ], validators=[Optional()])

    remote_option = SelectField("Hình thức", choices=[
        ("Onsite","Onsite"), ("Remote","Remote"), ("Hybrid","Hybrid")
    ], validators=[Optional()])

    salary_min = IntegerField("Lương tối thiểu", validators=[Optional()])
    salary_max = IntegerField("Lương tối đa", validators=[Optional()])
    currency = StringField("Đơn vị", default="VND", validators=[Optional()])

    city = StringField("Thành phố", validators=[Optional()])
    district = StringField("Quận/Huyện", validators=[Optional()])
    street_address = StringField("Địa chỉ", validators=[Optional()])

    work_start_time = TimeField("Giờ bắt đầu", format="%H:%M", validators=[Optional()])
    work_end_time = TimeField("Giờ kết thúc", format="%H:%M", validators=[Optional()])
    working_days = StringField("Ngày làm việc", validators=[Optional()])

    deadline = DateField("Hạn nộp", format="%Y-%m-%d", validators=[Optional()])
    interview_date = DateField("Ngày phỏng vấn", format="%Y-%m-%d", validators=[Optional()])

    submit = SubmitField("Đăng tin")

class EmployerRegisterForm(FlaskForm):
        email = StringField("Email", validators=[DataRequired(), Email()])
        password = PasswordField("Mật khẩu", validators=[DataRequired(), Length(min=6)])
        confirm_password = PasswordField("Xác nhận mật khẩu", validators=[DataRequired(), EqualTo("password")])
        company_name = StringField("Tên công ty", validators=[DataRequired()])
        address = StringField("Địa chỉ công ty", validators=[DataRequired()])
        description = TextAreaField("Mô tả công ty")
        submit = SubmitField("Đăng ký Nhà tuyển dụng")

class EmployerProfileForm(FlaskForm):
        company_name = StringField(
            "Tên công ty",
            validators=[DataRequired(), Length(max=200)]
        )
        phone = StringField(
            "Số điện thoại",
            validators=[Optional(), Length(max=20)]
        )
        industry = StringField(
            "Ngành nghề",
            validators=[Optional(), Length(max=200)]
        )
        company_size = StringField(
            "Quy mô công ty",
            validators=[Optional(), Length(max=50)]
        )
        address = StringField(
            "Địa chỉ",
            validators=[Optional(), Length(max=200)]
        )
        city = StringField(
            "Thành phố",
            validators=[Optional(), Length(max=100)]
        )
        website = StringField(
            "Website",
            validators=[Optional(), URL(), Length(max=200)]
        )
        description = TextAreaField(
            "Giới thiệu công ty",
            validators=[Optional(), Length(max=2000)]
        )
        founded_year = IntegerField(
            "Năm thành lập",
            validators=[Optional(), NumberRange(min=1800, max=2100)]
        )
        tax_code = StringField(
            "Mã số thuế",
            validators=[Optional(), Length(max=100)]
        )
        logo = FileField(
            "Logo công ty (jpg, png, gif)",
            validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Chỉ chấp nhận ảnh!')]
        )
        submit = SubmitField("Lưu hồ sơ")