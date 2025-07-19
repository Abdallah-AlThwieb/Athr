import os
from flask import Flask
from models import db, Student
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =f'postgresql://{os.environ.get("DATABASE_USERNAME")}:{os.environ.get("DATABASE_PASSWORD")}@localhost/{os.environ.get("DATABASE_NAME")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    existing = Student.query.filter_by(full_name='admin').first()
    if not existing:
        admin = Student(
            email=os.environ.get('OWNER_EMAIL'),  # ✅ إضافة البريد
            full_name=os.environ.get('OWNER_FULL_NAME'),
            password=generate_password_hash(os.environ.get('OWNER_PASSWORD')),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ تم إنشاء حساب المشرف")
    else:
        print("⚠️ حساب المشرف موجود بالفعل.")
