from datetime import datetime, timedelta
import secrets
from app.extensions import db
from app.models.academic import Student, Class, Schedule, Subject, Teacher
from app.models.attendance import Lesson, Attendance, AbsenceReason
from app.models.log import AuditLog, Notification
from app.utils.geo import is_within_radius
from app.utils.qr_engine import verify_qr_payload
from app.utils.decorators import record_audit

class AttendanceService:

    @staticmethod
    def open_lesson(teacher_id: int, class_id: int, subject_id: int, schedule_id: int = None,
                    latitude: float = None, longitude: float = None, radius_m: float = 100.0,
                    late_tolerance_minutes: int = 15):
        """
        Creates/opens a new attendance lesson session.
        """
        # Close any already open session for this teacher and subject on today
        today = datetime.utcnow().date()
        open_existing = Lesson.query.filter_by(teacher_id=teacher_id, subject_id=subject_id, date=today, status='open').first()
        if open_existing:
            if radius_m is not None:
                open_existing.radius_m = radius_m
            if late_tolerance_minutes is not None:
                open_existing.late_tolerance_minutes = late_tolerance_minutes
            if latitude is not None:
                open_existing.latitude = latitude
            if longitude is not None:
                open_existing.longitude = longitude
            db.session.commit()
            return open_existing

        lesson = Lesson(
            schedule_id=schedule_id,
            class_id=class_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            date=today,
            open_at=datetime.utcnow(),
            status='open',
            qr_secret=secrets.token_hex(16),
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            late_tolerance_minutes=late_tolerance_minutes
        )
        db.session.add(lesson)
        db.session.commit()

        record_audit('OPEN_LESSON', 'lessons', lesson.id, None, f"Opened lesson for class {class_id} subject {subject_id}")
        return lesson

    @staticmethod
    def close_lesson(lesson_id: int, user_id: int = None):
        """
        Closes lesson session and automatically marks remaining students as Alpa (absent).
        """
        lesson = Lesson.query.get(lesson_id)
        if not lesson or lesson.status == 'closed':
            return lesson

        lesson.status = 'closed'
        lesson.close_at = datetime.utcnow()

        # Find all students in this class
        students = Student.query.filter_by(class_id=lesson.class_id, status='active').all()
        existing_student_ids = {a.student_id for a in lesson.attendances}

        for student in students:
            if student.id not in existing_student_ids:
                # Automatically mark as Alpa (absent)
                absent_record = Attendance(
                    lesson_id=lesson.id,
                    student_id=student.id,
                    status='absent',
                    checked_in_at=datetime.utcnow(),
                    method='manual',
                    note='Otomatis Alpa saat sesi presensi ditutup'
                )
                db.session.add(absent_record)
                
                # Send notification to parent if student has a parent user
                if student.parent and student.parent.user_id:
                    notif = Notification(
                        user_id=student.parent.user_id,
                        title=f"Ketidakhadiran: {student.full_name}",
                        body=f"Anak Anda, {student.full_name}, tercatat Alpa pada mata pelajaran {lesson.subject.name} ({lesson.date})."
                    )
                    db.session.add(notif)

        db.session.commit()
        record_audit('CLOSE_LESSON', 'lessons', lesson.id, 'open', 'closed', user_id=user_id)
        return lesson

    @staticmethod
    def process_qr_scan(student: Student, lesson_id: int, qr_payload: str,
                          user_lat: float = None, user_lon: float = None,
                          device_hash: str = None):
        """
        Validates QR scan according to 8-step server verification from blueprint.
        """
        # Step 1 & 2: Lesson exists and status open
        lesson = Lesson.query.get(lesson_id)
        if not lesson or lesson.status != 'open':
            return False, {'code': 'LESSON_CLOSED', 'message': 'Sesi presensi ini tidak ditemukan atau sudah ditutup.'}

        # Step 3: Student enrolled in class
        if student.class_id != lesson.class_id:
            return False, {'code': 'NOT_ENROLLED', 'message': 'Anda tidak terdaftar pada kelas presensi ini.'}

        # Step 4: Validate dynamic QR HMAC signature
        rotation = 30
        is_qr_valid = verify_qr_payload(qr_payload, lesson.id, lesson.qr_secret, rotation_seconds=rotation)
        if not is_qr_valid:
            return False, {'code': 'QR_EXPIRED', 'message': 'Kode QR sudah kedaluwarsa atau tidak valid. Silakan scan ulang kode terbaru.'}

        # Step 5: Check duplicate attendance
        existing = Attendance.query.filter_by(lesson_id=lesson.id, student_id=student.id).first()
        if existing and existing.status in ['present', 'late']:
            return False, {'code': 'ALREADY_CHECKED_IN', 'message': f'Anda sudah melakukan presensi sebelumnya dengan status {existing.status.upper()}.'}

        # Step 6: Validate GPS Location radius (hanya jika radius > 0)
        is_flagged = False
        flag_reason = None
        if lesson.latitude is not None and lesson.longitude is not None and (lesson.radius_m or 0) > 0:
            if user_lat is None or user_lon is None:
                return False, {'code': 'GPS_REQUIRED', 'message': 'Akses lokasi GPS diperlukan untuk melakukan presensi.'}
            
            in_radius, distance_m = is_within_radius(user_lat, user_lon, lesson.latitude, lesson.longitude, lesson.radius_m)
            if not in_radius:
                return False, {'code': 'OUT_OF_RADIUS', 'message': f'Lokasi Anda berada di luar radius presensi ({distance_m:.1f} m dari titik pusat, batas maks {lesson.radius_m} m).'}

        # Step 7: Check punctuality (Hadir vs Terlambat)
        now = datetime.utcnow()
        late_cutoff = lesson.open_at + timedelta(minutes=lesson.late_tolerance_minutes)
        attendance_status = 'present' if now <= late_cutoff else 'late'

        # Step 8: Fraud detection (Device Hash)
        if device_hash:
            same_device_attendance = Attendance.query.filter(
                Attendance.lesson_id == lesson.id,
                Attendance.device_hash == device_hash,
                Attendance.student_id != student.id
            ).first()
            if same_device_attendance:
                is_flagged = True
                flag_reason = f'Device yang sama digunakan oleh siswa lain ({same_device_attendance.student.full_name})'

        # Save or update attendance
        if existing:
            attendance = existing
            attendance.status = attendance_status
            attendance.checked_in_at = now
            attendance.method = 'qr'
            attendance.latitude = user_lat
            attendance.longitude = user_lon
            attendance.device_hash = device_hash
            attendance.is_flagged = is_flagged
            attendance.flag_reason = flag_reason
            attendance.note = 'Presensi via Scan QR'
        else:
            attendance = Attendance(
                lesson_id=lesson.id,
                student_id=student.id,
                status=attendance_status,
                checked_in_at=now,
                method='qr',
                latitude=user_lat,
                longitude=user_lon,
                device_hash=device_hash,
                is_flagged=is_flagged,
                flag_reason=flag_reason,
                note='Presensi via Scan QR'
            )
            db.session.add(attendance)

        db.session.commit()

        record_audit('SCAN_QR', 'attendances', attendance.id, None, f"Status: {attendance_status}", user_id=student.user_id)

        msg = 'Presensi berhasil dicatat (Hadir tepat waktu).' if attendance_status == 'present' else f'Presensi dicatat (Terlambat, lewat {lesson.late_tolerance_minutes} menit).'
        return True, {
            'attendance_id': attendance.id,
            'status': attendance_status,
            'is_flagged': is_flagged,
            'flag_reason': flag_reason,
            'message': msg
        }

    @staticmethod
    def manual_update(attendance_id: int, new_status: str, reason: str, teacher_user_id: int):
        attendance = Attendance.query.get(attendance_id)
        if not attendance:
            return False, "Data presensi tidak ditemukan"

        old_status = attendance.status
        attendance.status = new_status
        attendance.method = 'manual'
        attendance.note = f"Koreksi manual oleh guru: {reason}"
        db.session.commit()

        record_audit('MANUAL_CORRECTION', 'attendances', attendance.id, old_status, f"{new_status} (Alasan: {reason})", user_id=teacher_user_id)
        return True, "Data presensi berhasil diperbarui"
