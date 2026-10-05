import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, g, current_app
from app.extensions import db
from app.models.academic import Student
from app.models.attendance import Attendance, LeaveRequest, Lesson
from app.models.log import Notification
from app.services.attendance_service import AttendanceService
from app.utils.decorators import role_required, get_current_user, record_audit

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/v1')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@attendance_bp.route('/attendance/scan', methods=['POST'])
@role_required('student')
def scan_attendance():
    user = g.current_user
    student = user.student_profile
    if not student:
        return jsonify({'success': False, 'error': {'code': 'STUDENT_PROFILE_NOT_FOUND', 'message': 'Profil siswa tidak ditemukan'}}), 404

    data = request.get_json() or {}
    qr_payload = data.get('qr_payload', '').strip()
    user_lat = data.get('latitude')
    user_lon = data.get('longitude')
    device_hash = data.get('device_hash')

    if not qr_payload:
        return jsonify({'success': False, 'error': {'code': 'INVALID_PAYLOAD', 'message': 'Payload QR code tidak valid atau kosong'}}), 400

    try:
        lesson_id = int(qr_payload.split(':')[0])
    except (ValueError, IndexError):
        return jsonify({'success': False, 'error': {'code': 'INVALID_QR_FORMAT', 'message': 'Format QR code tidak sesuai'}}), 400

    if user_lat is not None:
        user_lat = float(user_lat)
    if user_lon is not None:
        user_lon = float(user_lon)

    success, result = AttendanceService.process_qr_scan(
        student=student,
        lesson_id=lesson_id,
        qr_payload=qr_payload,
        user_lat=user_lat,
        user_lon=user_lon,
        device_hash=device_hash
    )

    if not success:
        return jsonify({'success': False, 'error': result}), 400

    return jsonify({
        'success': True,
        'data': result
    })

@attendance_bp.route('/attendance/<int:attendance_id>', methods=['PUT'])
@role_required('teacher', 'admin', 'superadmin')
def manual_update_attendance(attendance_id):
    user = g.current_user
    data = request.get_json() or {}
    new_status = data.get('status')
    reason = data.get('reason', '').strip()

    valid_statuses = ['present', 'late', 'sick', 'permit', 'absent']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'error': {'code': 'INVALID_STATUS', 'message': f'Status tidak valid. Harus salah satu dari {valid_statuses}'}}), 400

    if not reason:
        return jsonify({'success': False, 'error': {'code': 'REASON_REQUIRED', 'message': 'Alasan koreksi manual wajib disertakan'}}), 400

    success, msg = AttendanceService.manual_update(attendance_id, new_status, reason, user.id)
    if not success:
        return jsonify({'success': False, 'error': {'code': 'UPDATE_FAILED', 'message': msg}}), 404

    return jsonify({'success': True, 'message': msg})

@attendance_bp.route('/leave-requests', methods=['POST'])
@role_required('student')
def create_leave_request():
    user = g.current_user
    student = user.student_profile
    if not student:
        return jsonify({'success': False, 'error': {'code': 'STUDENT_NOT_FOUND', 'message': 'Profil siswa tidak ditemukan'}}), 404

    # Support form-data or JSON
    date_from_str = request.form.get('date_from') or request.json.get('date_from')
    date_to_str = request.form.get('date_to') or request.json.get('date_to')
    leave_type = request.form.get('type') or request.json.get('type')  # sick, permit
    reason = request.form.get('reason') or request.json.get('reason')

    if not date_from_str or not date_to_str or not leave_type or not reason:
        return jsonify({'success': False, 'error': {'code': 'MISSING_FIELDS', 'message': 'Tanggal mulai, tanggal selesai, jenis izin, dan alasan wajib diisi'}}), 400

    date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
    date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()

    attachment_filename = None
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename and allowed_file(file.filename):
            filename = f"leave_{student.id}_{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            attachment_filename = filename

    leave_req = LeaveRequest(
        student_id=student.id,
        date_from=date_from,
        date_to=date_to,
        type=leave_type,
        reason=reason,
        attachment_path=attachment_filename,
        status='pending'
    )
    db.session.add(leave_req)
    db.session.commit()

    record_audit('SUBMIT_LEAVE', 'leave_requests', leave_req.id, None, f"{leave_type}: {reason}", user_id=user.id)

    return jsonify({
        'success': True,
        'message': 'Pengajuan izin berhasil dikirim dan menunggu persetujuan.',
        'leave_request': leave_req.to_dict()
    }), 201

@attendance_bp.route('/leave-requests/<int:request_id>', methods=['PATCH'])
@role_required('teacher', 'admin', 'superadmin')
def review_leave_request(request_id):
    user = g.current_user
    leave_req = LeaveRequest.query.get(request_id)
    if not leave_req:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Pengajuan tidak ditemukan'}}), 404

    data = request.get_json() or {}
    new_status = data.get('status')  # approved, rejected
    review_notes = data.get('notes', '')

    if new_status not in ['approved', 'rejected']:
        return jsonify({'success': False, 'error': {'code': 'INVALID_STATUS', 'message': 'Status harus approved atau rejected'}}), 400

    leave_req.status = new_status
    leave_req.reviewed_by = user.id
    leave_req.reviewed_at = datetime.utcnow()
    leave_req.review_notes = review_notes

    # If approved, update existing attendance records within date range to sick/permit
    if new_status == 'approved':
        status_map = 'sick' if leave_req.type == 'sick' else 'permit'
        lessons_in_range = Lesson.query.filter(
            Lesson.class_id == leave_req.student.class_id,
            Lesson.date >= leave_req.date_from,
            Lesson.date <= leave_req.date_to
        ).all()

        for les in lessons_in_range:
            att = Attendance.query.filter_by(lesson_id=les.id, student_id=leave_req.student_id).first()
            if att:
                att.status = status_map
                att.method = 'leave'
                att.note = f"Izin disetujui: {leave_req.reason}"
            else:
                att = Attendance(
                    lesson_id=les.id,
                    student_id=leave_req.student_id,
                    status=status_map,
                    method='leave',
                    note=f"Izin disetujui: {leave_req.reason}"
                )
                db.session.add(att)

    # Send notification to student user
    if leave_req.student.user_id:
        status_text = 'disetujui' if new_status == 'approved' else 'ditolak'
        notif = Notification(
            user_id=leave_req.student.user_id,
            title=f"Pengajuan Izin {status_text.capitalize()}",
            body=f"Pengajuan izin Anda untuk tanggal {leave_req.date_from} s.d. {leave_req.date_to} telah {status_text}."
        )
        db.session.add(notif)

    db.session.commit()
    record_audit('REVIEW_LEAVE', 'leave_requests', leave_req.id, 'pending', new_status, user_id=user.id)

    return jsonify({
        'success': True,
        'message': f'Pengajuan izin berhasil di-{new_status}',
        'leave_request': leave_req.to_dict()
    })
