from flask import Blueprint, render_template, request, redirect, url_for, g, flash
from datetime import date
from models import db, Student, Question, Answer, ManualPoint
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def dashboard():
    if not g.user or not g.user.is_admin:
        return redirect(url_for('auth.login'))

    students = Student.query.filter_by(is_admin=False).order_by(Student.full_name).all()
    questions = Question.query.order_by(Question.id).all()

    points_summary = []
    for s in students:
        daily = db.session.query(func.coalesce(func.sum(Question.points), 0)).join(Answer).filter(
            Answer.student_id == s.id,
            Answer.date == date.today(),
            Answer.answer == 'yes',
            Question.id == Answer.question_id
        ).scalar()

        total = db.session.query(func.coalesce(func.sum(Question.points), 0)).join(Answer).filter(
            Answer.student_id == s.id,
            Answer.answer == 'yes',
            Question.id == Answer.question_id
        ).scalar()

        manual = db.session.query(func.coalesce(func.sum(ManualPoint.points), 0)).filter_by(student_id=s.id).scalar()

        points_summary.append({
            'id': s.id,
            'full_name': s.full_name,
            'daily_points': daily,
            'total_points': total,
            'manual_points': manual
        })

    return render_template('admin_dashboard.html', students=students, questions=questions, points_summary=points_summary)

@admin_bp.route('/add-question', methods=['POST'])
def add_question():
    text = request.form['question']
    points = request.form.get('points', type=int)

    if not text or points is None:
        flash('يجب إدخال نص السؤال والنقاط')
        return redirect(url_for('admin.dashboard'))

    question = Question(text=text, points=points)
    db.session.add(question)
    db.session.commit()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete-question/<int:id>')
def delete_question(id):
    question = Question.query.get(id)
    if question:
        try:
            # حذف جميع الإجابات المرتبطة بالسؤال أولًا
            Answer.query.filter_by(question_id=question.id).delete()

            db.session.delete(question)
            db.session.commit()
            flash('تم حذف السؤال بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء حذف السؤال: {str(e)}', 'error')
    else:
        flash('السؤال غير موجود', 'error')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/edit-question/<int:question_id>', methods=['POST'])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    question.text = request.form['text']
    question.points = request.form.get('points', type=int)
    db.session.commit()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/report')
def report():
    if not g.user or not g.user.is_admin:
        return redirect(url_for('auth.login'))

    report_data = db.session.query(
        Student.full_name,
        Question.text,
        Answer.date,
        Answer.answer
    ).join(Answer, Student.id == Answer.student_id) \
     .join(Question, Question.id == Answer.question_id) \
     .order_by(Answer.date.desc(), Student.full_name).all()

    return render_template('report.html', report=report_data)

@admin_bp.route('/student/<int:student_id>')
def student_details(student_id):
    student = Student.query.get_or_404(student_id)
    answers = db.session.query(Answer, Question).join(Question).filter(Answer.student_id == student.id).order_by(Answer.date.desc()).all()
    manual = ManualPoint.query.filter_by(student_id=student.id).order_by(ManualPoint.date.desc()).all()

    return render_template('student_details.html', student=student, answers=answers, manual=manual)

@admin_bp.route('/add-points/<int:student_id>', methods=['POST'])
def add_manual_points(student_id):
    points = request.form.get('points', type=int)
    reason = request.form['reason']

    if points is None:
        flash("يجب إدخال عدد النقاط")
        return redirect(url_for('admin.student_details', student_id=student_id))

    entry = ManualPoint(student_id=student_id, points=points, reason=reason, date=date.today())
    db.session.add(entry)
    db.session.commit()

    return redirect(url_for('admin.student_details', student_id=student_id))

@admin_bp.route('/question/<int:question_id>')
def question_detail(question_id):
    question = Question.query.get_or_404(question_id)
    answers = Answer.query.filter_by(question_id=question_id).all()
    return render_template('question_detail.html', question=question, answers=answers)
