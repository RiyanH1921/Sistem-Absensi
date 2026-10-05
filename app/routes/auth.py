from datetime import datetime
from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
from flask_jwt_extended import create_access_token
from app.extensions import db
from app.models.user import User
from app.models.academic import Student, Teacher
from app.utils.decorators import get_current_user, record_audit

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')
auth_views = Blueprint('auth_views', __name__)

def find_user_by_identifier(identifier: str):
    """
    Find user by username, email, student NIS, or teacher NIP.
    """
    if not identifier:
        return None
    identifier = identifier.strip()
    # 1. Direct username or email
    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    if user:
        return user
    # 2. Check student NIS
    student = Student.query.filter_by(nis=identifier).first()
    if student and student.user:
        return student.user
    # 3. Check teacher NIP
    teacher = Teacher.query.filter_by(nip=identifier).first()
    if teacher and teacher.user:
        return teacher.user
    return None

@auth_bp.route('/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    identifier = (data.get('username') or data.get('email') or data.get('identifier') or '').strip()
    password = data.get('password')

    if not identifier or not password:
        return jsonify({'success': False, 'error': {'code': 'MISSING_FIELDS', 'message': 'Username/Email/NIS dan password wajib diisi'}}), 400

    user = find_user_by_identifier(identifier)
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': {'code': 'INVALID_CREDENTIALS', 'message': 'Username, email, NIS, atau password salah'}}), 401

    if not user.is_active:
        return jsonify({'success': False, 'error': {'code': 'ACCOUNT_INACTIVE', 'message': 'Akun Anda dinonaktifkan'}}), 403

    user.last_login = datetime.utcnow()
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    session['user_id'] = user.id
    session['role'] = user.role
    session['user_name'] = user.name

    record_audit('LOGIN', 'users', user.id, None, 'User logged in via API', user_id=user.id)

    return jsonify({
        'success': True,
        'token': token,
        'user': user.to_dict()
    })

@auth_bp.route('/me', methods=['GET'])
def api_me():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': {'code': 'UNAUTHORIZED', 'message': 'Belum login'}}), 401
    return jsonify({'success': True, 'user': user.to_dict()})

@auth_views.route('/login', methods=['GET', 'POST'])
def login():
    user = get_current_user()
    if user:
        return redirect(url_for('views.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        target_user = find_user_by_identifier(identifier)
        if target_user and target_user.check_password(password):
            if not target_user.is_active:
                flash('Akun Anda dinonaktifkan oleh administrator.', 'danger')
                return render_template('login.html')

            target_user.last_login = datetime.utcnow()
            db.session.commit()

            session['user_id'] = target_user.id
            session['role'] = target_user.role
            session['user_name'] = target_user.name

            record_audit('LOGIN', 'users', target_user.id, None, 'User logged in via Web UI', user_id=target_user.id)
            return redirect(url_for('views.dashboard'))
        else:
            flash('Username/Email/NIS atau password tidak sesuai.', 'danger')

    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
def api_logout():
    user = get_current_user()
    user_id = user.id if user else session.get('user_id')
    user_name = user.name if user else session.get('user_name', 'User')
    role = user.role if user else session.get('role', '')

    if user_id:
        record_audit(
            action='LOGOUT',
            table_name='users',
            record_id=user_id,
            old_value=None,
            new_value=f'Pengguna {user_name} ({role}) logout via REST API',
            user_id=user_id
        )
    session.clear()
    return jsonify({'success': True, 'message': 'Logout berhasil dicatat'})

@auth_views.route('/logout', methods=['GET', 'POST'])
def logout():
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'User')
    role = session.get('role', '')

    if user_id:
        record_audit(
            action='LOGOUT',
            table_name='users',
            record_id=user_id,
            old_value=None,
            new_value=f'Pengguna {user_name} ({role}) berhasil logout dari sistem',
            user_id=user_id
        )
    session.clear()
    return redirect(url_for('auth_views.login'))
