import re
from flask import Blueprint, request, jsonify, g
from app.extensions import db, bcrypt
from app.models.user import User
from app.models.academic import Class, Subject, Teacher, Student, Parent, Schedule
from app.models.log import AuditLog
from app.utils.decorators import role_required, record_audit

master_bp = Blueprint('master', __name__, url_prefix='/api/v1')

# ----------------- CLASSES -----------------
@master_bp.route('/classes', methods=['GET'])
def get_classes():
    classes = Class.query.all()
    return jsonify({'success': True, 'data': [c.to_dict() for c in classes]})

@master_bp.route('/classes', methods=['POST'])
@role_required('admin', 'superadmin')
def create_class():
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'error': {'message': 'Nama kelas wajib diisi'}}), 400

    cls = Class(
        name=name,
        grade_level=data.get('grade_level', ''),
        academic_year=data.get('academic_year', '2025/2026'),
        homeroom_teacher_id=data.get('homeroom_teacher_id')
    )
    db.session.add(cls)
    db.session.commit()
    record_audit('CREATE_CLASS', 'classes', cls.id, None, name)
    return jsonify({'success': True, 'data': cls.to_dict()}), 201

# ----------------- SUBJECTS -----------------
@master_bp.route('/subjects', methods=['GET'])
def get_subjects():
    subjects = Subject.query.all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in subjects]})

@master_bp.route('/subjects', methods=['POST'])
@role_required('admin', 'superadmin')
def create_subject():
    data = request.get_json() or {}
    code = data.get('code')
    name = data.get('name')
    if not code or not name:
        return jsonify({'success': False, 'error': {'message': 'Kode dan nama mata pelajaran wajib diisi'}}), 400

    subject = Subject(code=code, name=name)
    db.session.add(subject)
    db.session.commit()
    record_audit('CREATE_SUBJECT', 'subjects', subject.id, None, f"{code} - {name}")
    return jsonify({'success': True, 'data': subject.to_dict()}), 201

# ----------------- TEACHERS -----------------
@master_bp.route('/teachers', methods=['GET'])
def get_teachers():
    teachers = Teacher.query.all()
    return jsonify({'success': True, 'data': [t.to_dict() for t in teachers]})

@master_bp.route('/teachers', methods=['POST'])
@role_required('admin', 'superadmin')
def create_teacher():
    data = request.get_json() or {}
    nip = data.get('nip')
    first_name = data.get('first_name')
    email = data.get('email')
    password = data.get('password', 'guru12345')

    if not nip or not first_name or not email:
        return jsonify({'success': False, 'error': {'message': 'NIP, nama depan, dan email wajib diisi'}}), 400

    # Create User account for Teacher
    username = data.get('username') or nip
    user = User(username=username, name=f"{first_name} {data.get('last_name', '')}".strip(), email=email, role='teacher')
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    teacher = Teacher(
        user_id=user.id,
        nip=nip,
        first_name=first_name,
        last_name=data.get('last_name', ''),
        phone=data.get('phone', ''),
        email=email
    )
    db.session.add(teacher)
    db.session.commit()

    record_audit('CREATE_TEACHER', 'teachers', teacher.id, None, teacher.full_name)
    return jsonify({'success': True, 'data': teacher.to_dict()}), 201

# ----------------- STUDENTS -----------------
@master_bp.route('/students', methods=['GET'])
def get_students():
    class_id = request.args.get('class_id', type=int)
    query = Student.query
    if class_id:
        query = query.filter_by(class_id=class_id)
    students = query.all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in students]})

@master_bp.route('/students', methods=['POST'])
@role_required('admin', 'superadmin')
def create_student():
    data = request.get_json() or {}
    nis = (data.get('nis') or '').strip()
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()
    class_id = data.get('class_id')
    parent_id = data.get('parent_id')

    if not nis or not first_name:
        return jsonify({'success': False, 'error': {'message': 'NIS dan nama depan wajib diisi'}}), 400

    # 1. Check duplicate NIS
    if Student.query.filter_by(nis=nis).first():
        return jsonify({'success': False, 'error': {'message': f'NIS/NIM {nis} sudah terdaftar pada siswa lain'}}), 400

    # 2. Process username
    raw_username = (data.get('username') or '').strip()
    if not raw_username:
        # Default: siswa_<first_name_lowercase>
        base_name = re.sub(r'[^a-zA-Z0-9_]', '', first_name.lower()) or 'siswa'
        candidate = f"siswa_{base_name}"
        counter = 1
        while User.query.filter_by(username=candidate).first():
            candidate = f"siswa_{base_name}{counter}"
            counter += 1
        username = candidate
    else:
        username = raw_username
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': {'message': f'Username "{username}" sudah digunakan oleh akun lain'}}), 400

    # 3. Process email
    raw_email = (data.get('email') or '').strip()
    if not raw_email:
        email = f"{nis}@student.umg.ac.id"
    else:
        email = raw_email

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': {'message': f'Email "{email}" sudah digunakan oleh akun lain'}}), 400

    # 4. Process password
    password = (data.get('password') or '').strip() or 'siswa123'

    # Create User Account for the student
    user = User(
        username=username,
        name=f"{first_name} {last_name}".strip(),
        email=email,
        role='student'
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    # Create Student profile
    student = Student(
        user_id=user.id,
        nis=nis,
        first_name=first_name,
        last_name=last_name,
        class_id=int(class_id) if class_id else None,
        parent_id=int(parent_id) if parent_id else None,
        status='active'
    )
    db.session.add(student)

    # Automatically enroll into subjects taught in this class
    if student.class_id:
        schedules = Schedule.query.filter_by(class_id=student.class_id).all()
        for sched in schedules:
            if sched.subject and sched.subject not in student.enrolled_subjects:
                student.enrolled_subjects.append(sched.subject)

    db.session.commit()

    record_audit('CREATE_STUDENT', 'students', student.id, None, f"Dibuat siswa {student.full_name} ({username})")
    
    res_data = student.to_dict()
    res_data['credentials'] = {
        'username': username,
        'email': email,
        'nis': nis
    }
    return jsonify({
        'success': True,
        'message': f'Siswa {student.full_name} berhasil ditambahkan dengan username: {username}',
        'data': res_data
    }), 201

@master_bp.route('/students/<int:student_id>/reset-password', methods=['POST', 'PUT'])
@role_required('admin', 'superadmin')
def reset_student_password(student_id):
    student = Student.query.get(student_id)
    if not student or not student.user:
        return jsonify({'success': False, 'error': {'message': 'Data siswa atau akun login tidak ditemukan'}}), 404

    data = request.get_json() or {}
    new_password = (data.get('password') or data.get('new_password') or '').strip()
    if not new_password:
        return jsonify({'success': False, 'error': {'message': 'Password baru tidak boleh kosong'}}), 400

    student.user.set_password(new_password)
    db.session.commit()
    record_audit('RESET_PASSWORD', 'users', student.user.id, None, f"Admin mereset password siswa {student.full_name}")

    return jsonify({
        'success': True,
        'message': f'Password untuk akun {student.user.username} ({student.full_name}) berhasil diperbarui.',
        'data': {
            'student_id': student.id,
            'nis': student.nis,
            'username': student.user.username
        }
    })

# ----------------- SCHEDULES -----------------
@master_bp.route('/schedules', methods=['GET'])
def get_schedules():
    class_id = request.args.get('class_id', type=int)
    teacher_id = request.args.get('teacher_id', type=int)
    query = Schedule.query
    if class_id:
        query = query.filter_by(class_id=class_id)
    if teacher_id:
        query = query.filter_by(teacher_id=teacher_id)
    schedules = query.all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in schedules]})

@master_bp.route('/schedules', methods=['POST'])
@role_required('admin', 'superadmin')
def create_schedule():
    data = request.get_json() or {}
    sched = Schedule(
        class_id=data.get('class_id'),
        subject_id=data.get('subject_id'),
        teacher_id=data.get('teacher_id'),
        day_of_week=data.get('day_of_week', 'Senin'),
        start_time=data.get('start_time', '08:00'),
        end_time=data.get('end_time', '09:30'),
        room=data.get('room', 'R. Kelas')
    )
    db.session.add(sched)
    db.session.commit()
    record_audit('CREATE_SCHEDULE', 'schedules', sched.id, None, f"{sched.day_of_week} {sched.start_time}")
    return jsonify({'success': True, 'data': sched.to_dict()}), 201

# ----------------- AUDIT LOGS -----------------
@master_bp.route('/audit-logs', methods=['GET'])
@role_required('admin', 'superadmin')
def get_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify({'success': True, 'data': [l.to_dict() for l in logs]})
