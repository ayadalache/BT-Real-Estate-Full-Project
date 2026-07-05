from django.core.validators import RegexValidator
from rest_framework import serializers

phone_regex = RegexValidator(
    regex=r"^\+?1?\d{9,15}$",
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
)


def validate_message_content(value: str) -> str:
    """Basic content guard: prevents empty/whitespace-only or absurdly short spam submissions."""
    cleaned = value.strip()
    if len(cleaned) < 5:
        raise serializers.ValidationError("Message must be at least 5 characters long.")
    if len(cleaned) > 2000:
        raise serializers.ValidationError("Message must not exceed 2000 characters.")
    return cleaned
