"""Cheap bot filters for the contact form: a honeypot, a minimum fill time and optional Turnstile.

Turnstile is checked only when CONTACT_TURNSTILE_SECRET is set; the website shows
the widget only when it is built with PUBLIC_TURNSTILE_SITE_KEY.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

HONEYPOT_FIELD = 'confirm_url'
MIN_FILL_MS = 3000
TURNSTILE_SECRET_ENV = 'CONTACT_TURNSTILE_SECRET'
TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def looks_automated(post) -> bool:
    if post.get(HONEYPOT_FIELD, '').strip():
        return True
    try:
        return int(post.get('elapsed_ms', '')) < MIN_FILL_MS
    except ValueError:
        return True


def passes_turnstile(token: str, ip) -> bool:
    secret = os.environ.get(TURNSTILE_SECRET_ENV, '')
    if not secret:
        return True
    if not token or len(token) > 2048:
        return False
    try:
        response = requests.post(
            TURNSTILE_VERIFY_URL, data={'secret': secret, 'response': token, 'remoteip': ip or ''}, timeout=10,
        )
        return bool(response.json().get('success'))
    except (requests.RequestException, ValueError) as error:
        # Cloudflare down: let people through rather than lose their message.
        logger.warning('Turnstile verification failed open: %s', error)
        return True
