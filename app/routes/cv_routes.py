import os
import uuid
from datetime import datetime
from flask import Blueprint, current_app, request, jsonify, send_file, flash, url_for
from flask_login import login_required, current_user
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont  # Chỉ cần này cho TrueType
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.rl_config import warnOnMissingFontGlyphs  # Để tắt warning missing glyphs
from werkzeug.utils import secure_filename, redirect
from io import BytesIO
from app.extensions import db
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from textwrap import wrap  # Giữ nguyên, nhưng wrap hỗ trợ Unicode ok ở Python 3

cv_bp = Blueprint('cv', __name__, url_prefix='/cv')

class CVHistory(db.Model):
    __tablename__ = 'cv_history'
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    cv_name = Column(String(100), nullable=False)
    filename = Column(String(255), nullable=False)
    template = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship('Candidate', backref=db.backref('cvs', order_by="desc(CVHistory.created_at)"))

def ensure_dirs():
    uploads = os.path.join(current_app.root_path, 'static', 'uploads')
    cvs = os.path.join(current_app.root_path, 'static', 'cvs')
    os.makedirs(uploads, exist_ok=True)
    os.makedirs(cvs, exist_ok=True)
    return uploads, cvs

def generate_pdf(data):
    """Tạo PDF bằng ReportLab, trả về bytes"""
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin

    # Tắt warning missing glyphs (nếu font thiếu gì đó)
    warnOnMissingFontGlyphs = 0

    # Đường dẫn font (thay Inter bằng DejaVuSans - hỗ trợ tốt tiếng Việt)
    font_dir = os.path.join(current_app.root_path, 'static', 'fonts')  # Sửa path tương đối để linh hoạt hơn

    # Đăng ký các variant font DejaVuSans (chỉ cần nếu dùng bold/italic, nhưng ở code bạn dùng Regular thôi)
    for font_name, file_name in [
        ('DejaVuSans', 'DejaVuSans.ttf'),
        ('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'),
        ('DejaVuSans-Oblique', 'DejaVuSans-Oblique.ttf'),
        ('DejaVuSans-BoldOblique', 'DejaVuSans-BoldOblique.ttf')
    ]:
        font_path = os.path.join(font_dir, file_name)
        if not os.path.isfile(font_path):
            raise FileNotFoundError(f"Font not found: {font_path}")
        pdfmetrics.registerFont(TTFont(font_name, font_path))

    # Optional: Đăng ký family để dùng <b>, <i> nếu cần sau này
    pdfmetrics.registerFontFamily('DejaVuSans', normal='DejaVuSans', bold='DejaVuSans-Bold', italic='DejaVuSans-Oblique', boldItalic='DejaVuSans-BoldOblique')

    def draw_text(title, text, y_pos):
        c.setFont("DejaVuSans-Bold", 12)  # Dùng bold cho title để nổi bật
        c.drawString(margin, y_pos, f"{title}:")
        y_pos -= 15
        c.setFont("DejaVuSans", 10)  # Regular cho nội dung
        for line in wrap(text or '-', 75):  # wrap hỗ trợ Unicode
            c.drawString(margin + 10, y_pos, line)
            y_pos -= 12
        return y_pos - 10

    # Đảm bảo data là Unicode (Python 3 mặc định ok, nhưng để chắc)
    y = draw_text("Họ và tên", data.get('full_name', ''), y)
    y = draw_text("Email", data.get('email', ''), y)
    y = draw_text("Điện thoại", data.get('phone', ''), y)
    y = draw_text("Địa chỉ", data.get('address', ''), y)
    y = draw_text("Mục tiêu nghề nghiệp", data.get('career_objective', ''), y)
    y = draw_text("Kinh nghiệm", data.get('experience', ''), y)
    y = draw_text("Học vấn", data.get('education', ''), y)
    y = draw_text("Kỹ năng", data.get('skills', ''), y)
    y = draw_text("Chứng chỉ", data.get('certifications', ''), y)
    y = draw_text("Sở thích", data.get('hobbies', ''), y)

    c.showPage()
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

@cv_bp.route('/create', methods=['POST'])
@login_required
def create_cv():
    if getattr(current_user, 'role', None) != 'candidate':
        return jsonify({'message': 'Chỉ ứng viên mới tạo CV'}), 403

    # Lấy dữ liệu từ form hoặc profile
    data = {
        'full_name': request.form.get('full_name') or getattr(current_user.candidate_profile, 'full_name', ''),
        'email': request.form.get('email') or getattr(current_user, 'email', ''),
        'phone': request.form.get('phone') or getattr(current_user.candidate_profile, 'phone', ''),
        'address': request.form.get('address') or getattr(current_user.candidate_profile, 'address', ''),
        'career_objective': request.form.get('career_objective') or getattr(current_user.candidate_profile, 'career_objective', ''),
        'experience': request.form.get('experience') or getattr(current_user.candidate_profile, 'experience', ''),
        'education': request.form.get('education') or getattr(current_user.candidate_profile, 'education', ''),
        'skills': request.form.get('skills') or getattr(current_user.candidate_profile, 'skills', ''),
        'certifications': request.form.get('certifications') or getattr(current_user.candidate_profile, 'certifications', ''),
        'hobbies': request.form.get('hobbies') or getattr(current_user.candidate_profile, 'hobbies', ''),
        'template': request.form.get('template', 'default')
    }

    # Tạo PDF
    try:
        pdf_buffer = generate_pdf(data)
    except Exception as e:
        current_app.logger.exception("Error generating PDF")
        return jsonify({'message': 'Lỗi khi tạo PDF', 'detail': str(e)}), 500

    # Lưu thư mục
    try:
        _, cvs_dir = ensure_dirs()
    except Exception as e:
        current_app.logger.exception("ensure_dirs failed")
        return jsonify({'message': 'Không thể tạo thư mục lưu CV', 'detail': str(e)}), 500

    safe_name = secure_filename(data['full_name'])[:50] or 'candidate'
    out_filename = f'cv_{current_user.id}_{uuid.uuid4().hex}_{safe_name}.pdf'
    out_path = os.path.join(cvs_dir, out_filename)

    # Ghi file ra disk
    try:
        with open(out_path, 'wb') as f:
            f.write(pdf_buffer.getbuffer())
    except Exception as e:
        current_app.logger.exception("Failed to write PDF to disk")
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=f'CV-{safe_name}.pdf', mimetype='application/pdf')

    # Lưu lịch sử vào DB
    try:
        ch = CVHistory(candidate_id=current_user.candidate_profile.id, filename=out_filename, template=data['template'])
        db.session.add(ch)
        db.session.commit()
    except Exception:
        current_app.logger.exception("Could not save CVHistory")

    # Gửi file cho client
    try:
        return send_file(out_path, as_attachment=True, download_name=f'CV-{safe_name}.pdf', mimetype='application/pdf')
    except Exception:
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=f'CV-{safe_name}.pdf', mimetype='application/pdf')

@cv_bp.route('/download-latest', methods=['GET'])
@login_required
def download_latest_cv():
    try:
        last = CVHistory.query.filter_by(candidate_id=current_user.candidate_profile.id).order_by(CVHistory.created_at.desc()).first()
        if not last:
            return jsonify({'message': 'Không tìm thấy CV'}), 404
        file_path = os.path.join(current_app.root_path, 'static', 'cvs', last.filename)
        if not os.path.exists(file_path):
            return jsonify({'message': 'File không tồn tại'}), 404
        return send_file(file_path, as_attachment=True, download_name=last.filename, mimetype='application/pdf')
    except Exception:
        current_app.logger.exception('download_latest error')
        return jsonify({'message': 'Lỗi khi tải CV'}), 500

@cv_bp.route('/view/<int:cv_id>')
@login_required
def view(cv_id):
    cv = CVHistory.query.get_or_404(cv_id)
    # Kiểm tra quyền: chỉ owner mới xem
    if cv.candidate_id != current_user.candidate_profile.id:
        flash("Không có quyền xem CV này", "danger")
        return redirect(url_for('candidate.profile'))
    file_path = os.path.join(current_app.root_path, 'static', 'cvs', cv.filename)
    if not os.path.exists(file_path):
        flash("File CV không tồn tại", "danger")
        return redirect(url_for('candidate.profile'))
    return send_file(file_path, as_attachment=False)  # False để mở trực tiếp trong browser

@cv_bp.route('/download/<int:cv_id>')
@login_required
def download(cv_id):
    cv = CVHistory.query.get_or_404(cv_id)
    if cv.candidate_id != current_user.candidate_profile.id:
        flash("Không có quyền tải CV này", "danger")
        return redirect(url_for('candidate.profile'))
    file_path = os.path.join(current_app.root_path, 'static', 'cvs', cv.filename)
    if not os.path.exists(file_path):
        flash("File CV không tồn tại", "danger")
        return redirect(url_for('candidate.profile'))
    return send_file(file_path, as_attachment=True, download_name=cv.filename)

@cv_bp.route('/delete/<int:cv_id>', methods=['POST'])
@login_required
def delete(cv_id):
    cv = CVHistory.query.get_or_404(cv_id)
    if cv.candidate_id != current_user.candidate_profile.id:
        flash("Không có quyền xóa CV này", "danger")
        return redirect(url_for('candidate.profile'))
    # Xóa file
    file_path = os.path.join(current_app.root_path, 'static', 'cvs', cv.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    # Xóa record DB
    db.session.delete(cv)
    db.session.commit()
    flash("Xóa CV thành công", "success")
    return redirect(url_for('candidate.profile'))
