import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

PHONE_ERROR = "Telefon raqami noto'g'ri formatda. Masalan: +998 90 123 45 67"

phone_validator = RegexValidator(r'^\+?998\d{9}$', PHONE_ERROR)


def mask_phone(value):
    digits = re.sub(r'\D', '', value or '')
    if not re.fullmatch(r'998\d{9}', digits):
        return ''
    return f"+{digits[:3]} {digits[3:5]} *** ** {digits[10:]}"


def normalize_phone(value):
    digits = re.sub(r'\D', '', value or '')
    if len(digits) == 9:
        digits = '998' + digits
    if not re.fullmatch(r'998\d{9}', digits):
        raise ValidationError(PHONE_ERROR)
    return '+' + digits
