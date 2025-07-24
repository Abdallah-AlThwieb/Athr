from flask import Blueprint, render_template, request, redirect, url_for, g, flash
from flask_login import login_required, current_user
from datetime import date
from models import Answer, Question, Student, ManualPoint, VisibleDay, db
from sqlalchemy import Integer, cast, func, or_
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
        answers = (
            db.session.query(Answer, Question)
            .outerjoin(Question, Answer.question_id == Question.id)
            .filter(Answer.student_id == s.id)
            .all()
        )

        total_points = 0
        daily_points = 0

        for ans, q in answers:
            pts = 0
            if q:
                if q.question_type == 'numeric':
                    try:
                        pts = float(ans.answer)
                    except (ValueError, TypeError):
                        pts = 0
                else:
                    if ans.answer.lower() in ['yes', 'نعم']:
                        pts = q.points or 0

            if ans.date == date.today():
                daily_points += pts
            total_points += pts

        manual = db.session.query(func.coalesce(func.sum(ManualPoint.points), 0)).filter_by(student_id=s.id).scalar()
        total_combined = total_points + manual

        points_summary.append({
            'id': s.id,
            'full_name': s.full_name,
            'daily_points': daily_points,
            'total_points': total_combined,
            'manual_points': manual
        })

    return render_template('admin_dashboard.html', students=students, questions=questions, points_summary=points_summary)

@admin_bp.route('/add-question', methods=['POST'])
def add_question():
    text = request.form['question']
    points = request.form.get('points', type=int)
    visible_days_raw = request.form.getlist('visible_days')  # ← قائمة نصوص من checkboxes
    question_type = request.form.get('question_type', 'boolean')

    if not text or points is None:
        flash('يجب إدخال نص السؤال والنقاط')
        return redirect(url_for('admin.dashboard'))

    # تحويل الأيام إلى كائنات VisibleDay
    visible_days = []
    if visible_days_raw:
        for day in visible_days_raw:
            try:
                day_index = int(day)
                visible_days.append(VisibleDay(day_index=day_index))
            except ValueError:
                continue

    # إنشاء السؤال مع الأيام المرتبطة
    question = Question(
        text=text,
        points=points,
        question_type=question_type,
        visible_days=visible_days  # ← كائنات، وليس أرقام
    )

    db.session.add(question)
    db.session.commit()

    flash('تمت إضافة السؤال بنجاح ✅', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete-question/<int:question_id>')
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)

    # أزل الربط مع الإجابات بدلًا من حذفها (بشكل مباشر وفعّال)
    Answer.query.filter_by(question_id=question.id).update({'question_id': None})

    db.session.delete(question)
    db.session.commit()

    flash('تم حذف السؤال بنجاح دون حذف الإجابات.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/edit-question/<int:question_id>', methods=['POST'])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)

    question.text = request.form['text']
    question.points = request.form.get('points', type=int)
    question.question_type = request.form.get('question_type', 'boolean')

    # حذف الأيام القديمة
    question.visible_days.clear()

    # إعادة الإضافة إن وجدت أيام محددة
    visible_days_raw = request.form.getlist('visible_days')
    if visible_days_raw:
        for day in visible_days_raw:
            try:
                day_index = int(day)
                question.visible_days.append(VisibleDay(day_index=day_index))
            except ValueError:
                continue

    db.session.commit()
    flash("تم تعديل السؤال بنجاح ✅", "success")

    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/report")
@login_required
def report():
    if not current_user.is_admin:
        flash("غير مصرح لك بالدخول إلى هذه الصفحة", "error")
        return redirect(url_for("auth.login"))

    answers = (
        db.session.query(Answer, Question)
        .outerjoin(Question, Answer.question_id == Question.id)
        .all()
    )

    # إعداد مجلد الرسوم
    chart_dir = os.path.join("static", "charts")
    os.makedirs(chart_dir, exist_ok=True)
    for file in os.listdir(chart_dir):
        file_path = os.path.join(chart_dir, file)
        if os.path.isfile(file_path):
            os.remove(file_path)

    df = []
    for ans, q in answers:
        if q:
            if q.question_type == 'numeric':
                try:
                    pts = float(ans.answer)
                except (ValueError, TypeError):
                    pts = 0
            else:
                pts = q.points if ans.answer.lower() in ['yes', 'نعم'] else 0
        else:
            pts = 0  # السؤال محذوف، لكن نعرضه بدون نقاط

        df.append({
            "student": ans.student.full_name if ans.student else "غير معروف",
            "question": q.text if q else "—",
            "answer": ans.answer or "—",
            "date": ans.date.strftime("%Y-%m-%d") if ans.date else "—",
            "points": pts
        })

    df = pd.DataFrame(df)

    # 🔥 حساب الطالب الأعلى نقاطًا
    top_student_row = df.groupby('student')['points'].sum().sort_values(ascending=False).reset_index()
    if not top_student_row.empty:
        top_student_name = top_student_row.iloc[0]['student']
        top_student_points = top_student_row.iloc[0]['points']
    else:
        top_student_name = "لا يوجد"
        top_student_points = 0

    chart_paths = []

    if not df.empty:
        # الرسم 1: أعلى 10 طلاب
        top_users = (
            df.groupby('student')['points']
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        plt.figure(figsize=(10, 6))
        sns.barplot(x=top_users.index, y=top_users.values, palette="viridis")
        plt.title(' أعلى 10 طلاب نقاطًا')
        plt.xlabel('الطالب')
        plt.ylabel('مجموع النقاط')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        chart1_path = os.path.join(chart_dir, 'top_students_vertical.png')
        plt.savefig(chart1_path)
        chart_paths.append('charts/top_students_vertical.png')
        plt.close()

        # الرسم 2: من أجاب بـ "نعم" لكل سؤال
        yes_df = df[df['answer'].str.lower() == 'yes']
        if not yes_df.empty:
            counts = yes_df.groupby(['question', 'student']).size().reset_index(name='count')
            pivot_df = counts.pivot(index='question', columns='student', values='count').fillna(0)

            plt.figure(figsize=(12, 6))
            pivot_df.plot(kind='bar', stacked=True, colormap='tab20', figsize=(12, 6))
            plt.title(' الطلاب الأكثر إجابة بـ "نعم" لكل سؤال')
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
        answers=[a for a, _ in answers],
        chart_paths=chart_paths,
        data=df.to_dict(orient='records'),
        top_student_name=top_student_name,
        top_student_points=top_student_points
        )

@admin_bp.route('/student/<int:student_id>')
def student_details(student_id):
    student = Student.query.get_or_404(student_id)

    # جلب الإجابات مع معلومات السؤال
    answers = (
        db.session.query(
            Answer,
            Question.text.label('question_text'),
            Question.points.label('question_points'),
            Question.question_type.label('question_type')
        )
        .join(Question, Answer.question_id == Question.id)
        .filter(Answer.student_id == student.id)
        .order_by(Answer.date.desc())
        .all()
    )

    manual = ManualPoint.query.filter_by(student_id=student.id).order_by(ManualPoint.date.desc()).all()

    formatted_answers = []
    total_points = 0

    for ans, text, points, q_type in answers:
        # حساب النقاط حسب نوع السؤال
        if q_type == 'numeric':
            try:
                pts = float(ans.answer)
            except ValueError:
                pts = 0
        else:
            pts = points if ans.answer.lower() in ['yes', 'نعم'] else 0

        total_points += pts

        formatted_answers.append({
            'question_text': text,
            'question_points': pts,
            'question_type': q_type,
            'answer': ans.answer,
            'date': ans.date
            })

    # إضافة النقاط اليدوية
    for m in manual:
        total_points += m.points

    return render_template(
        'student_details.html',
        student=student,
        answers=formatted_answers,
        manual=manual,
        total_points=total_points
    )

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
