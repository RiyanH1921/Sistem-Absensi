from functools import wraps
from flask import session, request, jsonify, redirect, url_for, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User
from app.models.log import AuditLog
from app.extensions import db

def get_current_user():
    """
    Get current user either from session (for web pages) or JWT (for REST API).
    """
    # 1. Try from Flask session
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user and user.is_active:
            return user

    # 2. Try from JWT token if header present
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                user = User.query.get(identity)
                if user and user.is_active:
                    return user
        except Exception:
            pass

    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': {'code': 'UNAUTHORIZED', 'message': 'Autentikasi diperlukan'}}), 401
            return redirect(url_for('auth_views.login', next=request.url))
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': {'code': 'UNAUTHORIZED', 'message': 'Autentikasi diperlukan'}}), 401
                return redirect(url_for('auth_views.login'))

            if 'superadmin' in [r.lower() for r in allowed_roles] and user.role == 'superadmin':
                # Superadmin always allowed if in list or by default
                g.current_user = user
                return f(*args, **kwargs)

            if user.role not in allowed_roles:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': {'code': 'FORBIDDEN', 'message': 'Akses ditolak: role tidak sesuai'}}), 403
                return render_unauthorized()
            
            g.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def render_unauthorized():
    return """
    <div style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1 style="color: #ef4444;">403 - Akses Ditolak</h1>
        <p>Anda tidak memiliki hak akses untuk membuka halaman ini.</p>
        <a href="/dashboard" style="color: #2563eb; text-decoration: underline;">Kembali ke Dashboard</a>
    </div>
    """, 403

def record_audit(action: str, table_name: str, record_id: int = None, old_value: str = None, new_value: str = None, user_id: int = None):
    try:
        if user_id is None:
            user = get_current_user()
            user_id = user.id if user else None
        
        client_ip = request.remote_addr if request else '127.0.0.1'
        log = AuditLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_value=str(old_value) if old_value else None,
            new_value=str(new_value) if new_value else None,
            ip=client_ip
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
