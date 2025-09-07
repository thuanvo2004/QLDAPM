from flask import Blueprint, render_template

message_bp = Blueprint("message", __name__, url_prefix="/message")

@message_bp.route("/inbox")
def inbox():
    return render_template("message/inbox.html")
