"""Link checks for announcement buttons: clients open these, so only safe schemes are stored."""
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _

_web_url = URLValidator(schemes=['http', 'https'])
CONTACT_SCHEMES = ('mailto:', 'tel:')


def validate_web_url(value: str):
    """http(s) only: no javascript:, data:, vbscript:, file: or ftp:."""
    try:
        _web_url(value)
    except ValidationError:
        raise ValidationError(_('Enter a link starting with https:// or http://.'), code='invalid_url')


def validate_action_url(value: str):
    """http(s), or mailto:/tel: for contact buttons."""
    lowered = value.strip().lower()
    if lowered.startswith(CONTACT_SCHEMES):
        target = value.split(':', 1)[1]
        if not target.strip() or any(char.isspace() or ord(char) < 32 for char in target):
            raise ValidationError(_('Enter a valid mailto: or tel: link.'), code='invalid_url')
        return
    try:
        validate_web_url(value)
    except ValidationError:
        raise ValidationError(_('Enter a link starting with https://, http://, mailto: or tel:.'), code='invalid_url')


def validate_intent_uri(value: str):
    if not value.strip().lower().startswith('intent:'):
        raise ValidationError(_('An Android intent URI starts with intent:'), code='invalid_intent')
