from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, session, g, request
from app.models.user import User
from app.models.academic import Class, Subject, Teacher, Student, Parent, Schedule
from app.models.attendance import Lesson, Attendance, LeaveRequest
from app.models.log import AuditLog
from app.utils.decorators import get_current_user, login_required, role_required

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    user = get_current_user()
    if user:
        return redirect(url_for('views.dashboard'))
    return redirect(url_for('auth_views.login'))

@views_bp.route('/dashboard')
@login_required
def dashboard():
    user = g.current_user
    classes = Class.query.all()
    today = datetime.utcnow().date()
    
    # Active lesson for teacher if applicable
    active_lesson = None
    if user.role == 'teacher' and user.teacher_profile:
        active_lesson = Lesson.query.filter_by(teacher_id=user.teacher_profile.id, status='open', date=today).first()
    
    # Recent attendances
    recent_attendances = Attendance.query.order_by(Attendance.checked_in_at.desc()).limit(10).all()

    return render_template('dashboard.html', user=user, classes=classes, active_lesson=active_lesson, recent_attendances=recent_attendances)

@views_bp.route('/lesson/session')
@login_required
def lesson_session():
    user = g.current_user
    if user.role not in ['teacher', 'admin', 'superadmin']:
        return redirect(url_for('views.dashboard'))

    today = datetime.utcnow().date()
    teacher_id = user.teacher_profile.id if user.teacher_profile else None
    
    lesson_id = request.args.get('lesson_id', type=int)
    lesson = None
    if lesson_id:
        lesson = Lesson.query.get(lesson_id)
    elif teacher_id:
        lesson = Lesson.query.filter_by(teacher_id=teacher_id, status='open').order_by(Lesson.id.desc()).first()

    classes = Class.query.all()
    subjects = Subject.query.all()

    return render_template('lesson_session.html', user=user, lesson=lesson, classes=classes, subjects=subjects)

@views_bp.route('/scan')
@login_required
def student_scan():
    user = g.current_user
    if user.role != 'student':
        return redirect(url_for('views.dashboard'))
    
    student = user.student_profile
    return render_template('student_scan.html', user=user, student=student)

@views_bp.route('/attendance/details')
@login_required
def attendance_details():
    user = g.current_user
    student = user.student_profile if user.role == 'student' else None
    
    # If teacher or admin, can pass student_id
    student_id = request.args.get('student_id', type=int)
    if not student and student_id:
        student = Student.query.get(student_id)
    elif not student:
        student = Student.query.first()

    subjects = Subject.query.all()
    selected_subject_id = request.args.get('subject_id', type=int) or (subjects[0].id if subjects else None)

    return render_template('attendance_details.html', user=user, student=student, subjects=subjects, selected_subject_id=selected_subject_id)

@views_bp.route('/leave-requests')
@login_required
def leave_requests_page():
    user = g.current_user
    student = user.student_profile if user.role == 'student' else None

    if user.role == 'student' and student:
        leaves = LeaveRequest.query.filter_by(student_id=student.id).order_by(LeaveRequest.created_at.desc()).all()
    else:
        leaves = LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).all()

    return render_template('leave_requests.html', user=user, student=student, leaves=leaves)

@views_bp.route('/master-data')
@login_required
def master_data_page():
    user = g.current_user
    if user.role not in ['admin', 'superadmin']:
        return redirect(url_for('views.dashboard'))

    classes = Class.query.all()
    teachers = Teacher.query.all()
    students = Student.query.all()
    subjects = Subject.query.all()
    schedules = Schedule.query.all()
    parents = Parent.query.all()
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(30).all()

    return render_template('master_data.html', user=user, classes=classes, teachers=teachers, students=students, subjects=subjects, schedules=schedules, parents=parents, audit_logs=audit_logs)
