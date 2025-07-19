import os
from models import db, Student
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from app import app  # ✅ استيراد الكائن الجاهز من app.py
load_dotenv()

with app.app_context():
    existing = Student.query.filter_by(full_name="admin").first()
    if not existing:
        admin = Student(
            email="Fisal@gmail.com",
            full_name="فيصل صلاح الحربي",
            password=generate_password_hash("Fisal2025"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ تم إنشاء حساب المشرف بنجاح.")
    else:
        print("⚠️ حساب المشرف موجود بالفعل.")
