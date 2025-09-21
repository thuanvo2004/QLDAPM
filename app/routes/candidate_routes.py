import uuid
from datetime import date

import cloudinary
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.forms import NotificationForm
from app.models import Job, Application, SavedJob, Candidate, Notification,CVHistory
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
import os
from utils.mail_utils import send_email  # đảm bảo import hàm gửi mail

from app.routes.cv_routes import CVHistory

candidate_bp = Blueprint("candidate", __name__, url_prefix="/candidate")


class CsrfForm(FlaskForm):
    pass


@candidate_bp.route("/profile")
@login_required
def profile():
    if current_user.role != "candidate":
        flash("Chỉ ứng viên mới xem profile này", "danger")
        return redirect(url_for("job.list_jobs"))

    candidate = (
        Candidate.query
        .options(joinedload(Candidate.cvs))
        .filter_by(id=current_user.candidate_profile.id)
        .first()
    )
    form = CsrfForm()  # Instantiate CSRF form
    return render_template("candidate/profile.html", candidate=candidate, users=current_user, form=form)

@candidate_bp.route("/apply/<int:job_id>", methods=["GET", "POST"])
@login_required
def apply_job(job_id):
    if current_user.role != "candidate":
        flash("Chỉ ứng viên mới nộp hồ sơ", "danger")
        return redirect(url_for("job.list_jobs"))

    job = Job.query.get_or_404(job_id)
    employer = job.employer

    # Kiểm tra đã nộp chưa
    existing = Application.query.filter_by(
        candidate_id=current_user.candidate_profile.id,
        job_id=job.id
    ).first()
    if existing:
        flash("Bạn đã nộp hồ sơ trước đó", "warning")
        return redirect(url_for("job.job_detail", job_id=job.id))

    # Xử lý CV (lấy từ form hoặc upload)
    cv_id = request.form.get("cv_id")
    uploaded_cv = request.files.get("cv_upload")
    cv = None
    if cv_id:
        cv = CVHistory.query.get_or_404(cv_id)
    elif uploaded_cv:
        # upload lên cloudinary (ví dụ)
        from werkzeug.utils import secure_filename
        import cloudinary.uploader, uuid
        filename = secure_filename(uploaded_cv.filename)
        result = cloudinary.uploader.upload(
            uploaded_cv,
            resource_type="raw",
            public_id=f'cv_{current_user.id}_{uuid.uuid4().hex}',
        )
        cv = CVHistory(
            candidate_id=current_user.candidate_profile.id,
            cv_name=filename.rsplit('.', 1)[0],
            filename=result['public_id'],
            public_url=result['secure_url'],
        )
        db.session.add(cv)
        db.session.commit()

    # Tạo application
    application = Application(
        candidate_id=current_user.candidate_profile.id,
        job_id=job.id,
        cv_id=cv.id if cv else None
    )
    db.session.add(application)
    db.session.commit()

    # 1️⃣ Email cho ứng viên
    body_candidate = render_template(
        "emails/job_applied_candidate.html",
        candidate_name=current_user.candidate_profile.full_name,
        job_title=job.title,
        company_name=employer.company_name
    )
    try:
     send_email(
        subject=f"Xác nhận nộp hồ sơ - {job.title}",
        recipients=[current_user.email],
        body=body_candidate
    )
    except Exception as e:
        print("Email lỗi:", e)

    # 2️⃣ Email cho nhà tuyển dụng
    body_employer = render_template(
        "emails/job_applied_employer.html",
        employer_name=employer.company_name,
        candidate_name=current_user.candidate_profile.full_name,
        candidate_email=current_user.email,
        candidate_phone=current_user.candidate_profile.phone,
        job_title=job.title
    )
    try:
     send_email(
        subject=f"Thông báo hồ sơ mới - {job.title}",
        recipients=[employer.email],
        body=body_employer
    )
    except Exception as e:
     print("Email lỗi:", e)

    notif_candidate = Notification(
        candidate_id=current_user.candidate_profile.id,
        message=f"Bạn đã nộp hồ sơ thành công cho {job.title} tại {employer.company_name}.",
        type="application"
    )
    notif_employer = Notification(
        employer_id=employer.id,
        message=f"Ứng viên {current_user.candidate_profile.full_name} đã nộp hồ sơ cho {job.title}.",
        type="application"
    )
    db.session.add_all([notif_candidate, notif_employer])
    db.session.commit()

    flash("Ứng tuyển thành công. Email và thông báo đã được gửi.", "success")
    return redirect(url_for("candidate.applications"))

@candidate_bp.route("/saved_jobs")
@login_required
def saved_jobs():
    if current_user.role != "candidate":
        flash("Chỉ ứng viên mới xem công việc đã lưu", "danger")
        return redirect(url_for("job.list_jobs"))

    saved_jobs = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id) \
        .order_by(SavedJob.saved_at.desc()).all()
    return render_template("candidate/saved_jobs.html", saved_jobs=saved_jobs)


@candidate_bp.route("/applications")
@login_required
def applications():
    apps = Application.query.filter_by(candidate_id=current_user.candidate_profile.id).all()
    return render_template("candidate/applications.html", applications=apps)


@candidate_bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    candidate = current_user.candidate_profile

    if request.method == "POST":
        candidate.name = request.form.get("name")
        candidate.phone = request.form.get("phone")
        candidate.address = request.form.get("address")
        candidate.skills = request.form.get("skills")
        candidate.experience = request.form.get("experience")
        candidate.bio = request.form.get("bio")

        if "avatar" in request.files:
            file = request.files["avatar"]
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                upload_path = os.path.join("app", "static", "Uploads", filename)
                file.save(upload_path)
                candidate.avatar = filename

        db.session.commit()
        flash("Cập nhật hồ sơ thành công!", "success")
        return redirect(url_for("candidate.profile"))

    return render_template("candidate/edit_profile.html", candidate=candidate)


@candidate_bp.route("/save_job/<int:job_id>", methods=["POST"])
@login_required
def save_job(job_id):
    if current_user.role != "candidate":
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Chỉ ứng viên mới lưu công việc'}), 403
        flash("Chỉ ứng viên mới lưu công việc", "danger")
        return redirect(url_for("job.list_jobs"))

    job = Job.query.get_or_404(job_id)
    existing = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id, job_id=job.id).first()
    if existing:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Công việc đã được lưu trước đó'}), 400
        flash("Công việc đã được lưu trước đó", "warning")
        return redirect(request.referrer or url_for("main.index"))

    saved_job = SavedJob(candidate_id=current_user.candidate_profile.id, job_id=job.id)
    db.session.add(saved_job)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Lưu công việc thành công', 'action': 'saved'})
    flash("Lưu công việc thành công", "success")
    return redirect(request.referrer or url_for("main.index"))


@candidate_bp.route("/unsave_job/<int:job_id>", methods=["POST"])
@login_required
def unsave_job(job_id):
    if current_user.role != "candidate":
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Chỉ ứng viên mới bỏ lưu công việc'}), 403
        flash("Chỉ ứng viên mới bỏ lưu công việc", "danger")
        return redirect(url_for("job.list_jobs"))

    saved_job = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id, job_id=job_id).first()
    if not saved_job:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Công việc không được lưu trước đó'}), 400
        flash("Công việc không được lưu trước đó", "warning")
        return redirect(url_for("candidate.saved_jobs"))

    db.session.delete(saved_job)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Bỏ lưu công việc thành công', 'action': 'unsaved'})
    flash("Bỏ lưu công việc thành công", "success")
    return redirect(url_for("candidate.saved_jobs"))


@candidate_bp.route("/check_saved/<int:job_id>", methods=["GET"])
@login_required
def check_saved(job_id):
    if current_user.role != "candidate":
        return jsonify({"success": False, "is_saved": False, "message": "Chỉ ứng viên mới dùng chức năng này"}), 403

    saved = SavedJob.query.filter_by(candidate_id=current_user.candidate_profile.id, job_id=job_id).first()
    return jsonify({"success": True, "is_saved": bool(saved)})


@candidate_bp.route("/upload_avatar", methods=["POST"])
@login_required
def upload_avatar():
    if current_user.role != "candidate":
        return jsonify({"success": False, "message": "Chỉ ứng viên mới upload ảnh"}), 403

    if "avatar" not in request.files:
        return jsonify({"success": False, "message": "Không tìm thấy file"}), 400

    file = request.files["avatar"]
    if file.filename == "":
        return jsonify({"success": False, "message": "Tên file trống"}), 400

    filename = secure_filename(file.filename)
    upload_path = os.path.join("app", "static", "Uploads", filename)
    file.save(upload_path)

    candidate = current_user.candidate_profile
    candidate.avatar = filename
    db.session.commit()

    return jsonify({"success": True, "message": "Upload thành công", "filename": filename})

@candidate_bp.route("/notifications", methods=['GET', 'POST'])
@login_required
def view_notifications():
    form = NotificationForm()
    if current_user.role == "candidate":
        notifs = current_user.candidate_profile.notifications
    elif current_user.role == "employer":
        notifs = current_user.employer_profile.notifications
    else:
        notifs = []

    notifs = sorted(notifs, key=lambda n: n.created_at, reverse=True)
    return render_template("notifications/notifications.html", notifications=notifs, form=form)

@candidate_bp.route("/notifications/mark_read/<int:notif_id>", methods=["POST"])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)

    # Kiểm tra quyền
    if (current_user.role == "candidate" and notif.candidate_id != current_user.candidate_profile.id) or \
       (current_user.role == "employer" and notif.employer_id != current_user.employer_profile.id):
        return jsonify({"success": False, "message": "Không có quyền"}), 403

    notif.is_read = True
    db.session.commit()
    return jsonify({"success": True})

@candidate_bp.route("/notifications/mark_all_read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    try:
        validate_csrf(request.form.get('csrf_token') or request.json.get('csrf_token'))
    except:
        return jsonify({"success": False, "message": "CSRF token không hợp lệ"}), 403

    if current_user.role != "candidate" or not (hasattr(current_user, 'candidate_profile') and current_user.candidate_profile):
        return jsonify({"success": False, "message": "Chỉ ứng viên mới dùng chức năng này"}), 403

    notifications = Notification.query.filter_by(
        candidate_id=current_user.candidate_profile.id,
        is_read=False
    ).all()
    for notif in notifications:
        notif.is_read = True
    db.session.commit()
    return jsonify({"success": True, "message": "Tất cả thông báo đã được đánh dấu là đã đọc"})


@candidate_bp.route("/unread_notifications_count")
@login_required
def unread_notifications_count():
    # chỉ đếm notifications gắn candidate_id cho tài khoản candidate hiện tại
    if current_user.role != "candidate" or not getattr(current_user, "candidate_profile", None):
        return jsonify({"count": 0})
    candidate_id = current_user.candidate_profile.id
    count = Notification.query.filter_by(candidate_id=candidate_id, is_read=False).count()
    return jsonify({"count": count})
