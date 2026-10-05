import hmac
import hashlib
import time
import io
import base64
import qrcode
from flask import current_app

def generate_qr_payload(lesson_id: int, secret: str, rotation_seconds: int = 30) -> str:
    """
    Generate dynamic QR payload: {lesson_id}:{period}:{signature}
    """
    current_time = int(time.time())
    period = current_time // rotation_seconds
    raw_data = f"{lesson_id}:{period}"
    signature = hmac.new(secret.encode('utf-8'), raw_data.encode('utf-8'), hashlib.sha256).hexdigest()[:16]
    return f"{lesson_id}:{period}:{signature}"

def verify_qr_payload(qr_string: str, lesson_id: int, secret: str, rotation_seconds: int = 30) -> bool:
    """
    Verify dynamic QR payload with ±2 time period tolerance (up to 60-90s) to handle network delay & clock drift.
    """
    try:
        parts = qr_string.strip().split(':')
        if len(parts) != 3:
            return False
        
        parsed_lesson_id = int(parts[0])
        parsed_period = int(parts[1])
        parsed_sig = parts[2]

        if parsed_lesson_id != lesson_id:
            return False

        current_period = int(time.time()) // rotation_seconds

        # Check tolerance: allow current, 2 previous periods, and 1 next period
        valid_periods = [current_period, current_period - 1, current_period - 2, current_period + 1]
        if parsed_period not in valid_periods:
            return False

        # Verify signature
        expected_raw = f"{lesson_id}:{parsed_period}"
        expected_sig = hmac.new(secret.encode('utf-8'), expected_raw.encode('utf-8'), hashlib.sha256).hexdigest()[:16]

        return hmac.compare_digest(parsed_sig, expected_sig)
    except Exception:
        return False

def generate_qr_base64_image(payload: str) -> str:
    """
    Render QR code to Base64 PNG image Data URI with high contrast and standard 4-module quiet zone.
    """
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,  # ISO/IEC standard 4 modules quiet zone for easy camera recognition
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#000000", back_color="#ffffff")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"
