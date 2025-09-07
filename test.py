from app import create_app
from app.extensions import db
from app.models import User

app = create_app()
app.app_context().push()

u = User(email="admin@gmail.com", role="employer")
u.set_password("admin")
db.session.add(u)
db.session.commit()

# Kiểm tra login
u.check_password("admin")   # True
u.check_password("wrong")    # False
