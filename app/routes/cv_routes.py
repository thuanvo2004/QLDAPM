import asyncio
import os
import uuid
from datetime import datetime

from playwright.async_api import async_playwright
from flask import Blueprint, current_app, request, jsonify, send_file, flash, url_for, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename, redirect
from io import BytesIO
from app.extensions import db
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

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

async def html_to_pdf_bytes(html_str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_str, wait_until='networkidle')
        pdf_bytes = await page.pdf(format="A4", print_background=True)
        await browser.close()
        return pdf_bytes

@cv_bp.route('/create', methods=['GET','POST'])
@login_required
def create_cv():
    if request.method == 'GET':
        return render_template('cv/create_cv.html')

    # POST
    data = {
        'full_name': request.form.get('full_name'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'address': request.form.get('address'),
        'career_objective': request.form.get('career_objective'),
        'experience': request.form.get('experience'),
        'education': request.form.get('education'),
        'skills': request.form.get('skills'),
        'certifications': request.form.get('certifications'),
        'hobbies': request.form.get('hobbies'),
        'template': request.form.get('template')
    }

    # Render HTML template
    html_str = render_template(f'cv/{data["template"]}.html', cv=data)

    # HTML -> PDF
    pdf_bytes = asyncio.run(html_to_pdf_bytes(html_str))

    # Lưu vào DB
    cv = CVHistory(candidate_id=current_user.candidate_profile.id,
                   cv_name=data['full_name'],
                   filename=f'{current_user.id}_{uuid.uuid4().hex}.pdf',
                   template=data['template'])
    db.session.add(cv)
    db.session.commit()

    return send_file(BytesIO(pdf_bytes), as_attachment=True, download_name=f'{data["full_name"]}.pdf', mimetype='application/pdf')

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
