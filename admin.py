from flask import Blueprint, render_template, request, redirect, url_for, g, flash
from datetime import date
from models import Answer, Question, Student, ManualPoint, db
from sqlalchemy import func
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from sqlalchemy import case

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

@admin_bp.route('/delete-question/<int:question_id>')
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)

    # فقط حذف السؤال بدون حذف الإجابات، لأن نص السؤال محفوظ داخل Answer.question_text
    db.session.delete(question)
    db.session.commit()

    flash('تم حذف السؤال بنجاح.', 'success')
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

    # جلب البيانات من قاعدة البيانات
    report_data = db.session.query(
        Student.full_name,
        Question.text,
        Answer.date,
        Answer.answer
    ).join(Answer, Student.id == Answer.student_id) \
     .join(Question, Question.id == Answer.question_id) \
     .order_by(Answer.date.desc(), Student.full_name).all()

    # تحويلها إلى DataFrame
    df = pd.DataFrame(report_data, columns=['full_name', 'question', 'date', 'answer'])

    # إنشاء مجلد الرسوم إذا لم يكن موجودًا
    chart_dir = os.path.join('static', 'charts')
    os.makedirs(chart_dir, exist_ok=True)

    # 1. عدّاد إجابات نعم/لا
    if not df.empty:
        answer_counts = df['answer'].value_counts()
        plt.figure(figsize=(5, 4))
        sns.barplot(x=answer_counts.index, y=answer_counts.values, palette='Set2')
        plt.title('إجمالي عدد الإجابات')
        plt.ylabel('العدد')
        plt.xlabel('الإجابة')
        plt.savefig(os.path.join(chart_dir, 'answers_count.png'))
        plt.close()

    # 2. أكثر الطلاب نقاطًا (نعم + يدويًا)
    top_students_query = db.session.query(
        Student.full_name,
        (
            func.coalesce(func.sum(case([(Answer.answer == 'yes', Question.points)], else_=0)), 0) +
            func.coalesce(func.sum(ManualPoint.points), 0)
        ).label('total_points')
    ).select_from(Student) \
     .outerjoin(Answer, Answer.student_id == Student.id) \
     .outerjoin(Question, Question.id == Answer.question_id) \
     .outerjoin(ManualPoint, ManualPoint.student_id == Student.id) \
     .group_by(Student.full_name) \
     .order_by(func.sum(Question.points + ManualPoint.points).desc()) \
     .limit(5).all()

    top_df = pd.DataFrame(top_students_query, columns=['full_name', 'total_points'])
    if not top_df.empty:
        plt.figure(figsize=(7, 4))
        sns.barplot(data=top_df, x='total_points', y='full_name', palette='viridis')
        plt.title('📊 أكثر 5 طلاب نقاطًا (إجابات + يدوي)')
        plt.xlabel('المجموع الكلي للنقاط')
        plt.ylabel('الاسم')
        plt.savefig(os.path.join(chart_dir, 'top_students.png'))
        plt.close()

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
