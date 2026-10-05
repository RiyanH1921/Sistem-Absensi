import calendar
from datetime import datetime, date
from app.extensions import db
from app.models.user import User
from app.models.academic import Student, Class, Subject, Schedule
from app.models.attendance import Lesson, Attendance

class ReportService:

    @staticmethod
    def get_dashboard_summary():
        today = datetime.utcnow().date()
        total_users = User.query.filter_by(is_active=True).count()
        total_students = Student.query.filter_by(status='active').count()

        # Today attendances across all lessons
        today_lessons = Lesson.query.filter_by(date=today).all()
        today_lesson_ids = [l.id for l in today_lessons]

        hadir = 0
        izin = 0
        sakit = 0
        alpa = 0

        if today_lesson_ids:
            attendances = Attendance.query.filter(Attendance.lesson_id.in_(today_lesson_ids)).all()
            for att in attendances:
                if att.status in ['present', 'late']:
                    hadir += 1
                elif att.status == 'permit':
                    izin += 1
                elif att.status == 'sick':
                    sakit += 1
                elif att.status == 'absent':
                    alpa += 1

        total_sudah_absen = hadir + izin + sakit + alpa
        belum_absen = max(0, total_students - total_sudah_absen)

        return {
            'total_users': total_users,
            'total_students': total_students,
            'hadir_hari_ini': hadir,
            'izin_hari_ini': izin,
            'sakit_hari_ini': sakit,
            'alpa_hari_ini': alpa,
            'total_absen_hari_ini': total_sudah_absen,
            'belum_absen_hari_ini': belum_absen
        }

    @staticmethod
    def get_attendance_chart_data(class_id=None, month=None, year=None):
        now = datetime.utcnow()
        if not month:
            month = now.month
        else:
            month = int(month)

        if not year:
            year = now.year
        else:
            year = int(year)

        num_days = calendar.monthrange(year, month)[1]
        labels = [f"{day:02d}" for day in range(1, num_days + 1)]

        hadir_series = [0] * num_days
        sakit_series = [0] * num_days
        izin_series = [0] * num_days
        alpa_series = [0] * num_days

        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        lesson_query = Lesson.query.filter(Lesson.date >= start_date, Lesson.date <= end_date)
        if class_id and class_id != 'all' and str(class_id).isdigit():
            lesson_query = lesson_query.filter_by(class_id=int(class_id))

        lessons = lesson_query.all()
        lesson_map = {l.id: l.date.day for l in lessons}
        lesson_ids = list(lesson_map.keys())

        if lesson_ids:
            attendances = Attendance.query.filter(Attendance.lesson_id.in_(lesson_ids)).all()
            for att in attendances:
                day_idx = lesson_map[att.lesson_id] - 1
                if 0 <= day_idx < num_days:
                    if att.status in ['present', 'late']:
                        hadir_series[day_idx] += 1
                    elif att.status == 'sick':
                        sakit_series[day_idx] += 1
                    elif att.status == 'permit':
                        izin_series[day_idx] += 1
                    elif att.status == 'absent':
                        alpa_series[day_idx] += 1

        total_hadir = sum(hadir_series)
        total_sakit = sum(sakit_series)
        total_izin = sum(izin_series)
        total_alpa = sum(alpa_series)

        return {
            'labels': labels,
            'hadir': hadir_series,
            'sakit': sakit_series,
            'izin': izin_series,
            'alpa': alpa_series,
            'totals': {
                'hadir': total_hadir,
                'sakit': total_sakit,
                'izin': total_izin,
                'alpa': total_alpa,
                'grand_total': total_hadir + total_sakit + total_izin + total_alpa
            }
        }

    @staticmethod
    def get_student_monthly_grid(student_id: int, subject_id: int = None, month: int = None, year: int = None):
        """
        Returns grid of attendance for days 1 to 31 matching Gambar 5.
        """
        now = datetime.utcnow()
        month = int(month) if month else now.month
        year = int(year) if year else now.year
        num_days = calendar.monthrange(year, month)[1]

        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        lesson_query = Lesson.query.filter(Lesson.date >= start_date, Lesson.date <= end_date)
        if subject_id:
            lesson_query = lesson_query.filter_by(subject_id=subject_id)
        lessons = lesson_query.all()

        lesson_ids = [l.id for l in lessons]
        attendances = {}
        if lesson_ids:
            records = Attendance.query.filter(
                Attendance.lesson_id.in_(lesson_ids),
                Attendance.student_id == student_id
            ).all()
            for rec in records:
                # Map by day of month
                day = rec.lesson.date.day
                attendances[day] = rec.status

        # Build day 1..31 grid
        grid = []
        present_count = 0
        class_count = len(lessons)

        for day in range(1, 32):
            if day <= num_days:
                status = attendances.get(day, None)
                if status in ['present', 'late']:
                    present_count += 1
                grid.append({'day': day, 'status': status, 'valid_day': True})
            else:
                grid.append({'day': day, 'status': None, 'valid_day': False})

        return {
            'month': month,
            'year': year,
            'month_name': calendar.month_name[month],
            'total_classes': class_count,
            'my_presence': present_count,
            'grid': grid
        }
