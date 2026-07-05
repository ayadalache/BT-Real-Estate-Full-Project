import os

from django.core.exceptions import ValidationError
from PIL import Image

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_image_upload(uploaded_file) -> None:
    """
    Defense-in-depth validation for any uploaded image across the platform:
    1. Extension allow-list.
    2. Declared content-type allow-list.
    3. Size cap (prevents storage exhaustion / DoS via huge uploads).
    4. Actual image verification via Pillow — opens and decodes the file and
       confirms the real format matches what was claimed. This is what
       actually stops a disguised malicious file (e.g. a script renamed to
       .jpg with a forged content-type) — extension/MIME checks alone are
       trivially spoofed and are only the first line of defense.
    """
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}.")

    content_type = getattr(uploaded_file, "content_type", None)
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError("Unsupported file type. Only JPEG, PNG, and WEBP images are allowed.")

    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(f"Image file too large. Maximum size is {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB.")

    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as img:
            img.verify()
            detected_format = (img.format or "").upper()
    except Exception as exc:
        raise ValidationError("File is not a valid image or is corrupted.") from exc
    finally:
        uploaded_file.seek(0)

    valid_formats = {"JPEG", "PNG", "WEBP"}
    if detected_format not in valid_formats:
        raise ValidationError("File content does not match an allowed image format.")
