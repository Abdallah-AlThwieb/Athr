import os
from flask import Flask
from models import db, Student
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    existing = Student.query.filter_by(full_name='admin').first()
    if not existing:
        admin = Student(
            email="Fisal@gmail.com",  # ✅ إضافة البريد
            full_name="فيصل صلاح الحربي",
            password=generate_password_hash("Fisal2025"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ تم إنشاء حساب المشرف")
    else:
        print("⚠️ حساب المشرف موجود بالفعل.")
