import json
import os
import re

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField, DateField, \
    TimeField, DateTimeField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional,URL,NumberRange
from flask_wtf.file import FileField, FileAllowed
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, Length, EqualTo

def strip_to_int(value):
    if value is None:
        return None
    s = str(value).strip()
    if s == '':
        return None
    digits = re.sub(r'[^\d]', '', s)
    if digits == '':
        return None
    try:
        return int(digits)
    except ValueError:
        return None

# Load provinces from JSON file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(BASE_DIR,'static', 'data', 'provinces.json')
try:
    with open(json_path, 'r', encoding='utf-8') as f:
        provinces_data = json.load(f)
        if not isinstance(provinces_data, dict) or 'provinces' not in provinces_data:
            raise ValueError("provinces.json must contain a 'provinces' key with a list of province objects")
        PROVINCE_CHOICES = [(province['id'], province['name']) for province in provinces_data['provinces']]
except FileNotFoundError:
    PROVINCE_CHOICES = [("Unknown", "Unknown")]  # Fallback
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")
    PROVINCE_CHOICES = [("Unknown", "Unknown")]  # Fallback
except KeyError:
    print("Error: 'provinces' key not found in JSON")
    PROVINCE_CHOICES = [("Unknown", "Unknown")]  # Fallback
except ValueError as e:
    print(f"Error: {e}")
    PROVINCE_CHOICES = [("Unknown", "Unknown")]  # Fallback



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
        ("Full-time","Full-time"),
        ("Part-time","Part-time"),
        ("Internship","Internship"),
        ("Remote","Remote")
    ], validators=[Optional()])

    remote_option = SelectField("Hình thức", choices=[
        ("Onsite","Onsite"), ("Remote","Remote"), ("Hybrid","Hybrid")
    ], validators=[Optional()])

    salary_min = IntegerField("Lương tối thiểu", validators=[Optional()], filters=[strip_to_int])
    salary_max = IntegerField("Lương tối đa", validators=[Optional()], filters=[strip_to_int])
    currency = StringField("Đơn vị", default="VND", validators=[Optional()])

    city = StringField("Thành phố", validators=[DataRequired()])
    district = StringField("Quận/Huyện", validators=[Optional()])
    street_address = StringField("Địa chỉ", validators=[Optional()])

    work_start_time = TimeField("Giờ bắt đầu", format="%H:%M", validators=[Optional()])
    work_end_time = TimeField("Giờ kết thúc", format="%H:%M", validators=[Optional()])
    working_days = StringField("Ngày làm việc", validators=[Optional()])

    deadline = DateField("Hạn nộp", format="%Y-%m-%d", validators=[DataRequired()])
    interview_date = DateField("Ngày phỏng vấn", format="%Y-%m-%d", validators=[DataRequired()])

    submit = SubmitField("Đăng tin")

    def validate(self, extra_validators=None):
        # Chạy validate mặc định trước
        rv = super().validate(extra_validators=extra_validators)
        if not rv:
            return False

        a = self.salary_min.data
        b = self.salary_max.data
        if a is not None and b is not None:
            if a > b:
                self.salary_min.errors.append('Lương tối thiểu không được lớn hơn lương tối đa')
                self.salary_max.errors.append('Lương tối đa phải lớn hơn hoặc bằng lương tối thiểu')
                return False
        return True

class EmployerRegisterForm(FlaskForm):
        email = StringField("Email", validators=[DataRequired(), Email()])
        password = PasswordField("Mật khẩu", validators=[DataRequired(), Length(min=6)])
        confirm_password = PasswordField("Xác nhận mật khẩu", validators=[DataRequired(), EqualTo("password")])
        company_name = StringField("Tên công ty", validators=[DataRequired()])
        phone = StringField("Số điện thoại", validators=[DataRequired()])
        address = StringField("Địa chỉ công ty", validators=[DataRequired()])
        industry = StringField("Ngành nghề", validators=[DataRequired()])
        company_size = StringField("Quy mô công ty", validators=[Optional()])
        logo = FileField(
            "Logo công ty",
            validators=[FileAllowed(['jpg', 'jpeg', 'png'], "Chỉ chấp nhận ảnh JPG/PNG!")]
        )
        website = StringField("Website công ty", validators=[Optional(), URL()])
        city = SelectField("Thành phố", choices=PROVINCE_CHOICES, validators=[DataRequired()])
        founded_year = IntegerField("Năm thành lập", validators=[Optional()])
        tax_code = StringField("Mã số thuế", validators=[Optional()])
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

class NotificationForm(FlaskForm):
    notification_id = HiddenField('Notification ID', validators=[DataRequired()])
    mark_read = SubmitField('Mark as Read')