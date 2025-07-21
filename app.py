from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from models import Student, db
from auth import auth
from survey import survey
from admin import admin_bp
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY')

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/Athr2'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

migrate = Migrate(app, db)

db.init_app(app)

def create_tables():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return Student.query.get(int(user_id))

app.register_blueprint(auth)
app.register_blueprint(survey)
app.register_blueprint(admin_bp)

if __name__ == '__main__':
    app.run(debug=True)
