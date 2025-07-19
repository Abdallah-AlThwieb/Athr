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
import matplotlib
matplotlib.rcParams['font.family'] = 'Tahoma'  # أو أي خط عربي متوفر

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

@admin_bp.route("/report")
@login_required
def report():
    if not current_user.is_admin:
        flash("غير مصرح لك بالدخول إلى هذه الصفحة", "error")
        return redirect(url_for("auth.login"))

    answers = Answer.query.all()

    # إعداد المجلد لحفظ الرسوم
    chart_dir = os.path.join("static", "charts")
    os.makedirs(chart_dir, exist_ok=True)

    # حذف الرسوم القديمة
    for file in os.listdir(chart_dir):
        file_path = os.path.join(chart_dir, file)
        if os.path.isfile(file_path):
            os.remove(file_path)

    # تحليل البيانات باستخدام pandas
    df = pd.DataFrame([{
        "user": a.user.full_name,
        "question": a.question_text,
        "answer": a.answer_text,
        "points": a.points
    } for a in answers])

    chart_paths = []

    if not df.empty:
        # عدد الإجابات "نعم" و "لا"
        answer_counts = df['answer'].value_counts()
        plt.figure()
        answer_counts.plot(kind='bar', color=['skyblue', 'salmon'])
        plt.title('عدد الإجابات نعم / لا')
        plt.xlabel('الإجابة')
        plt.ylabel('العدد')
        chart1_path = os.path.join(chart_dir, 'answers_bar.png')
        plt.savefig(chart1_path)
        chart_paths.append(chart1_path)
        plt.close()

        # أكثر الطلاب نقاطًا
        top_users = df.groupby('user')['points'].sum().sort_values(ascending=False)
        plt.figure()
        top_users.plot(kind='bar', color='mediumseagreen')
        plt.title('الطلاب الأعلى نقاطًا')
        plt.xlabel('الطالب')
        plt.ylabel('النقاط')
        chart2_path = os.path.join(chart_dir, 'top_users.png')
        plt.savefig(chart2_path)
        chart_paths.append(chart2_path)
        plt.close()

        # توزيع النقاط باستخدام seaborn
        plt.figure()
        sns.histplot(df['points'], kde=True, bins=10, color='mediumpurple')
        plt.title('توزيع النقاط')
        plt.xlabel('النقاط')
        plt.ylabel('عدد الإجابات')
        chart3_path = os.path.join(chart_dir, 'points_dist.png')
        plt.savefig(chart3_path)
        chart_paths.append(chart3_path)
        plt.close()

    return render_template("admin_report.html", users=users, questions=questions, answers=answers, chart_paths=chart_paths)


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
