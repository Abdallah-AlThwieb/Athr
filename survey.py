from flask import Blueprint, render_template, request, redirect, url_for
from datetime import date
from models import db, Question, Answer
from sqlalchemy.exc import IntegrityError
from flask_login import current_user, login_required

survey = Blueprint('survey', __name__)

@survey.route('/')
@login_required
def index():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))

    questions = Question.query.all()
    answered_ids = [
        ans.question_id for ans in Answer.query
        .filter_by(student_id=current_user.id, date=date.today()).all()
    ]

    return render_template('survey.html', questions=questions, answered_ids=answered_ids)

@survey.route('/submit', methods=['POST'])
@login_required
def submit():
    for qid, value in request.form.items():
        question = Question.query.get(int(qid))
        if not question:
            continue  # تجاهل الأسئلة المحذوفة

        try:
            answer = Answer(
                student_id=current_user.id,
                question_id=question.id,
                question_text=question.text,
                question_points=question.points,  # ✅ لتخزين النقاط
                date=date.today(),
                answer=value
            )
            db.session.add(answer)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            existing = Answer.query.filter_by(
                student_id=current_user.id,
                question_id=question.id,
                date=date.today()
            ).first()
            if existing:
                existing.answer = value
                existing.question_text = question.text
                existing.question_points = question.points  # ✅ تحديث النقاط
                db.session.commit()

    return redirect(url_for('survey.index'))
