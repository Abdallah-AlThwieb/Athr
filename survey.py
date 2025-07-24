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

    from datetime import datetime
    today_index = datetime.today().weekday()  # 0 = الإثنين, 6 = الأحد

    questions = Question.query.filter(
        (Question.visible_days == None) |               # يظهر دائمًا
        (~Question.visible_days.any()) |                 # لا أيام محددة
        (Question.visible_days.any(day_index=today_index)) # يظهر في هذا اليوم
    ).all()

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

        value_cleaned = value.strip().lower()
        points = 0  # القيمة الافتراضية

        # --- تحديد النقاط ---
        if question.question_type == 'numeric':
            try:
                numeric_value = float(value_cleaned)
                if numeric_value > 0:
                    points = numeric_value
            except ValueError:
                points = 0  # إذا لم تكن القيمة رقمًا
        else:  # boolean
            if value_cleaned in ['yes', 'نعم']:
                points = question.points

        # --- إضافة أو تعديل الإجابة ---
        try:
            answer = Answer(
                student_id=current_user.id,
                question_id=question.id,
                question_text=question.text,
                question_points=points,
                question_type=question.question_type,
                date=date.today(),
                answer=value_cleaned  # ← نخزنها موحدة
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
                existing.answer = value_cleaned
                existing.question_text = question.text
                existing.question_points = points
                existing.question_type = question.question_type
                db.session.commit()

    return redirect(url_for('survey.index'))
