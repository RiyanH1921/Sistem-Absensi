import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'cloud-presensi-secret-key-super-secure-2026')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'cloud-presensi-jwt-key-2026')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # Database
    db_url = os.getenv('DATABASE_URL', 'sqlite:///presensi.db')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Presensi & QR Settings
    QR_ROTATION_SECONDS = int(os.getenv('QR_ROTATION_SECONDS', 30))
    DEFAULT_MAX_RADIUS_METERS = float(os.getenv('DEFAULT_MAX_RADIUS_METERS', 100.0))
    DEFAULT_LATITUDE = float(os.getenv('DEFAULT_LATITUDE', -7.156556))
    DEFAULT_LONGITUDE = float(os.getenv('DEFAULT_LONGITUDE', 112.655523))
    DEFAULT_LATE_TOLERANCE_MINUTES = int(os.getenv('DEFAULT_LATE_TOLERANCE_MINUTES', 15))
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB limit
