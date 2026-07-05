from .base import *  # noqa

DEBUG = False

# Fail loudly if these are misconfigured in production
if SECRET_KEY == "changeme" or not ALLOWED_HOSTS:  # noqa
    raise RuntimeError("DJANGO_SECRET_KEY and ALLOWED_HOSTS must be set for production.")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
