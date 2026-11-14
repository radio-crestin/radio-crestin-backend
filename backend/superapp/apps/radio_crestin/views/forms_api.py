"""Forms opened from announcements: the page (WebView / iframe), submitting answers, poll results.

Everything lives under /api/: the public ingress routes only /api, /graphql and /health.
"""
import hashlib
import json

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.core import is_ratelimited

from superapp.apps.posthog_error_tracking.utils import track_event
from ..models import Form, FormSubmission
from ..models.announcement_categories import text_color_on
from ..services import forms as form_service
from ..utils.client_request import client_country, client_ip, safe_ip

PAGE_CACHE_CONTROL = 'public, max-age=60, stale-while-revalidate=86400'
RESULTS_CACHE_SECONDS = 30
SUBMIT_RATE_PER_IP = '20/m'
SUBMIT_RATE_PER_DEVICE = '5/m'
# The website embeds the page in an iframe; the apps load it top-level in a WebView.
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src https: data:; "
    "connect-src 'self'; form-action 'self'; "
    "frame-ancestors https://www.radiocrestin.ro https://radiocrestin.ro http://localhost:3005"
)

# Romanian copy produced with `codex exec` (copy4-ro.json and the form strings next to it), verbatim.
PAGE_STRINGS = {
    'next': 'Înainte',
    'back': 'Înapoi',
    'submit': 'Trimite',
    'vote': 'Votează',
    'close': 'Închide',
    'step': 'Întrebarea {n} din {total}',
    'required': 'Alege un răspuns pentru a continua',
    'thanks_title': 'Îți mulțumim!',
    'thanks_body': 'Răspunsul tău ne ajută să îmbunătățim Radio Creștin.',
    'votes': '{n} voturi',  # CLDR "few"; the page picks the form with Intl.PluralRules('ro')
    'votes_one': '{n} vot',
    'votes_many': '{n} de voturi',
    'your_vote': 'Votul tău',
    'results_title': 'Rezultatele de până acum',
    'yes': 'Da',
    'no': 'Nu',
    'text_required': 'Scrie un răspuns pentru a continua',
    'text_placeholder': 'Scrie răspunsul aici…',
    'text_too_long': 'Răspunsul tău este prea lung',
    'closed_title': 'Acest formular este închis',
    'closed_body': 'Nu mai acceptă răspunsuri. Îți mulțumim pentru interes!',
    'already_title': 'Ai răspuns deja',
    'already_body': 'Mulțumim! Am primit răspunsul tău mai devreme.',
    'error': 'A apărut o eroare. Încearcă din nou.',
    'not_found': 'Acest formular nu este disponibil.',
    'rating_low': 'Deloc',
    'rating_high': 'Foarte mult',
}


def _json(data, status=200) -> JsonResponse:
    response = JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False})
    response['Cache-Control'] = 'private, no-store'
    response['Access-Control-Allow-Origin'] = '*'
    return response


def _form(slug: str):
    return Form.objects.select_related('category').prefetch_related('questions').filter(slug=slug).first()


@method_decorator(xframe_options_exempt, name='dispatch')
class FormPageView(View):
    """GET /api/v1/forms/<slug>/page/?theme=dark|light

    The same page for every device, so Cloudflare may cache it; the device context
    (#device_id=…&platform=…&app_version=…&locale=…) stays in the fragment.
    """

    def get(self, request, slug: str):
        theme = 'dark' if request.GET.get('theme') == 'dark' else 'light'
        form = _form(slug)
        if form is None:
            response = render(request, 'radio_crestin/forms/not_found.html',
                              {'theme': theme, 'text': PAGE_STRINGS['not_found']}, status=404)
        else:
            config = {
                **form_service.page_config(form),
                't': PAGE_STRINGS,
                'submit_url': reverse('api_v1_form_submit', args=(form.slug,)),
                'results_url': reverse('api_v1_form_results', args=(form.slug,)),
            }
            response = render(request, 'radio_crestin/forms/page.html', {
                'theme': theme, 'title': form.title, 'config': config,
                'accent': form.accent, 'accent_text': text_color_on(form.accent),
            })
        response['Cache-Control'] = PAGE_CACHE_CONTROL
        response['Content-Security-Policy'] = CONTENT_SECURITY_POLICY
        return response


def _over_limit(request, group: str, value: str, rate: str) -> bool:
    return is_ratelimited(request, group=group, key=lambda _group, _request: value, rate=rate, increment=True)


def _first_submit_in_flight(form: Form, device_id: str) -> bool:
    """A short lock so two quick taps from one device can't both pass the "already answered" check."""
    device_hash = hashlib.sha256(device_id.encode('utf-8')).hexdigest()[:32]
    return cache.add(f'forms:submitting:{form.pk}:{device_hash}', 1, 10)


def _text(value, max_length: int) -> str:
    return str(value).strip()[:max_length] if value is not None else ''


@method_decorator(csrf_exempt, name='dispatch')
class FormSubmitView(View):
    """POST /api/v1/forms/<slug>/submit/ with {device_id, platform, app_version, locale, answers, receipt?}.

    CSRF-exempt: the page runs in an iframe of another site, where cookies can't be relied on.
    """

    def post(self, request, slug: str):
        ip = safe_ip(client_ip(request))
        if _over_limit(request, 'form-submit-ip', ip or '', SUBMIT_RATE_PER_IP):
            return _json({'status': 'rate_limited'}, status=429)
        try:
            payload = json.loads((request.body or b'{}').decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return _json({'status': 'invalid', 'code': 'json'}, status=400)
        if not isinstance(payload, dict):
            return _json({'status': 'invalid', 'code': 'json'}, status=400)

        device_id = _text(payload.get('device_id'), 512)
        if not device_id:
            return _json({'status': 'invalid', 'code': 'device_id'}, status=400)
        if _over_limit(request, 'form-submit-device', device_id, SUBMIT_RATE_PER_DEVICE):
            return _json({'status': 'rate_limited'}, status=429)

        form = _form(slug)
        if form is None:
            return _json({'status': 'not_found'}, status=404)
        if not form.is_open():
            return _json({'status': 'closed'}, status=410)
        try:
            answers = form_service.clean_answers(form, payload.get('answers'))
        except form_service.AnswerError as error:
            return _json({'status': 'invalid', 'question_id': error.question_id, 'code': error.code}, status=400)

        if not form.allow_multiple_submissions and (
                form_service.has_answered(form, device_id) or not _first_submit_in_flight(form, device_id)):
            # A poll's earlier choice comes back so the page marks "Votul tău" on the vote that counts.
            return _json(_compact({
                'status': 'already_submitted',
                'results': form_service.poll_results(form),
                'your_answer': form_service.previous_poll_choice(form, device_id, payload.get('receipt')),
            }), status=409)

        platform = _text(payload.get('platform'), 32)
        submission = FormSubmission.objects.create(
            form=form, device_id=device_id, platform=platform,
            app_version=_text(payload.get('app_version'), 64), locale=_text(payload.get('locale'), 64),
            country=client_country(request) or '', answers=answers,
        )
        cache.delete(_results_cache_key(form.slug))
        track_event(device_id, 'form_submitted', {
            'form_slug': form.slug, 'form_kind': form.kind, 'platform': platform,
        })
        return _json(_compact({
            'status': 'ok',
            'results': form_service.poll_results(form),
            # Kept by the page; shown back on a repeat vote to see the device's own choice again.
            'receipt': form_service.receipt_for(submission),
        }))

    def options(self, request, *args, **kwargs):
        response = _json({})
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        response['Access-Control-Max-Age'] = '86400'
        return response


def _compact(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def _results_cache_key(slug: str) -> str:
    return f'forms:results:{slug}'


class FormResultsView(View):
    """GET /api/v1/forms/<slug>/results/ — votes of a poll that shows its results, cached 30 s."""

    def get(self, request, slug: str):
        results = cache.get(_results_cache_key(slug))
        if results is None:
            form = _form(slug)
            results = (form_service.poll_results(form) if form else None) or {}
            cache.set(_results_cache_key(slug), results, RESULTS_CACHE_SECONDS)
        if not results:
            return _json({'status': 'not_found'}, status=404)
        response = JsonResponse(results, json_dumps_params={'ensure_ascii': False})
        response['Cache-Control'] = f'public, max-age={RESULTS_CACHE_SECONDS}'
        response['Access-Control-Allow-Origin'] = '*'
        return response
