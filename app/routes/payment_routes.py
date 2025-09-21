# app/payment/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import Payment, User
from app.extensions import db
import json
import re
from datetime import datetime
from typing import Any, Dict

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")

# Payment fee for premium activation (in VND)
PREMIUM_FEE = 2000  # 2,000 VND


@payment_bp.route("/")
@login_required
def payment_view():
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng mới có thể nâng cấp Premium", "danger")
        return redirect(url_for("main.index"))

    if current_user.isPremiumActive:
        flash("Tài khoản của bạn đã là Premium", "info")
        return redirect(url_for("job.post_job"))

    # Generate unique order ID using user ID
    order_id = f"PREMIUM{current_user.id}"

    payment_data = {
        "amount": PREMIUM_FEE,
        "order_id": order_id,
        "bank_account": "88458504602",
        "bank_name": "TPBank",
        "account_holder": "NGUYEN HOAI XUAN QUANG",
        "description": f"Thanh toan Premium {order_id}",
    }

    return render_template("payment/payment.html", payment_data=payment_data)


def _parse_transaction_date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return datetime.utcnow()


def process_payment(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Xử lý payload webhook, cập nhật DB, trả về dict kết quả.
    Trả về: {"ok": True, "payment_id": <id>} hoặc {"ok": False, "msg": "..."}
    """
    try:
        # Extract payment information with safe defaults
        gateway = webhook_data.get("gateway", "")
        transaction_date_str = webhook_data.get("transactionDate", "")
        account_number = webhook_data.get("accountNumber", "")
        sub_account = webhook_data.get("subAccount", "")
        # transferAmount có thể là số hoặc chuỗi
        try:
            amount_in = float(webhook_data.get("transferAmount", 0) or 0)
        except (ValueError, TypeError):
            amount_in = 0.0
        amount_out = 0.00
        try:
            accumulated = float(webhook_data.get("accumulated", 0) or 0)
        except (ValueError, TypeError):
            accumulated = 0.0
        code = webhook_data.get("code", "")
        transaction_content = webhook_data.get("content", "") or webhook_data.get("transferContent", "")
        reference_number = webhook_data.get("referenceCode", "") or webhook_data.get("reference_number", "")
        description = webhook_data.get("description", "") or webhook_data.get("note", "")

        transaction_date = _parse_transaction_date(transaction_date_str)

        # Extract user ID from description/content (format: PREMIUM{user_id})
        user_id_match = re.search(r"PREMIUM(\d+)", description or "")
        if not user_id_match:
            user_id_match = re.search(r"PREMIUM(\d+)", transaction_content or "")

        if not user_id_match:
            return {"ok": False, "msg": "Could not extract user id from description/content."}

        user_id = int(user_id_match.group(1))

        # Find user
        user = User.query.get(user_id)
        if not user or user.role != "employer":
            return {"ok": False, "msg": "User not found or not employer."}

        # Check amount
        if amount_in < PREMIUM_FEE:
            return {"ok": False, "msg": f"Insufficient payment amount: {amount_in}"}

        # Avoid duplicate
        existing = Payment.query.filter_by(reference_number=reference_number, user_id=user_id).first()
        if existing:
            current_app.logger.info("Duplicate payment: %s", reference_number)
            return {"ok": True, "payment_id": existing.id}

        # Create payment record
        payment = Payment(
            gateway=gateway,
            transaction_date=transaction_date,
            account_number=account_number,
            sub_account=sub_account,
            amount_in=amount_in,
            amount_out=amount_out,
            accumulated=accumulated,
            code=code,
            transaction_content=transaction_content,
            reference_number=reference_number,
            body=json.dumps(webhook_data, ensure_ascii=False),
            user_id=user_id,
        )

        # Activate premium for user
        user.isPremiumActive = True

        db.session.add(payment)
        db.session.add(user)  # ensure user change tracked
        db.session.commit()

        return {"ok": True, "payment_id": payment.id}
    except Exception as exc:
        current_app.logger.exception("Error in process_payment")
        db.session.rollback()
        return {"ok": False, "msg": str(exc)}


@payment_bp.route("/webhook", methods=["POST"])
def payment_webhook():
    """
    Endpoint chính: POST /payment/webhook
    Sepay => gọi tới URL này (content-type: application/json)
    """
    # Log headers + raw body for debugging (xem ngrok inspector)
    current_app.logger.info("Webhook received. Headers: %s", dict(request.headers))
    raw_body = request.get_data(as_text=True)
    current_app.logger.info("Webhook raw body: %s", raw_body)

    # Try parse JSON
    webhook_data = request.get_json(silent=True)
    if webhook_data is None:
        current_app.logger.warning("Webhook: no JSON payload parsed.")
        # Trả 400 để Sepay biết payload không hợp lệ (tùy chọn).
        return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

    # (Optional) Verify signature here if you configured HMAC/API key in Sepay
    # ex: sig = request.headers.get("X-Sepay-Signature"); verify_signature(raw_body, sig)
    # if not ok: return 403

    result = process_payment(webhook_data)
    if result.get("ok"):
        current_app.logger.info("Payment processed, id=%s", result.get("payment_id"))
        # Trả 200 để Sepay biết thành công (và nếu Sepay "wait for webhook", họ sẽ redirect)
        return jsonify({"status": "success"}), 200
    else:
        current_app.logger.warning("Payment processing failed: %s", result.get("msg"))
        # Nếu bạn muốn Sepay retry, trả mã lỗi 4xx/5xx.
        return jsonify({"status": "error", "message": result.get("msg")}), 400


# Alias route cho trường hợp Sepay được cấu hình gọi /webhook/payment (nhiều người cấu hình nhầm)
def init_payment_routes(app):
    """
    Gọi hàm này trong app factory sau khi register blueprint:
        app.register_blueprint(payment_bp)
        init_payment_routes(app)
    Nó sẽ tạo thêm route /webhook/payment -> map tới cùng handler ở trên.
    """
    # Nếu route đã tồn tại, add_url_rule sẽ raise; để an toàn, kiểm tra trước:
    endpoint_name = "sepay_webhook_root"
    if endpoint_name not in app.view_functions:
        app.add_url_rule("/webhook/payment", endpoint_name, payment_webhook, methods=["POST"])

    # (tùy chọn) thêm route khác nếu bạn muốn hỗ trợ /payment (POST) — nhưng KHÔNG khuyến khích
    # nếu cần: app.add_url_rule("/payment", "payment_post_alias", payment_webhook, methods=["POST"])


@payment_bp.route("/status")
@login_required
def payment_status():
    """
    API cho frontend poll: GET /payment/status
    Trả về JSON {isPremiumActive: bool}
    """
    return jsonify({"isPremiumActive": bool(current_user.isPremiumActive)}), 200


@payment_bp.route("/success")
@login_required
def payment_success():
    """
    Payment success page: user chỉ được thấy khi isPremiumActive == True
    """
    if current_user.isPremiumActive:
        return render_template("payment/success.html")
    else:
        flash("Thanh toán chưa được xử lý. Vui lòng thử lại sau.", "warning")
        return redirect(url_for("payment.payment_view"))
