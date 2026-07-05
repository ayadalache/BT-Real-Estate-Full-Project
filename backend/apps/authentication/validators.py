import re

from django.core.exceptions import ValidationError


class ComplexPasswordValidator:
    """
    Enforces a strong password policy beyond Django's built-in validators:
    at least one uppercase, one lowercase, one digit, and one special
    character. Reduces susceptibility to dictionary/brute-force attacks.
    """

    def validate(self, password, user=None):
        errors = []
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]", password):
            errors.append("Password must contain at least one special character.")
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            "Your password must contain at least one uppercase letter, one "
            "lowercase letter, one digit, and one special character."
        )


def validate_username(username: str) -> None:
    """
    Restrict usernames to a safe character set. Prevents usernames that look
    like injection payloads, path fragments, or that collide with reserved
    routes (e.g. 'admin', 'api').
    """
    if not re.match(r"^[a-zA-Z0-9_.-]{3,30}$", username):
        raise ValidationError(
            "Username must be 3-30 characters and contain only letters, "
            "numbers, dots, hyphens, and underscores."
        )
    reserved = {"admin", "api", "root", "system", "null", "undefined", "staff", "support"}
    if username.lower() in reserved:
        raise ValidationError("This username is reserved and cannot be used.")
