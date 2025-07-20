from flask import Blueprint, request, redirect, url_for, render_template, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Student

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        full_name = request.form['full_name']
        password = request.form['password']
        
        user = Student.query.filter_by(full_name=full_name).first()

        if user is None or not check_password_hash(user.password, password):
            flash('الاسم أو كلمة المرور غير صحيحة', 'error')
        else:
            login_user(user)
            flash('تم تسجيل الدخول بنجاح', 'success')

            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin.dashboard') if user.is_admin else url_for('survey.index'))
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        full_name = request.form['full_name']
        password = request.form['password']

        if Student.query.filter((Student.full_name == full_name) | (Student.email == email)).first():
            flash('الاسم أو البريد الإلكتروني مستخدم مسبقًا', 'error')
        else:
            new_user = Student(
                email=email,
                full_name=full_name,
                password=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()
            flash('تم إنشاء الحساب بنجاح. يمكنك الآن تسجيل الدخول.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح", "success")
    return redirect(url_for('auth.login'))
