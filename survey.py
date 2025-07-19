from flask import Blueprint, render_template, request, redirect, url_for, g
from datetime import date
from models import db, Question, Answer
from sqlalchemy.exc import IntegrityError

survey = Blueprint('survey', __name__)

@survey.route('/')
def index():
    if g.user is None:
        return redirect(url_for('auth.login'))

    if g.user.is_admin:
        return redirect(url_for('admin.dashboard'))

    questions = Question.query.all()
    answered_ids = [
        ans.question_id for ans in Answer.query
        .filter_by(student_id=g.user.id, date=date.today()).all()
    ]

    return render_template('survey.html', questions=questions, answered_ids=answered_ids)

@survey.route('/submit', methods=['POST'])
def submit():
    if g.user is None:
        return redirect(url_for('auth.login'))

    for qid, value in request.form.items():
        question = Question.query.get(int(qid))
        if not question:
            continue  # تجاهل الأسئلة المحذوفة

        try:
            answer = Answer(
                student_id=g.user.id,
                question_id=question.id,
                question_text=question.text,  # ✅ تخزين النص هنا
                date=date.today(),
                answer=value
            )
            db.session.add(answer)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            existing = Answer.query.filter_by(
                student_id=g.user.id,
                question_id=question.id,
                date=date.today()
            ).first()
            if existing:
                existing.answer = value
                existing.question_text = question.text  # ✅ تحديث النص أيضًا عند التعديل
                db.session.commit()

    return redirect(url_for('survey.index'))
