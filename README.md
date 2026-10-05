# dAttendance - Cloud Computing Presensi System

Sistem Presensi Kampus & Sekolah Berbasis Cloud dengan Dynamic QR Code (HMAC-SHA256), Geofencing Radius GPS (Haversine), Role-Based Access Control (RBAC), Dashboard Statistik Interaktif, dan Rekapitulasi Grid Kehadiran Bulanan (1–31).

Disusun dan diimplementasikan secara komprehensif mengacu pada dokumen **SRS & Blueprint Sistem Presensi (Versi 1.0)**.

---

## 🌟 Fitur Utama Sesuai Blueprint

1. **Autentikasi & RBAC (5 Aktor):**
   - **Super Admin**: Akses penuh ke sistem, audit log, dan master data.
   - **Admin Akademik**: Manajemen kelas, mata kuliah, jadwal, siswa, guru.
   - **Guru / Dosen**: Membuka sesi presensi QR dinamis di proyektor, koreksi manual, review permohonan izin/sakit, dan penutupan sesi.
   - **Siswa / Mahasiswa**: Pemindai kamera QR web (`html5-qrcode`) + deteksi GPS, cek riwayat absensi bulanan, ajukan izin/sakit.
   - **Orang Tua**: Menerima notifikasi otomatis saat anak Alpa / Sakit / Izin.

2. **Mesin Presensi Anti-Titip Absen:**
   - **Dynamic QR Code**: Token QR di-generate menggunakan HMAC-SHA256 dan berganti otomatis tiap 30 detik sehingga foto QR yang dikirim ke teman tidak dapat digunakan.
   - **Geofencing GPS**: Menghitung jarak siswa ke titik lokasi kelas menggunakan rumus **Haversine** (default radius 100 meter).
   - **Deteksi Perangkat Ganda**: Mencegah satu perangkat HP dipakai absen oleh banyak akun sekaligus.
   - **Mekanisme Otomatis**: Hadir $\le$ batas toleransi; lewat batas = Terlambat; dan saat guru menutup sesi, siswa yang belum presensi otomatis tercatat **Alpa**.

3. **Dashboard & Visualisasi Data (Mengacu Gambar 4):**
   - 4 Kartu Metrik: `USERS`, `SISWA`, `ABSENSI KEHADIRAN (H/I/S/A)`, dan `BELUM ABSENSI`.
   - Grafik garis tren absensi harian (Chart.js) + Doughnut Chart komposisi kehadiran + Tabel Rekapitulasi.
   - Fitur Filter Kelas, Bulan, Tahun, serta tombol **Download Chart** dan **Export Excel (.xlsx)**.

4. **Grid Kehadiran Bulanan 1–31 (Mengacu Gambar 5):**
   - Matriks tanggal 1 s.d. 31 dengan badge status (*Present, Late, Sick, Permit, Absent*).
   - Metrik ringkasan: `Total Classes` dan `My Presence`.

5. **Modul Perizinan & Surat Keterangan:**
   - Pengajuan izin sakit/keperluan mendesak disertai upload bukti (foto/surat dokter).
   - Approval oleh Guru yang langsung mengupdate status absensi di rentang tanggal tersebut.

6. **Audit Trail & Keamanan:**
   - Password terenkripsi dengan **Bcrypt**.
   - Setiap aktivitas presensi, login, dan koreksi manual tercatat di tabel `audit_logs`.

---

## 🔑 Akun Demo Pengujian Instan

Anda dapat langsung masuk atau menggunakan tombol pintasan 1-klik di halaman login:

| Peran | Username | Password | Keterangan |
|---|---|---|---|
| **Super Admin** | `superadmin` | `admin123` | Administrator Sistem & Audit Log |
| **Admin Akademik** | `admin` | `admin123` | Kelola Kelas, Mapel & Jadwal |
| **Guru / Dosen** | `guru_budi` | `guru123` | Budi Santoso, M.Kom. (Dosen Pengampu) |
| **Siswa / Mahasiswa** | `siswa_riyan` | `siswa123` | Riyan Pratama (NIS: 22060511001) |
| **Orang Tua** | `ortu_riyan` | `ortu123` | Bpk. Joko Susanto (Wali Riyan) |

---

## 🚀 Cara Menjalankan Proyek Secara Lokal

### 1. Prasyarat
- Python 3.11+ (Telah teruji pada Python 3.13)
- Pip & Virtualenv (opsional)

### 2. Instalasi Dependensi
```bash
pip install -r requirements.txt
```

### 3. Inisialisasi Database & Data Awal (Seeding)
```bash
python seed.py
```

### 4. Menjalankan Server Web
```bash
python run.py
```
Akses di browser Anda: **`http://localhost:5000`**

---

## 📁 Struktur Direktori Proyek

```
Sistem Presensi/
├── app/
│   ├── models/           # User, Student, Teacher, Lesson, Attendance, LeaveRequest, AuditLog
│   ├── routes/           # Auth, Master Data, Lesson, Attendance, Report, Web Views
│   ├── services/         # AttendanceService (QR validation, GPS, auto-alpa), ReportService
│   ├── static/           # CSS modern, uploads bukti surat izin
│   ├── templates/        # Template Jinja2 responsive (Dashboard, Layar QR, Scanner, Grid)
│   ├── utils/            # Geo Haversine, Dynamic QR HMAC Engine, RBAC Decorators
│   ├── config.py         # Konfigurasi aplikasi & .env
│   └── extensions.py     # SQLAlchemy, Bcrypt, JWT, CORS
├── .env.example          # Template konfigurasi environment
├── requirements.txt      # Daftar dependensi Python
├── run.py                # Server entry point
├── seed.py               # Database seeder
└── README.md
```
