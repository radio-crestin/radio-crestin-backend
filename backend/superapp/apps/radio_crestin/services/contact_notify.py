"""Emails the team about a new contact message: plain text, Reply-To the sender.

Sent only when CONTACT_NOTIFY_EMAILS (comma separated) is set and Django can send
mail (RESEND_API_KEY configures it). The admin's address is CONTACT_ADMIN_BASE_URL.
"""
import os

from django.core.mail import EmailMessage
from django.urls import reverse

from ..models import ContactMessage

RECIPIENTS_ENV = 'CONTACT_NOTIFY_EMAILS'
ADMIN_BASE_URL_ENV = 'CONTACT_ADMIN_BASE_URL'
DEFAULT_ADMIN_BASE_URL = 'https://api.radiocrestin.ro'


def recipients() -> list[str]:
    return [address.strip() for address in os.environ.get(RECIPIENTS_ENV, '').split(',') if address.strip()]


def admin_url(message: ContactMessage) -> str:
    base = os.environ.get(ADMIN_BASE_URL_ENV, DEFAULT_ADMIN_BASE_URL).rstrip('/')
    return base + reverse('admin:radio_crestin_contactmessage_change', args=(message.pk,))


def _one_line(text: str) -> str:
    """Header-safe: no line breaks."""
    return ' '.join(text.split())


def build_email(message: ContactMessage) -> EmailMessage:
    subject = _one_line(f'[Radio Crestin] {message.get_kind_display()}: {message.subject or message.email}')[:180]
    lines = [
        f'{message.get_kind_display()} from {message.name or "-"} <{message.email}>',
        f'Phone: {message.phone or "-"}',
        f'Source: {message.source or "web"} {message.platform} {message.app_version}'.rstrip(),
        '',
    ]
    if message.message:
        lines += [message.message, '']
    lines += [f'{name}: {value}' for name, value in message.details.items()]
    image_count = message.images.count()
    if image_count:
        lines += ['', f'Images: {image_count}']
    lines += ['', f'Open in the admin: {admin_url(message)}']
    return EmailMessage(subject=subject, body='\n'.join(lines), to=recipients(), reply_to=[message.email])


def send(message: ContactMessage) -> bool:
    if not recipients():
        return False
    build_email(message).send(fail_silently=False)
    return True
