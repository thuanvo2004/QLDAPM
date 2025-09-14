from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Mật khẩu", validators=[DataRequired()])
    role = SelectField("Vai trò", choices=[("candidate", "Ứng viên"), ("employer", "Nhà tuyển dụng")])
    submit = SubmitField("Đăng nhập")

class RegisterForm(FlaskForm):
    name = StringField("Họ và tên / Tên công ty", validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Mật khẩu", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Xác nhận mật khẩu", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Đăng ký")

class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Gửi liên kết đặt lại mật khẩu")

class ResetPasswordForm(FlaskForm):
    password = PasswordField("Mật khẩu mới", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Xác nhận mật khẩu", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Đặt lại mật khẩu")

class CandidateProfileForm(FlaskForm):
    full_name = StringField("Họ và tên", validators=[DataRequired()])
    phone = StringField("Số điện thoại")
    resume = TextAreaField("Tóm tắt hồ sơ")
    submit = SubmitField("Lưu thông tin")

class EmployerProfileForm(FlaskForm):
    company_name = StringField("Tên công ty", validators=[DataRequired()])
    phone = StringField("Số điện thoại")
    description = TextAreaField("Mô tả công ty")
    submit = SubmitField("Lưu thông tin")
