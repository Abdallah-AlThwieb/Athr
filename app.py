from flask import Flask
from models import db
from auth import auth
from survey import survey
from admin import admin_bp
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# إعداد الاتصال بقاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{os.environ.get("DATABASE_USERNAME")}:{os.environ.get("DATABASE_PASSWORD")}@localhost/{os.environ.get("DATABASE_NAME")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# تهيئة قاعدة البيانات
db.init_app(app)

# تسجيل Blueprints
app.register_blueprint(auth)
app.register_blueprint(survey)
app.register_blueprint(admin_bp)

# إنشاء الجداول تلقائيًا
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
