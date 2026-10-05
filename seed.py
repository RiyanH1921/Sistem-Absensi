import sys
import os

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from datetime import datetime, date, timedelta
import random
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.academic import Class, Subject, Teacher, Student, Parent, Schedule
from app.models.attendance import Lesson, Attendance, AbsenceReason, LeaveRequest
from app.models.log import AuditLog, Notification

app = create_app()

def run_seed():
    with app.app_context():
        print("[*] Menginisialisasi database & seeding data...")
        db.create_all()

        # Check if already seeded
        if User.query.filter_by(username='superadmin').first():
            print("[INFO] Database sudah memiliki data awal.")
            return

        # 1. Absence Reasons
        reasons = ['Sakit', 'Izin', 'Dispensasi', 'Alpa', 'Lainnya']
        for r in reasons:
            db.session.add(AbsenceReason(reason=r))
        db.session.commit()

        # 2. Super Admin & Admin
        superadmin = User(username='superadmin', name='Super Administrator', email='superadmin@presensi.cloud', role='superadmin')
        superadmin.set_password('admin123')
        db.session.add(superadmin)

        admin = User(username='admin', name='Admin Akademik', email='admin@presensi.cloud', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)

        # 3. Teachers
        user_guru1 = User(username='guru_budi', name='Budi Santoso, M.Kom.', email='budi@presensi.cloud', role='teacher')
        user_guru1.set_password('guru123')
        db.session.add(user_guru1)
        db.session.flush()

        guru1 = Teacher(
            user_id=user_guru1.id,
            nip='198501012010011001',
            first_name='Budi',
            last_name='Santoso',
            phone='081234567890',
            email='budi@presensi.cloud'
        )
        db.session.add(guru1)

        user_guru2 = User(username='guru_siti', name='Dr. Siti Rahayu, M.T.', email='siti@presensi.cloud', role='teacher')
        user_guru2.set_password('guru123')
        db.session.add(user_guru2)
        db.session.flush()

        guru2 = Teacher(
            user_id=user_guru2.id,
            nip='199002022015022002',
            first_name='Siti',
            last_name='Rahayu',
            phone='081298765432',
            email='siti@presensi.cloud'
        )
        db.session.add(guru2)
        db.session.commit()

        # 4. Classes
        kelas_5a = Class(name='TI-5A Cloud & Web', grade_level='Semester 5', academic_year='2025/2026', homeroom_teacher_id=guru1.id)
        kelas_5b = Class(name='TI-5B Sistem Cerdas', grade_level='Semester 5', academic_year='2025/2026', homeroom_teacher_id=guru2.id)
        db.session.add_all([kelas_5a, kelas_5b])
        db.session.commit()

        # 5. Subjects
        sub_cc = Subject(code='CC501', name='Cloud Computing')
        sub_oop = Subject(code='520202', name='Object Oriented Programming')
        sub_db = Subject(code='DB301', name='Database System & Architecture')
        db.session.add_all([sub_cc, sub_oop, sub_db])
        db.session.commit()

        # Connect teachers to subjects
        guru1.subjects.append(sub_cc)
        guru1.subjects.append(sub_oop)
        guru2.subjects.append(sub_db)
        db.session.commit()

        # 6. Parents
        user_ortu1 = User(username='ortu_riyan', name='Bpk. Joko Susanto', email='joko@gmail.com', role='parent')
        user_ortu1.set_password('ortu123')
        db.session.add(user_ortu1)
        db.session.flush()

        ortu1 = Parent(user_id=user_ortu1.id, first_name='Joko', last_name='Susanto', phone='081333444555', email='joko@gmail.com')
        db.session.add(ortu1)
        db.session.commit()

        # 7. Students
        students_data = [
            ('siswa_riyan', 'Riyan', 'Pratama', '22060511001', 'riyan@student.umg.ac.id', ortu1.id, kelas_5a.id),
            ('siswa_fauzi', 'Ahmad', 'Fauzi', '22060511002', 'fauzi@student.umg.ac.id', None, kelas_5a.id),
            ('siswa_dian', 'Dian', 'Lestari', '22060511003', 'dian@student.umg.ac.id', None, kelas_5a.id),
            ('siswa_bayu', 'Bayu', 'Setiawan', '22060511004', 'bayu@student.umg.ac.id', None, kelas_5b.id),
        ]

        created_students = []
        for uname, fname, lname, nis, email, pid, cid in students_data:
            u = User(username=uname, name=f"{fname} {lname}", email=email, role='student')
            u.set_password('siswa123')
            db.session.add(u)
            db.session.flush()

            st = Student(user_id=u.id, nis=nis, first_name=fname, last_name=lname, parent_id=pid, class_id=cid, status='active')
            db.session.add(st)
            db.session.flush()
            st.enrolled_subjects.append(sub_cc)
            st.enrolled_subjects.append(sub_oop)
            created_students.append(st)
        db.session.commit()

        # 8. Schedules
        sched1 = Schedule(class_id=kelas_5a.id, subject_id=sub_cc.id, teacher_id=guru1.id, day_of_week='Senin', start_time='08:00', end_time='10:30', room='Lab Cloud 3')
        sched2 = Schedule(class_id=kelas_5a.id, subject_id=sub_oop.id, teacher_id=guru1.id, day_of_week='Rabu', start_time='10:30', end_time='12:30', room='Lab Pemrograman 2')
        sched3 = Schedule(class_id=kelas_5b.id, subject_id=sub_db.id, teacher_id=guru2.id, day_of_week='Selasa', start_time='13:00', end_time='15:30', room='R. Teori 204')
        db.session.add_all([sched1, sched2, sched3])
        db.session.commit()

        # 9. Create Historical Lessons and Attendances (For Charts & Grid Matching Gambar 4 & Gambar 5)
        # November 2025 as seen in screenshots
        today = datetime.utcnow().date()
        riyan = created_students[0]
        fauzi = created_students[1]
        dian = created_students[2]

        print("[INFO] Menghasilkan sesi pelajaran dan riwayat absensi...")
        for day in range(1, 28):
            # simulate classes every 2-3 days
            if day in [1, 3, 5, 8, 10, 12, 15, 17, 19, 22, 24, 26]:
                les_date = date(2025, 11, day)
                les = Lesson(
                    schedule_id=sched2.id,
                    class_id=kelas_5a.id,
                    subject_id=sub_oop.id,
                    teacher_id=guru1.id,
                    date=les_date,
                    open_at=datetime.combine(les_date, datetime.min.time()) + timedelta(hours=10, minutes=30),
                    close_at=datetime.combine(les_date, datetime.min.time()) + timedelta(hours=12, minutes=30),
                    status='closed',
                    latitude=-7.156556,
                    longitude=112.655523,
                    radius_m=100.0
                )
                db.session.add(les)
                db.session.flush()

                # Attendance statuses matching typical pattern (mostly present, some late/sick/absent)
                # Riyan presence
                st_status = 'present' if day not in [8, 17, 24] else ('late' if day == 8 else 'absent')
                att_r = Attendance(
                    lesson_id=les.id,
                    student_id=riyan.id,
                    status=st_status,
                    checked_in_at=les.open_at + timedelta(minutes=5 if st_status == 'present' else 25),
                    method='qr' if st_status in ['present', 'late'] else 'manual',
                    latitude=-7.156550,
                    longitude=112.655520
                )
                db.session.add(att_r)

                # Fauzi presence
                f_status = 'present' if day % 4 != 0 else 'sick'
                att_f = Attendance(
                    lesson_id=les.id,
                    student_id=fauzi.id,
                    status=f_status,
                    checked_in_at=les.open_at + timedelta(minutes=7),
                    method='qr' if f_status == 'present' else 'leave'
                )
                db.session.add(att_f)

                # Dian presence
                d_status = 'present' if day % 5 != 0 else 'permit'
                att_d = Attendance(
                    lesson_id=les.id,
                    student_id=dian.id,
                    status=d_status,
                    checked_in_at=les.open_at + timedelta(minutes=10),
                    method='qr' if d_status == 'present' else 'leave'
                )
                db.session.add(att_d)

        # 10. Open an active lesson for today (Cloud Computing)
        active_today_lesson = Lesson(
            schedule_id=sched1.id,
            class_id=kelas_5a.id,
            subject_id=sub_cc.id,
            teacher_id=guru1.id,
            date=today,
            open_at=datetime.utcnow(),
            status='open',
            latitude=-7.156556,
            longitude=112.655523,
            radius_m=100.0,
            late_tolerance_minutes=15
        )
        db.session.add(active_today_lesson)
        db.session.flush()

        # Seed initial attendance for active lesson
        att_active = Attendance(
            lesson_id=active_today_lesson.id,
            student_id=dian.id,
            status='present',
            checked_in_at=datetime.utcnow(),
            method='qr',
            latitude=-7.156550,
            longitude=112.655520,
            note='Presensi via QR Scanner'
        )
        db.session.add(att_active)

        # 11. Initial Notifications
        notif1 = Notification(
            user_id=superadmin.id,
            title="Selamat Datang di Sistem Presensi Cloud",
            body="Sistem presensi terintegrasi Cloud Computing telah siap digunakan."
        )
        notif2 = Notification(
            user_id=user_ortu1.id,
            title="Update Kehadiran Anak",
            body="Ananda Riyan Pratama aktif mengikuti perkuliahan semester 5."
        )
        db.session.add_all([notif1, notif2])

        db.session.commit()
        print("[SUCCESS] Seeding selesai! Akun default telah dibuat:")
        print("   Superadmin : superadmin / admin123")
        print("   Admin      : admin / admin123")
        print("   Guru       : guru_budi / guru123")
        print("   Siswa      : siswa_riyan / siswa123")
        print("   Orang Tua  : ortu_riyan / ortu123")

if __name__ == '__main__':
    run_seed()
