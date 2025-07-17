import os
from flask import Flask
from models import db, Student
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{os.environ.get("DATABASE_USERNAME")}:{os.environ.get("DATABASE_PASSWORD")}@localhost/{os.environ.get("DATABASE_NAME")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    existing = Student.query.filter_by(username='admin').first()
    if not existing:
        admin = Student(
            email='aldwybballh@gmail.com',  # ✅ إضافة البريد
            full_name='عبدالله الذويب',
            password=generate_password_hash('abdallah10'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ تم إنشاء حساب المشرف (abdallah / abdallah10)")
    else:
        print("⚠️ حساب المشرف موجود بالفعل.")
