import asyncio
import uuid
from datetime import datetime
from io import BytesIO
import cloudinary.uploader
import requests
from playwright.async_api import async_playwright
from flask import Blueprint, current_app, request, flash, url_for, redirect, render_template, Response
from flask_login import login_required, current_user
from app.extensions import db
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models import Application, CVHistory
from werkzeug.utils import secure_filename

cv_bp = Blueprint('cv', __name__, url_prefix='/cv')


# ===== Helper =====
async def html_to_pdf_bytes(html_str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_str, wait_until='networkidle')
        pdf_bytes = await page.pdf(format="A4", print_background=True)
        await browser.close()
        return pdf_bytes

# ===== Routes =====
@cv_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_cv():
    if not current_user.candidate_profile:
        flash("Hồ sơ ứng viên chưa được tạo", "danger")
        return redirect(url_for('candidate.edit_profile'))

    if request.method == 'GET':
        return render_template('cv/create_cv.html')

    data = {key: request.form.get(key) for key in [
        'full_name', 'email', 'phone', 'address', 'career_objective',
        'experience', 'education', 'skills', 'certifications', 'hobbies', 'template'
    ]}

    if not data['full_name'] or data['full_name'].strip() == '':
        flash("Họ và tên không được để trống", "danger")
        return redirect(url_for('cv.create_cv'))

    html_str = render_template(f'cv/{data["template"]}.html', cv=data)
    pdf_bytes = asyncio.run(html_to_pdf_bytes(html_str))

    try:
        public_id = f'cv_{current_user.id}_{uuid.uuid4().hex}'
        result = cloudinary.uploader.upload(
            BytesIO(pdf_bytes),
            resource_type="raw",
            public_id=public_id,
        )
        current_app.logger.debug("Cloudinary upload result: %s", result)
    except Exception as e:
        current_app.logger.exception("Cloudinary upload failed: %s", str(e))
        flash(f"Tạo CV thất bại: {str(e)}", "danger")
        return redirect(url_for('candidate.profile'))

    cv = CVHistory(
        candidate_id=current_user.candidate_profile.id,
        cv_name=data['full_name'].strip(),
        filename=result['public_id'],
        public_url=result['secure_url'],
        template=data['template']
    )
    db.session.add(cv)
    db.session.commit()
    flash("Tạo CV thành công", "success")
    return redirect(url_for('candidate.profile'))

@cv_bp.route('/view/<int:cv_id>')
@login_required
def view(cv_id):
    cv = CVHistory.query.get_or_404(cv_id)
    if cv.candidate_id != current_user.candidate_profile.id:
        flash("Không có quyền xem CV này", "danger")
        return redirect(url_for('candidate.profile'))

    if not cv.public_url:
        current_app.logger.error("No public_url for CV: id=%s", cv.id)
        flash("CV không có URL hợp lệ", "danger")
        return redirect(url_for('candidate.profile'))

    try:
        current_app.logger.debug("Viewing CV: id=%s, url=%s", cv.id, cv.public_url)
        r = requests.get(cv.public_url, stream=True, timeout=10)
        if r.status_code != 200:
            current_app.logger.error("Failed to fetch CV from Cloudinary: status=%s, url=%s, reason=%s",
                                    r.status_code, cv.public_url, r.reason)
            flash(f"Không thể xem CV: {r.reason}", "danger")
            return redirect(url_for('candidate.profile'))

        filename = secure_filename(f"{cv.cv_name}.pdf" if not cv.cv_name.endswith('.pdf') else cv.cv_name)
        return Response(
            r.content,
            mimetype='application/pdf',
            headers={"Content-Disposition": f"inline;filename*=UTF-8''{filename}"}
        )
    except Exception as e:
        current_app.logger.exception("View failed for CV: id=%s, error=%s", cv.id, str(e))
        flash(f"Xem CV thất bại: {str(e)}", "danger")
        return redirect(url_for('candidate.profile'))

@cv_bp.route('/download/<int:cv_id>')
@login_required
def download(cv_id):
    cv = CVHistory.query.get_or_404(cv_id)
    if cv.candidate_id != current_user.candidate_profile.id:
        flash("Không có quyền tải CV này", "danger")
        return redirect(url_for('candidate.profile'))

    if not cv.public_url:
        current_app.logger.error("No public_url for CV: id=%s", cv.id)
        flash("CV không có URL hợp lệ", "danger")
        return redirect(url_for('candidate.profile'))

    try:
        current_app.logger.debug("Downloading CV: id=%s, url=%s", cv.id, cv.public_url)
        r = requests.get(cv.public_url, stream=True, timeout=10)
        if r.status_code != 200:
            current_app.logger.error("Failed to fetch CV from Cloudinary: status=%s, url=%s, reason=%s",
                                    r.status_code, cv.public_url, r.reason)
            flash(f"Không thể tải CV từ Cloudinary: {r.reason}", "danger")
            return redirect(url_for('candidate.profile'))

        filename = secure_filename(f"{cv.cv_name}.pdf" if not cv.cv_name.endswith('.pdf') else cv.cv_name)
        return Response(
            r.content,
            mimetype='application/pdf',
            headers={"Content-Disposition": f"attachment;filename*=UTF-8''{filename}"}
        )
    except Exception as e:
        current_app.logger.exception("Download failed for CV: id=%s, error=%s", cv.id, str(e))
        flash(f"Tải CV thất bại: {str(e)}", "danger")
        return redirect(url_for('candidate.profile'))

@cv_bp.route('/delete/<int:cv_id>', methods=['POST'])
@login_required
def delete(cv_id):
    cv = CVHistory.query.get_or_404(cv_id)
    if cv.candidate_id != current_user.candidate_profile.id:
        flash("Không có quyền xóa CV này", "danger")
        return redirect(url_for('candidate.profile'))

    if cv.is_used():
        flash("CV đang được sử dụng trong ứng tuyển chưa bị từ chối, không thể xóa", "danger")
        return redirect(url_for('candidate.profile'))

    current_app.logger.debug("Deleting CV: id=%s, filename=%s", cv.id, cv.filename)
    try:
        # Set cv_id to NULL in applications where status = 'rejected'
        Application.query.filter_by(cv_id=cv.id).filter(Application.status == 'rejected').update({'cv_id': None})
        db.session.commit()

        # Delete CV from Cloudinary
        destroy_result = cloudinary.uploader.destroy(cv.filename, resource_type="raw")
        current_app.logger.debug("Cloudinary destroy result: %s", destroy_result)
        if destroy_result.get('result') != 'ok' and destroy_result.get('result') != 'not found':
            current_app.logger.error("Cloudinary destroy failed: %s", destroy_result)
            flash("Xóa file CV trên Cloudinary thất bại", "danger")
            return redirect(url_for('candidate.profile'))
    except Exception as e:
        current_app.logger.exception("Cloudinary destroy failed: %s", str(e))
        flash(f"Xóa file CV thất bại: {str(e)}", "danger")
        return redirect(url_for('candidate.profile'))

    db.session.delete(cv)
    db.session.commit()
    flash("Xóa CV thành công", "success")
    return redirect(url_for('candidate.profile'))