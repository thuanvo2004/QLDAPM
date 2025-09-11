from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import Payment, User
from app.extensions import db
import json
import re
from datetime import datetime

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")

# Payment fee for premium activation (in VND)
PREMIUM_FEE = 2000  # 2,000 VND

@payment_bp.route("/")
@login_required
def payment_view():
    """Display payment page with QR code and banking details"""
    if current_user.role != "employer":
        flash("Chỉ nhà tuyển dụng mới có thể nâng cấp Premium", "danger")
        return redirect(url_for("main.index"))
    
    if current_user.isPremiumActive:
        flash("Tài khoản của bạn đã là Premium", "info")
        return redirect(url_for("job.post_job"))
    
    # Generate unique order ID using user ID
    order_id = f"PREMIUM{current_user.id}"
    
    payment_data = {
        'amount': PREMIUM_FEE,
        'order_id': order_id,
        'bank_account': '07994336868',
        'bank_name': 'MBBank',
        'account_holder': 'NGUYEN QUOC THAI ',
        'description': f'Thanh toan Premium {order_id}'
    }
    
    return render_template("payment/payment.html", payment_data=payment_data)

@payment_bp.route("/webhook", methods=["POST"])
def payment_webhook():
    """Handle payment webhook from bank/payment gateway"""
    try:
        # Get JSON data from webhook
        webhook_data = request.get_json()
        
        if not webhook_data:
            return jsonify({"status": "error", "message": "No data received"}), 400
        
        # Extract payment information
        gateway = webhook_data.get('gateway', '')
        transaction_date_str = webhook_data.get('transactionDate', '')
        account_number = webhook_data.get('accountNumber', '')
        sub_account = webhook_data.get('subAccount', '')
        amount_in = float(webhook_data.get('transferAmount', 0))
        amount_out = 0.00
        accumulated = float(webhook_data.get('accumulated', 0))
        code = webhook_data.get('code', '')
        transaction_content = webhook_data.get('content', '')
        reference_number = webhook_data.get('referenceCode', '')
        description = webhook_data.get('description', '')
        
        # Parse transaction date
        try:
            transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            transaction_date = datetime.utcnow()
        
        # Extract user ID from description (format: PREMIUMX where X is user_id)
        user_id_match = re.search(r'PREMIUM(\d+)', description)
        if not user_id_match:
            # Try to extract from transaction content as fallback
            user_id_match = re.search(r'PREMIUM(\d+)', transaction_content)
        
        if not user_id_match:
            current_app.logger.warning(f"Could not extract user ID from payment description: {description}")
            return jsonify({"status": "error", "message": "Invalid payment description"}), 400
        
        user_id = int(user_id_match.group(1))
        
        # Find user
        user = User.query.get(user_id)
        if not user or user.role != 'employer':
            current_app.logger.warning(f"User not found or not employer: {user_id}")
            return jsonify({"status": "error", "message": "User not found"}), 400
        
        # Check if payment amount matches required fee
        if amount_in < PREMIUM_FEE:
            current_app.logger.warning(f"Payment amount {amount_in} less than required {PREMIUM_FEE}")
            return jsonify({"status": "error", "message": "Insufficient payment amount"}), 400
        
        # Check if payment already processed (avoid duplicate processing)
        existing_payment = Payment.query.filter_by(
            reference_number=reference_number,
            user_id=user_id
        ).first()
        
        if existing_payment:
            current_app.logger.info(f"Payment already processed: {reference_number}")
            return jsonify({"status": "success", "message": "Payment already processed"}), 200
        
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
            body=json.dumps(webhook_data),
            user_id=user_id
        )
        
        # Activate premium for user
        user.isPremiumActive = True
        
        # Save to database
        db.session.add(payment)
        db.session.commit()
        
        current_app.logger.info(f"Premium activated for user {user_id}, payment ID: {payment.id}")
        
        return jsonify({
            "status": "success", 
            "message": "Payment processed and premium activated",
            "user_id": user_id,
            "payment_id": payment.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error processing payment webhook")
        return jsonify({"status": "error", "message": str(e)}), 500

@payment_bp.route("/success")
@login_required
def payment_success():
    """Payment success page"""
    if current_user.isPremiumActive:
        return render_template("payment/success.html")
    else:
        flash("Thanh toán chưa được xử lý. Vui lòng thử lại sau.", "warning")
        return redirect(url_for("payment.payment_view"))
