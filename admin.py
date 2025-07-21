from flask import Blueprint, render_template, request, redirect, url_for, g, flash
from flask_login import login_required, current_user
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
@login_required
def dashboard():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("غير مصرح لك بالدخول", "error")
        return redirect(url_for("auth.login"))

    students = Student.query.filter_by(is_admin=False).order_by(Student.full_name).all()
    questions = Question.query.order_by(Question.id).all()

    points_summary = []
    for s in students:
        daily = db.session.query(func.coalesce(func.sum(Answer.question_points), 0)).filter(
            Answer.student_id == s.id,
            Answer.date == date.today(),
            Answer.answer == 'yes'
            ).scalar()
        
        total = db.session.query(func.coalesce(func.sum(Answer.question_points), 0)).filter(
            Answer.student_id == s.id,
            Answer.answer == 'yes'
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
    visible_days_raw = request.form.getlist('visible_days')  # ← قائمة نصوص من checkboxes

    if not text or points is None:
        flash('يجب إدخال نص السؤال والنقاط')
        return redirect(url_for('admin.dashboard'))

    # تحويل الأيام إلى أرقام (int)، أو None إن لم يتم اختيار شيء
    visible_days = [int(d) for d in visible_days_raw] if visible_days_raw else None

    question = Question(text=text, points=points, visible_days=visible_days)
    db.session.add(question)
    db.session.commit()

    flash('تمت إضافة السؤال بنجاح ✅', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete-question/<int:question_id>')
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)

    # أزل الربط مع الإجابات بدلًا من حذفها
    for answer in question.answers:
        answer.question_id = None  # إزالة الربط
    db.session.delete(question)
    db.session.commit()

    flash('تم حذف السؤال بنجاح دون حذف الإجابات.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/edit-question/<int:question_id>', methods=['POST'])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)

    question.text = request.form['text']
    question.points = request.form.get('points', type=int)

    visible_days_raw = request.form.getlist('visible_days')
    question.visible_days = [int(d) for d in visible_days_raw] if visible_days_raw else None

    db.session.commit()
    flash("تم تعديل السؤال بنجاح ✅", "success")

    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/report")
@login_required
def report():
    if not current_user.is_admin:
        flash("غير مصرح لك بالدخول إلى هذه الصفحة", "error")
        return redirect(url_for("auth.login"))

    answers = Answer.query.all()

    # إعداد مجلد الرسوم
    chart_dir = os.path.join("static", "charts")
    os.makedirs(chart_dir, exist_ok=True)
    for file in os.listdir(chart_dir):
        file_path = os.path.join(chart_dir, file)
        if os.path.isfile(file_path):
            os.remove(file_path)

    # تجهيز البيانات
    df = pd.DataFrame([{
        "student": a.student.full_name if a.student else "غير معروف",
        "question": a.question_text or "—",
        "answer": a.answer or "—",
        "date": a.date.strftime("%Y-%m-%d") if a.date else "—",
        "points": a.question_points or 0
    } for a in answers])

    chart_paths = []

    if not df.empty:
        # الرسم 1: Bar - أعلى 10 طلاب نقاطًا (عمودي)
        top_users = (
            df.groupby('student')['points']
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        plt.figure(figsize=(10, 6))
        sns.barplot(x=top_users.index, y=top_users.values, palette="viridis")
        plt.title('🏆 أعلى 10 طلاب نقاطًا')
        plt.xlabel('الطالب')
        plt.ylabel('مجموع النقاط')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        chart1_path = os.path.join(chart_dir, 'top_students_vertical.png')
        plt.savefig(chart1_path)
        chart_paths.append('charts/top_students_vertical.png')
        plt.close()

        # الرسم 2: لكل سؤال، من الطالب الذي أجاب بـ "نعم" أكثر
        yes_df = df[df['answer'] == 'yes']
        if not yes_df.empty:
            counts = yes_df.groupby(['question', 'student']).size().reset_index(name='count')
            pivot_df = counts.pivot(index='question', columns='student', values='count').fillna(0)

            plt.figure(figsize=(12, 6))
            pivot_df.plot(kind='bar', stacked=True, colormap='tab20', figsize=(12, 6))
            plt.title('📌 الطلاب الأكثر إجابة بـ "نعم" لكل سؤال')
            plt.xlabel('السؤال')
            plt.ylabel('عدد مرات الإجابة بـ نعم')
            plt.xticks(rotation=45, ha='right')
            plt.legend(title='الطالب', bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()
            chart2_path = os.path.join(chart_dir, 'yes_answers_per_question.png')
            plt.savefig(chart2_path)
            chart_paths.append('charts/yes_answers_per_question.png')
            plt.close()

    return render_template(
        "report.html",
        answers=answers,
        chart_paths=chart_paths,
        data=df.to_dict(orient='records')
    )

@admin_bp.route('/student/<int:student_id>')
def student_details(student_id):
    student = Student.query.get_or_404(student_id)
    answers = Answer.query.filter_by(student_id=student.id).order_by(Answer.date.desc()).all()
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
