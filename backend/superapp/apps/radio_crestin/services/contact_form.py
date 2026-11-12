"""Validates a contact form submission and stores it.

FIELDS lists every question per kind with its limits; the website shows the
same questions. Errors are short codes per field ({'email': 'invalid_email'})
that the website turns into sentences.
"""
import datetime
import re
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email
from django.db import transaction

from ..models import ContactImageRole, ContactKind, ContactMessage, ContactMessageImage, Stations
from .contact_images import ImageRejected, clean_image

DENOMINATIONS = (
    'pentecostal', 'baptist', 'brethren', 'adventist', 'orthodox', 'lords_army', 'roman_catholic',
    'greek_catholic', 'reformed', 'lutheran', 'evangelical', 'nondenominational', 'other', 'unknown',
)


@dataclass(frozen=True)
class Field:
    name: str
    type: str = 'text'  # text | email | url | choice | date | bool
    required: bool = False
    max_length: int = 200
    min_length: int = 0
    choices: tuple = ()


@dataclass(frozen=True)
class Files:
    name: str
    max_count: int
    role: str = ContactImageRole.IMAGE


COMMON_FIELDS = (
    Field('email', 'email', required=True, max_length=254),
    Field('name', max_length=100),
    Field('phone', max_length=40),
)

CONTEXT_FIELDS = (
    Field('source', max_length=16),
    Field('platform', max_length=32),
    Field('app_version', max_length=32),
    Field('device_id', max_length=128),
)

FIELDS = {
    ContactKind.GENERAL: (
        Field('message', required=True, min_length=10, max_length=5000),
    ),
    ContactKind.STATION: (
        Field('relation', 'choice', required=True, choices=('owner', 'listener')),
        Field('station_name', required=True, max_length=120),
        Field('website', 'url', max_length=500),
        Field('listen_url', 'url', max_length=500),
        Field('description', max_length=1500),
        Field('denomination', 'choice', required=True, choices=DENOMINATIONS),
        Field('denomination_other', max_length=100),
        Field('mission', max_length=1000),
        Field('station_email', 'email', max_length=254),
        Field('facebook_url', 'url', max_length=500),
        Field('consent', 'bool'),
        Field('note', max_length=2000),
    ),
    ContactKind.ANNOUNCEMENT: (
        Field('about', 'choice', required=True, choices=('station', 'general')),
        Field('station_slug', max_length=100),
        Field('title', required=True, max_length=80),
        Field('summary', required=True, max_length=280),
        Field('details', max_length=5000),
        Field('link', 'url', max_length=500),
        Field('starts_on', 'date'),
        Field('ends_on', 'date'),
    ),
}

FILES = {
    ContactKind.GENERAL: Files('images', 3),
    ContactKind.STATION: Files('logo', 1, ContactImageRole.LOGO),
    ContactKind.ANNOUNCEMENT: Files('images', 3),
}

# Fields stored in their own columns rather than in `details`.
COLUMN_FIELDS = {'email', 'name', 'phone', 'message'}

_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_url_validator = URLValidator(schemes=['http', 'https'])


@dataclass
class Result:
    data: dict = field(default_factory=dict)
    images: list = field(default_factory=list)  # (role, CleanImage)
    errors: dict = field(default_factory=dict)


def clean_text(value) -> str:
    """Trimmed text without control characters (Postgres rejects NUL)."""
    text = _CONTROL_CHARS.sub('', str(value or '')).replace('\r\n', '\n').replace('\r', '\n')
    return text.strip()


def _with_scheme(url: str) -> str:
    """People type "radio.ro" or "www.radio.ro"; the stored link needs a scheme."""
    return url if re.match(r'^[a-z][a-z0-9+.-]*:', url, re.I) else f'https://{url}'


def _clean_field(spec: Field, raw):
    """(value, error_code)."""
    value = clean_text(raw)
    if spec.type == 'bool':
        return value.lower() in ('true', '1', 'on', 'yes'), None
    if not value:
        return '', 'required' if spec.required else None
    if len(value) > spec.max_length:
        return value, 'too_long'
    if len(value) < spec.min_length:
        return value, 'too_short'
    if spec.type == 'email':
        try:
            validate_email(value)
        except ValidationError:
            return value, 'invalid_email'
        return value.lower(), None
    if spec.type == 'url':
        url = _with_scheme(value)
        try:
            _url_validator(url)
        except ValidationError:
            return value, 'invalid_url'
        return (url, None) if len(url) <= spec.max_length else (url, 'too_long')
    if spec.type == 'choice':
        return (value, None) if value in spec.choices else (value, 'invalid_choice')
    if spec.type == 'date':
        try:
            return datetime.date.fromisoformat(value).isoformat(), None
        except ValueError:
            return value, 'invalid_date'
    return value, None


def _check_rules(kind: str, data: dict, errors: dict):
    """Rules that span fields."""
    def require(name, code='required'):
        if not data.get(name) and name not in errors:
            errors[name] = code

    if kind == ContactKind.STATION:
        require('name')
        if not data.get('website') and not data.get('listen_url') and not errors.keys() & {'website', 'listen_url'}:
            errors['listen_url'] = 'need_website_or_listen_url'
        if data.get('denomination') == 'other':
            require('denomination_other')
        if data.get('relation') == 'owner' and not data.get('consent'):
            errors['consent'] = 'consent_required'
    elif kind == ContactKind.ANNOUNCEMENT:
        require('name')
        if data.get('about') == 'station' and 'station_slug' not in errors:
            slug = data.get('station_slug')
            if not slug:
                errors['station_slug'] = 'required'
            elif not Stations.objects.filter(slug=slug, disabled=False).exists():
                errors['station_slug'] = 'unknown_station'
        starts, ends = data.get('starts_on'), data.get('ends_on')
        if starts and ends and 'starts_on' not in errors and 'ends_on' not in errors and ends < starts:
            errors['ends_on'] = 'end_before_start'


def _clean_files(spec: Files, files, result: Result):
    uploads = files.getlist(spec.name) if files else []
    if len(uploads) > spec.max_count:
        result.errors[spec.name] = 'too_many_files'
        return
    for upload in uploads:
        try:
            result.images.append((spec.role, clean_image(upload)))
        except ImageRejected as rejected:
            result.errors[spec.name] = rejected.code
            return


def validate(kind: str, post, files) -> Result:
    result = Result()
    if kind not in FIELDS:
        result.errors['kind'] = 'invalid_choice'
        return result
    for spec in COMMON_FIELDS + CONTEXT_FIELDS + FIELDS[kind]:
        value, error = _clean_field(spec, post.get(spec.name, ''))
        if error:
            result.errors[spec.name] = error
        else:
            result.data[spec.name] = value
    _check_rules(kind, result.data, result.errors)
    # Images cost CPU: only decode them for an otherwise valid form.
    if not result.errors:
        _clean_files(FILES[kind], files, result)
    return result


def _subject(kind: str, data: dict) -> str:
    text = {
        ContactKind.STATION: data.get('station_name'),
        ContactKind.ANNOUNCEMENT: data.get('title'),
    }.get(kind) or data.get('message', '')
    first_line = text.split('\n', 1)[0]
    return first_line[:120] + ('…' if len(first_line) > 120 else '')


def create(kind: str, result: Result, *, ip=None, country='', user_agent='') -> ContactMessage:
    data = result.data
    context = {spec.name: data.get(spec.name, '') for spec in CONTEXT_FIELDS}
    details = {
        name: value for name, value in data.items()
        if name not in COLUMN_FIELDS and name not in context and value not in ('', None)
    }
    with transaction.atomic():
        message = ContactMessage.objects.create(
            kind=kind, subject=_subject(kind, data),
            name=data.get('name', ''), email=data['email'], phone=data.get('phone', ''),
            message=data.get('message', ''), details=details,
            ip=ip, country=country or '', user_agent=clean_text(user_agent)[:300], **context,
        )
        for role, image in result.images:
            ContactMessageImage.objects.create(
                message=message, role=role, image=image.content, width=image.width, height=image.height,
            )
    return message
