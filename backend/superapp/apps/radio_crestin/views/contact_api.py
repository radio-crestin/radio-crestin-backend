import logging

from django.core.exceptions import RequestDataTooBig, SuspiciousOperation, TooManyFieldsSent
from django.http import JsonResponse
from django.http.multipartparser import MultiPartParserError
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.core import get_usage

from ..services import contact_form, contact_spam
from ..tasks.notify_contact_message import notify_contact_message
from ..utils.client_request import client_country, client_ip, safe_ip

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 32 * 1024 * 1024

# Every request counts here, so a client can't hammer the parser with invalid forms.
ATTEMPT_RATES = (('contact-attempts-ip', 'ip', '30/10m'),)
# Only stored (or dropped as spam) messages count here, so fixing a typo costs nothing.
# Per IP and email: a person sends a few messages; a flood from many IPs is capped overall.
SENT_RATES = (
    ('contact-ip-burst', 'ip', '5/10m'),
    ('contact-ip-day', 'ip', '20/d'),
    ('contact-email-day', 'email', '10/d'),
    ('contact-all-hour', 'all', '300/h'),
)


def _json(data, status):
    response = JsonResponse(data, status=status)
    response['Cache-Control'] = 'private, no-store'
    response['Access-Control-Allow-Origin'] = '*'
    return response


def _over(request, rates, keys: dict, increment: bool) -> bool:
    """True when a rate is used up; with `increment`, this request counts first."""
    over = False
    for group, key, rate in rates:
        value = keys.get(key)
        if not value:
            continue
        usage = get_usage(request, group=group, key=lambda *_, v=value: v, rate=rate, increment=increment)
        if usage and (usage['count'] > usage['limit'] if increment else usage['count'] >= usage['limit']):
            over = True
    return over


@method_decorator(csrf_exempt, name='dispatch')
class ContactMessageView(View):
    """POST /api/v1/contact/ - a contact form from the website, as multipart/form-data.

    201 when stored (or silently dropped as spam), 400 with {"errors": {field: code}},
    413 above MAX_BODY_BYTES, 429 when rate limited.
    """

    def post(self, request):
        try:
            length = int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return _json({'status': 'invalid', 'errors': {'form': 'required'}}, 400)
        if length > MAX_BODY_BYTES:
            return _json({'status': 'too_large'}, 413)
        try:
            post, files = request.POST, request.FILES
        except RequestDataTooBig:
            return _json({'status': 'too_large'}, 413)
        except (TooManyFieldsSent, SuspiciousOperation, MultiPartParserError):
            return _json({'status': 'invalid', 'errors': {'form': 'invalid_choice'}}, 400)

        ip = safe_ip(client_ip(request))
        email = contact_form.clean_text(post.get('email', '')).lower()[:254]
        # Requests without a usable IP share one bucket instead of skipping the limit.
        keys = {'ip': ip or 'unknown', 'email': email, 'all': 'all'}
        if _over(request, ATTEMPT_RATES, keys, increment=True) or _over(request, SENT_RATES, keys, increment=False):
            return _json({'status': 'rate_limited'}, 429)

        if contact_spam.looks_automated(post):
            _over(request, SENT_RATES, keys, increment=True)
            # Answer like a success so bots learn nothing.
            logger.info('Contact form dropped as automated from %s', ip)
            return _json({'status': 'ok'}, 201)
        if not contact_spam.passes_turnstile(post.get('turnstile_token', ''), ip):
            return _json({'status': 'invalid', 'errors': {'turnstile_token': 'captcha_failed'}}, 400)

        kind = post.get('kind', '')
        result = contact_form.validate(kind, post, files)
        if result.errors:
            return _json({'status': 'invalid', 'errors': result.errors}, 400)

        _over(request, SENT_RATES, keys, increment=True)
        message = contact_form.create(
            kind, result, ip=ip, country=client_country(request) or '',
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        try:
            notify_contact_message.delay(message.pk)
        except Exception as error:  # The message is stored; the email is a convenience.
            logger.error('Could not queue the contact notification for %s: %s', message.pk, error)
        return _json({'status': 'ok'}, 201)

    def options(self, request, *args, **kwargs):
        response = _json({}, 200)
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        response['Access-Control-Max-Age'] = '86400'
        return response
