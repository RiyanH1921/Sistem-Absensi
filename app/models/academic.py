from datetime import datetime
from app.extensions import db

# Association tables
teacher_subject = db.Table('teacher_subject',
    db.Column('teacher_id', db.Integer, db.ForeignKey('teachers.id'), primary_key=True),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'), primary_key=True)
)

student_subject = db.Table('student_subject',
    db.Column('student_id', db.Integer, db.ForeignKey('students.id'), primary_key=True),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'), primary_key=True)
)

class Parent(db.Model):
    __tablename__ = 'parents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), default='')
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    students = db.relationship('Student', backref='parent', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'email': self.email
        }

class Class(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)
    grade_level = db.Column(db.String(20), nullable=True)  # e.g., '10', '11', '12' or 'Semester 5'
    academic_year = db.Column(db.String(30), default='2025/2026')
    homeroom_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)

    # Relationships
    students = db.relationship('Student', backref='class_room', lazy=True)
    schedules = db.relationship('Schedule', backref='class_room', lazy=True, cascade='all, delete-orphan')
    lessons = db.relationship('Lesson', backref='class_room', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'grade_level': self.grade_level,
            'academic_year': self.academic_year,
            'homeroom_teacher': self.homeroom_teacher.full_name if self.homeroom_teacher else None,
            'total_students': len(self.students)
        }

class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    nip = db.Column(db.String(40), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), default='')
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    # Relationships
    homeroom_classes = db.relationship('Class', backref='homeroom_teacher', foreign_keys=[Class.homeroom_teacher_id])
    subjects = db.relationship('Subject', secondary=teacher_subject, backref=db.backref('teachers', lazy='dynamic'))
    schedules = db.relationship('Schedule', backref='teacher', lazy=True)
    lessons = db.relationship('Lesson', backref='teacher', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'nip': self.nip,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'email': self.email,
            'subjects': [s.name for s in self.subjects]
        }

class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    nis = db.Column(db.String(40), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), default='')
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parents.id'), nullable=True)
    status = db.Column(db.String(20), default='active')  # active, graduated, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    enrolled_subjects = db.relationship('Subject', secondary=student_subject, backref=db.backref('students', lazy='dynamic'))
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')
    leave_requests = db.relationship('LeaveRequest', backref='student', lazy=True, cascade='all, delete-orphan')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'nis': self.nis,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'class_id': self.class_id,
            'class_name': self.class_room.name if self.class_room else '-',
            'parent_name': self.parent.full_name if self.parent else '-',
            'parent_phone': self.parent.phone if self.parent else '-',
            'status': self.status
        }

class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)

    # Relationships
    schedules = db.relationship('Schedule', backref='subject', lazy=True, cascade='all, delete-orphan')
    lessons = db.relationship('Lesson', backref='subject', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name
        }

class Schedule(db.Model):
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)  # Senin, Selasa, dst.
    start_time = db.Column(db.String(10), nullable=False)   # HH:MM e.g. "08:00"
    end_time = db.Column(db.String(10), nullable=False)     # HH:MM e.g. "09:30"
    room = db.Column(db.String(50), default='R. Teori 1')

    # Relationships
    lessons = db.relationship('Lesson', backref='schedule', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'class_id': self.class_id,
            'class_name': self.class_room.name if self.class_room else '',
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else '',
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher.full_name if self.teacher else '',
            'day_of_week': self.day_of_week,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'room': self.room
        }
