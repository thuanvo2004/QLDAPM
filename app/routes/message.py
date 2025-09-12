from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, Message, User, Conversation
from datetime import datetime
from sqlalchemy import desc

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
def send_message_user(user_id):
    other_user = User.query.get_or_404(user_id)
    content = request.form.get("content")

    if not content.strip():
        return redirect(url_for("messages.chat_with_user", user_id=other_user.id))

    # Tìm conversation cũ giữa 2 người
    conversation = Conversation.query.filter(
        ((Conversation.user1_id == current_user.id) & (Conversation.user2_id == other_user.id)) |
        ((Conversation.user1_id == other_user.id) & (Conversation.user2_id == current_user.id))
    ).first()

    # Nếu chưa có thì tạo mới
    if not conversation:
        conversation = Conversation(user1_id=current_user.id, user2_id=other_user.id)
        db.session.add(conversation)
        db.session.commit()

    # Thêm tin nhắn mới
    new_msg = Message(
        sender_id=current_user.id,
        receiver_id=other_user.id,
        conversation_id=conversation.id,
        content=content.strip()
    )
    db.session.add(new_msg)
    db.session.commit()

    return redirect(url_for("messages.chat_with_user", user_id=other_user.id))

@messages_bp.route("/conversations")
@login_required
def list_conversations():
    # Tìm tất cả hội thoại mà user đang tham gia
    conversations = Conversation.query.filter(
        (Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id)
    ).all()

    return render_template("messages/conversations.html", conversations=conversations)

@messages_bp.route("/")
@login_required
def index():
    # Lấy tất cả hội thoại của user hiện tại
    conversations = Conversation.query.filter(
        (Conversation.user1_id == current_user.id) |
        (Conversation.user2_id == current_user.id)
    ).all()

    # Thêm thuộc tính last_message cho từng conversation
    for convo in conversations:
        if convo.messages:  # Nếu có tin nhắn
            convo.last_message = sorted(
                convo.messages,
                key=lambda m: m.created_at,
                reverse=True
            )[0]
        else:
            convo.last_message = None

    return render_template("messages/index.html", conversations=conversations)


@messages_bp.route("/conversation/<int:conversation_id>")
@login_required
def conversation_detail(conversation_id):
    convo = Conversation.query.get_or_404(conversation_id)

    if current_user.id not in [convo.user1_id, convo.user2_id]:
        return "Bạn không có quyền", 403

    # 🔹 Xác định user còn lại trong hội thoại
    if convo.user1_id == current_user.id:
        other_user = convo.user2
    else:
        other_user = convo.user1

    # 🔹 Lấy tin nhắn của hội thoại
    messages = Message.query.filter_by(conversation_id=convo.id).order_by(Message.created_at.asc()).all()

    return render_template(
        "messages/chat.html",
        conversation=convo,
        messages=messages,
        other_user=other_user
    )

@messages_bp.route("/conversation/<int:conversation_id>/send", methods=["POST"])
@login_required
def send_message_conversation(conversation_id):
    convo = Conversation.query.get_or_404(conversation_id)

    if current_user.id not in [convo.user1_id, convo.user2_id]:
        return "Bạn không có quyền", 403

    content = request.form.get("content")
    if content:
        msg = Message(
            conversation_id=convo.id,
            sender_id=current_user.id,
            content=content,
            created_at=datetime.utcnow()
        )
        db.session.add(msg)
        db.session.commit()

    return redirect(url_for("messages.conversation_detail", conversation_id=convo.id))




@messages_bp.route("/messages/")
@login_required
def message_list():
    # Lấy danh sách user khác (trừ current_user)
    users = User.query.filter(User.id != current_user.id).all()
    return render_template("messages/list.html", users=users)
