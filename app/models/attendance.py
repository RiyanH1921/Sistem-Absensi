from datetime import datetime
import secrets
from app.extensions import db

class AbsenceReason(db.Model):
    __tablename__ = 'absence_reasons'

    id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.String(80), nullable=False, unique=True)

    attendances = db.relationship('Attendance', backref='absence_reason', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'reason': self.reason}

class Lesson(db.Model):
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    open_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    close_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='open')  # open, closed
    qr_secret = db.Column(db.String(64), nullable=False, default=lambda: secrets.token_hex(16))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    radius_m = db.Column(db.Float, default=100.0)
    late_tolerance_minutes = db.Column(db.Integer, default=15)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    attendances = db.relationship('Attendance', backref='lesson', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'schedule_id': self.schedule_id,
            'class_id': self.class_id,
            'class_name': self.class_room.name if self.class_room else '',
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else '',
            'subject_code': self.subject.code if self.subject else '',
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher.full_name if self.teacher else '',
            'date': self.date.strftime('%Y-%m-%d') if self.date else '',
            'open_at': self.open_at.strftime('%Y-%m-%d %H:%M:%S') if self.open_at else '',
            'close_at': self.close_at.strftime('%Y-%m-%d %H:%M:%S') if self.close_at else '',
            'status': self.status,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'radius_m': self.radius_m,
            'late_tolerance_minutes': self.late_tolerance_minutes,
            'total_attendances': len(self.attendances)
        }

class Attendance(db.Model):
    __tablename__ = 'attendances'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    # Status: 'present' (Hadir), 'late' (Terlambat), 'sick' (Sakit), 'permit' (Izin), 'absent' (Alpa)
    status = db.Column(db.String(20), nullable=False, default='absent')
    checked_in_at = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.String(20), default='qr')  # qr, manual, leave
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    device_hash = db.Column(db.String(64), nullable=True)
    is_flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.String(255), nullable=True)
    absence_reason_id = db.Column(db.Integer, db.ForeignKey('absence_reasons.id'), nullable=True)
    note = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('lesson_id', 'student_id', name='uq_lesson_student'),
        db.Index('idx_student_checked_in', 'student_id', 'checked_in_at')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'lesson_id': self.lesson_id,
            'student_id': self.student_id,
            'student_name': self.student.full_name if self.student else '',
            'student_nis': self.student.nis if self.student else '',
            'status': self.status,
            'checked_in_at': self.checked_in_at.strftime('%Y-%m-%d %H:%M:%S') if self.checked_in_at else '',
            'method': self.method,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'device_hash': self.device_hash,
            'is_flagged': self.is_flagged,
            'flag_reason': self.flag_reason,
            'absence_reason': self.absence_reason.reason if self.absence_reason else None,
            'note': self.note
        }

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date_from = db.Column(db.Date, nullable=False)
    date_to = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # sick, permit
    reason = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_leaves')

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.full_name if self.student else '',
            'student_nis': self.student.nis if self.student else '',
            'date_from': self.date_from.strftime('%Y-%m-%d'),
            'date_to': self.date_to.strftime('%Y-%m-%d'),
            'type': self.type,
            'reason': self.reason,
            'attachment_path': self.attachment_path,
            'status': self.status,
            'reviewed_by': self.reviewer.name if self.reviewer else None,
            'reviewed_at': self.reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if self.reviewed_at else None,
            'review_notes': self.review_notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
