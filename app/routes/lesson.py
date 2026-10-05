from flask import Blueprint, request, jsonify, g
from app.models.academic import Teacher, Schedule
from app.models.attendance import Lesson
from app.services.attendance_service import AttendanceService
from app.utils.qr_engine import generate_qr_payload, generate_qr_base64_image
from app.utils.decorators import role_required, get_current_user

lesson_bp = Blueprint('lesson', __name__, url_prefix='/api/v1/lessons')

@lesson_bp.route('', methods=['POST'])
@role_required('teacher', 'admin', 'superadmin')
def create_lesson():
    user = g.current_user
    data = request.get_json() or {}

    teacher_id = data.get('teacher_id')
    if not teacher_id and user.teacher_profile:
        teacher_id = user.teacher_profile.id

    class_id = data.get('class_id')
    subject_id = data.get('subject_id')
    schedule_id = data.get('schedule_id')
    lat = data.get('latitude')
    lng = data.get('longitude')
    radius_m = data.get('radius_m', 100.0)
    tolerance = data.get('late_tolerance_minutes', 15)

    if not teacher_id or not class_id or not subject_id:
        return jsonify({'success': False, 'error': {'code': 'MISSING_DATA', 'message': 'teacher_id, class_id, dan subject_id wajib diisi'}}), 400

    lesson = AttendanceService.open_lesson(
        teacher_id=teacher_id,
        class_id=class_id,
        subject_id=subject_id,
        schedule_id=schedule_id,
        latitude=lat,
        longitude=lng,
        radius_m=radius_m,
        late_tolerance_minutes=tolerance
    )

    # Generate initial dynamic QR
    qr_payload = generate_qr_payload(lesson.id, lesson.qr_secret, rotation_seconds=30)
    qr_img = generate_qr_base64_image(qr_payload)

    return jsonify({
        'success': True,
        'lesson': lesson.to_dict(),
        'qr': {
            'payload': qr_payload,
            'image': qr_img,
            'rotation_seconds': 30
        }
    }), 201

@lesson_bp.route('/<int:lesson_id>/qr', methods=['GET'])
@role_required('teacher', 'admin', 'superadmin')
def get_lesson_qr(lesson_id):
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Sesi presensi tidak ditemukan'}}), 404

    if lesson.status != 'open':
        return jsonify({'success': False, 'error': {'code': 'LESSON_CLOSED', 'message': 'Sesi sudah ditutup'}}), 400

    payload = generate_qr_payload(lesson.id, lesson.qr_secret, rotation_seconds=30)
    img_data = generate_qr_base64_image(payload)

    return jsonify({
        'success': True,
        'lesson_id': lesson.id,
        'payload': payload,
        'image': img_data,
        'rotation_seconds': 30
    })

@lesson_bp.route('/<int:lesson_id>/close', methods=['POST'])
@role_required('teacher', 'admin', 'superadmin')
def close_lesson(lesson_id):
    user = g.current_user
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Sesi presensi tidak ditemukan'}}), 404

    closed_lesson = AttendanceService.close_lesson(lesson.id, user_id=user.id)

    return jsonify({
        'success': True,
        'message': 'Sesi presensi berhasil ditutup. Siswa yang belum absen otomatis tercatat Alpa.',
        'lesson': closed_lesson.to_dict()
    })

@lesson_bp.route('/<int:lesson_id>/live', methods=['GET'])
def get_live_attendances(lesson_id):
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Sesi tidak ditemukan'}}), 404

    attendances = [a.to_dict() for a in lesson.attendances]
    return jsonify({
        'success': True,
        'lesson': lesson.to_dict(),
        'attendances': attendances,
        'stats': {
            'total': len(attendances),
            'present': sum(1 for a in attendances if a['status'] == 'present'),
            'late': sum(1 for a in attendances if a['status'] == 'late'),
            'sick': sum(1 for a in attendances if a['status'] == 'sick'),
            'permit': sum(1 for a in attendances if a['status'] == 'permit'),
            'absent': sum(1 for a in attendances if a['status'] == 'absent')
        }
    })
