from flask import Blueprint, render_template, request, redirect, url_for, jsonify
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

    user_id = {current_user.id, other_user.id}
    for m in chat_messages:
        print(f"[{m.id}] {m.sender_id} → {m.receiver_id} : {m.content}")

    return render_template("messages/chat.html", other_user=other_user, chat_messages=chat_messages)


@messages_bp.route("/send/<int:user_id>", methods=["POST"])
@login_required
def send_message_user(user_id):
    other_user = User.query.get_or_404(user_id)
    content = request.form.get("content")

    if not content.strip():
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return jsonify({"error": "empty"}), 400
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
        content=content.strip(),
        created_at=datetime.utcnow(),
        is_read=False
    )
    db.session.add(new_msg)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
        return jsonify({
            "id": new_msg.id,
            "sender_id": new_msg.sender_id,
            "receiver_id": new_msg.receiver_id,
            "content": new_msg.content,
            "created_at": new_msg.created_at.isoformat(),
            "created_at_display": new_msg.created_at.strftime("%H:%M %d/%m/%Y"),
            "conversation_id": new_msg.conversation_id
        }), 201

    return redirect(url_for("messages.chat_with_user", user_id=other_user.id))

@messages_bp.route("/conversations")
@login_required
def list_conversations():
    # Tìm tất cả hội thoại mà user đang tham gia
    conversations = Conversation.query.filter(
        (Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id)
    ).all()

    return render_template("messages/conversations.html", conversations=conversations, current_user=current_user)

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
    # Đánh dấu tất cả tin nhắn gửi cho current_user trong cuộc trò chuyện này là đã đọc
    unread_msgs = Message.query.filter_by(conversation_id=convo.id, receiver_id=current_user.id, is_read=False).all()
    for msg in unread_msgs:
        msg.is_read = True
    db.session.commit()

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

    # Kiểm tra quyền tham gia hội thoại
    if current_user.id not in [convo.user1_id, convo.user2_id]:
        return "Bạn không có quyền", 403

    content = request.form.get("content", "").strip()
    if not content:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return jsonify({"error": "empty"}), 400
        return redirect(url_for("messages.conversation_detail", conversation_id=convo.id))

    if convo.user1_id == current_user.id:
        receiver_id = convo.user2_id
    else:
        receiver_id = convo.user1_id

    # Tạo tin nhắn mới
    msg = Message(
        conversation_id=convo.id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content,
        created_at=datetime.utcnow(),
        is_read=False
    )

    db.session.add(msg)
    db.session.commit()


    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
        return jsonify({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "created_at_display": msg.created_at.strftime("%H:%M %d/%m/%Y"),
            "conversation_id": msg.conversation_id
        }), 201

    return redirect(url_for("messages.conversation_detail", conversation_id=convo.id))

# dem so tin nhan chua doc
@messages_bp.route("/unread_count")
@login_required
def unread_count():
    count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return {"count": count}

# Inject vào template context
@messages_bp.app_context_processor
def inject_unread_count():
    if current_user.is_authenticated:
        unread_count = Message.query.filter_by(
            receiver_id=current_user.id,
            is_read=False
        ).count()
    else:
        unread_count = 0
    return dict(unread_count=unread_count)
@messages_bp.route("/messages/")
@login_required
def message_list():
    # Lấy danh sách user khác (trừ current_user)
    users = User.query.filter(User.id != current_user.id).all()
    return render_template("messages/list.html", users=users)

# import cần thiết
from app.models import User, Candidate, Employer

def build_display_names(user_ids: set):
    """
    Trả về dict: { user_id: display_name }
    - Nếu user.role == 'candidate' => lấy từ Candidate.full_name (hoặc name)
    - Nếu user.role == 'employer' => lấy từ Employer.company_name (hoặc name)
    - Nếu ko có profile => fallback user.username
    """
    if not user_ids:
        return {}

    users = User.query.filter(User.id.in_(list(user_ids))).all()
    user_map = {u.id: u for u in users}

    # Lấy tất cả candidate/employer cho các user_ids (1 query mỗi bảng)
    candidate_rows = Candidate.query.filter(Candidate.user_id.in_(list(user_ids))).all()
    employer_rows = Employer.query.filter(Employer.user_id.in_(list(user_ids))).all()
    candidate_map = {c.user_id: c for c in candidate_rows}
    employer_map = {e.user_id: e for e in employer_rows}

    display = {}
    for uid, u in user_map.items():
        role = getattr(u, "role", None)
        if role == "candidate":
            c = candidate_map.get(uid)
            # thay thế 'full_name' bằng tên field thực tế trong model Candidate
            display[uid] = getattr(c, "full_name", None) or getattr(c, "name", None) or u.username
        elif role == "employer":
            e = employer_map.get(uid)
            # thay 'company_name' bằng field thực tế trong model Employer
            display[uid] = getattr(e, "company_name", None) or getattr(e, "name", None) or u.username
        else:
            display[uid] = u.username or f"User#{uid}"

    return display
