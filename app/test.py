# populate_public_url.py
from app.extensions import db
from app.routes.cv_routes import CVHistory
import cloudinary
from cloudinary.utils import cloudinary_url
import os
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

cvs = CVHistory.query.all()
for cv in cvs:
    if not cv.public_url:
        try:
            cv.public_url = cloudinary_url(cv.filename, resource_type="raw")[0]
            db.session.add(cv)
            print(f"Updated public_url for CV id={cv.id}: {cv.public_url}")
        except Exception as e:
            print(f"Failed to generate public_url for CV id={cv.id}: {str(e)}")
db.session.commit()