from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from models import Student
from models import db
from auth import auth
from survey import survey
from admin import admin_bp
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

login_manager = LoginManager()
migrate = Migrate()

login_manager.login_view = 'auth.login'  # أو اسم مسارك لتسجيل الدخول
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Student.query.get(int(user_id))

# إعداد الاتصال بقاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# تهيئة قاعدة البيانات
db.init_app(app)
migrate.init_app(app, db)

# تسجيل Blueprints
app.register_blueprint(auth)
app.register_blueprint(survey)
app.register_blueprint(admin_bp)

# إنشاء الجداول تلقائيًا
with app.app_context():
  db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
