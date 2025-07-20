from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Student(UserMixin, db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    full_name = db.Column(db.String(100), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    answers = db.relationship('Answer', backref='student', lazy=True)
    manual_points = db.relationship('ManualPoint', backref='student', lazy=True)


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False, default=0)
    answers = db.relationship(
    'Answer',
    backref='question',
    lazy=True,
    cascade="save-update, merge, refresh-expire, expunge",  # ✅ لا تشمل delete
    passive_deletes=True  # ✅ يمنع حذف الأب من حذف الأبناء تلقائيًا
)



class Answer(db.Model):
    __tablename__ = 'answers'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=True)
    question_text = db.Column(db.Text, nullable=False)
    question_points = db.Column(db.Integer, nullable=False, default=0)  # ✅ نقاط السؤال وقت الإجابة
    date = db.Column(db.Date, nullable=False)
    answer = db.Column(db.String(10), nullable=False)


class ManualPoint(db.Model):
    __tablename__ = 'manual_points'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text)
    date = db.Column(db.Date)
