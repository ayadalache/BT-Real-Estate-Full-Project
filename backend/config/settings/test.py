from .development import *  # noqa
import tempfile

# Throttling is a production concern; disabling it for the test run avoids
# tests interfering with each other via a shared cache within the same
# rate-limit window, while still being covered by dedicated throttle tests
# that explicitly enable rates via override_settings.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {scope: None for scope in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]},  # noqa: F405
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast hashing for tests only

MEDIA_ROOT = tempfile.mkdtemp(prefix="btrealestate_test_media_")
