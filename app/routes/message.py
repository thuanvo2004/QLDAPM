from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, Message, User
from datetime import datetime

# Blueprint cho messages
messages_bp = Blueprint("messages", __name__)

@messages_bp.route("/chat/<int:user_id>")
@login_required
def chat_with_user(user_id):
    # Lấy user đối phương
    other_user = User.query.get_or_404(user_id)

    # Debug in ra console
    print("🔹 current_user =", current_user.id, "🔹 other_user =", other_user.id)

    # Lấy toàn bộ tin nhắn 2 chiều
    chat_messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == other_user.id)) |
        ((Message.sender_id == other_user.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    # Debug tin nhắn
    for m in chat_messages:
        print(f"[{m.id}] {m.sender_id} → {m.receiver_id} : {m.content}")

    return render_template("messages/chat.html", other_user=other_user, chat_messages=chat_messages)


@messages_bp.route("/send/<int:user_id>", methods=["POST"])
@login_required
def send_message(user_id):
    other_user = User.query.get_or_404(user_id)
    content = request.form.get("content")

    if content:
        new_msg = Message(
            sender_id=current_user.id,
            receiver_id=other_user.id,
            content=content.strip()
        )
        db.session.add(new_msg)
        db.session.commit()

    # Redirect về lại trang chat
    return redirect(url_for("messages.chat_with_user", user_id=other_user.id))
@messages_bp.route("/chat/<int:user_id>/messages")
@login_required
def get_messages(user_id):
    other_user = User.query.get_or_404(user_id)

    chat_messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == other_user.id)) |
        ((Message.sender_id == other_user.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    return {
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "receiver_id": m.receiver_id,
                "content": m.content,
                "created_at": m.created_at.strftime("%H:%M:%S %d-%m-%Y")
            }
            for m in chat_messages
        ]
    }
