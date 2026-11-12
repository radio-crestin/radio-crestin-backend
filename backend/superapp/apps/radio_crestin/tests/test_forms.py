import json
import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ..models import Announcement, AnnouncementCategory, Form, FormQuestion, FormSubmission
from ..services import forms as form_service
from ..views import forms_api

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


def make_poll(slug='morning-poll', **fields):
    form = Form.objects.create(slug=slug, title='Ce post asculți dimineața?', kind='poll', **fields)
    FormQuestion.objects.create(form=form, order=0, type='single_choice', text='Ce post?',
                                options=['Radio Elim', 'Radio Vocea Evangheliei', 'Alt post'])
    return form


def make_survey(slug='app-survey', **fields):
    form = Form.objects.create(slug=slug, title='Ajută-ne', kind='survey', **fields)
    questions = {
        'how_often': FormQuestion.objects.create(form=form, order=0, type='single_choice', text='Cât de des?',
                                                 options=['Zilnic', 'Rar']),
        'what': FormQuestion.objects.create(form=form, order=1, type='multiple_choice', text='Ce asculți?',
                                            options=['Muzică', 'Predici', 'Lecturi']),
        'rating': FormQuestion.objects.create(form=form, order=2, type='rating', text='Cât de mulțumit ești?'),
        'idea': FormQuestion.objects.create(form=form, order=3, type='long_text', text='Ce să adăugăm?',
                                            required=False),
        'again': FormQuestion.objects.create(form=form, order=4, type='yes_no', text='Recomanzi?', required=False),
    }
    return form, questions


class AnswerValidationTests(TestCase):
    def setUp(self):
        self.form, self.q = make_survey()

    def answers(self, **values):
        base = {'how_often': 'Zilnic', 'what': ['Predici'], 'rating': 4}
        base.update(values)
        return {str(self.q[name].id): value for name, value in base.items() if value is not None}

    def error(self, **values):
        try:
            form_service.clean_answers(self.form, self.answers(**values))
        except form_service.AnswerError as error:
            return error.question_id, error.code
        return None

    def test_valid_answers_are_normalized(self):
        cleaned = form_service.clean_answers(self.form, {
            **self.answers(what=['Lecturi', 'Muzică', 'Lecturi'], idea='  Mai multe predici  ', again=False),
            '999999': 'unknown question is dropped',
        })
        self.assertEqual(cleaned[str(self.q['what'].id)], ['Muzică', 'Lecturi'])
        self.assertEqual(cleaned[str(self.q['idea'].id)], 'Mai multe predici')
        self.assertIs(cleaned[str(self.q['again'].id)], False)
        self.assertNotIn('999999', cleaned)

    def test_required_questions(self):
        self.assertEqual(self.error(how_often=None), (self.q['how_often'].id, 'required'))
        self.assertEqual(self.error(what=[]), (self.q['what'].id, 'required'))
        self.assertIsNone(self.error(idea=''))

    def test_types_and_options(self):
        self.assertEqual(self.error(how_often='Uneori'), (self.q['how_often'].id, 'invalid'))
        self.assertEqual(self.error(what='Predici'), (self.q['what'].id, 'invalid'))
        self.assertEqual(self.error(what=['Altceva']), (self.q['what'].id, 'invalid'))
        for rating in (0, 6, '4', True, 4.5):
            self.assertEqual(self.error(rating=rating), (self.q['rating'].id, 'invalid'), rating)
        self.assertEqual(self.error(again='yes'), (self.q['again'].id, 'invalid'))
        self.assertEqual(self.error(idea=['x']), (self.q['idea'].id, 'invalid'))

    def test_text_limit(self):
        self.assertIsNone(self.error(idea='a' * 2000))
        self.assertEqual(self.error(idea='a' * 2001), (self.q['idea'].id, 'too_long'))

    def test_answers_must_be_an_object(self):
        with self.assertRaises(form_service.AnswerError):
            form_service.clean_answers(self.form, ['Zilnic'])


@override_settings(CACHES=LOCMEM_CACHE)
class FormPageTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_cache_and_framing_headers(self):
        make_poll()
        response = self.client.get('/api/v1/forms/morning-poll/page/', {'theme': 'dark'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'public, max-age=60, stale-while-revalidate=86400')
        self.assertNotIn('X-Frame-Options', response)
        csp = response['Content-Security-Policy']
        self.assertIn("frame-ancestors https://www.radiocrestin.ro https://radiocrestin.ro http://localhost:3005", csp)
        for directive in ("default-src 'none'", "connect-src 'self'", "form-action 'self'", 'img-src https: data:'):
            self.assertIn(directive, csp)

    def test_theme_accent_and_config(self):
        category = AnnouncementCategory.objects.get(slug='prayer')
        make_poll(category=category)
        html = self.client.get('/api/v1/forms/morning-poll/page/', {'theme': 'dark'}).content.decode()
        self.assertIn('data-t="dark"', html)
        self.assertIn('--acc:#9D174D', html)
        config = json.loads(re.search(r'<script id="cfg" type="application/json">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(config['kind'], 'poll')
        self.assertEqual(config['submit_url'], '/api/v1/forms/morning-poll/submit/')
        self.assertEqual(config['questions'][0]['options'][0], 'Radio Elim')
        self.assertEqual(config['t']['vote'], 'Votează')
        self.assertEqual((config['t']['votes_one'], config['t']['votes'], config['t']['votes_many']),
                         ('{n} vot', '{n} voturi', '{n} de voturi'))
        self.assertTrue(config['open'])

    def test_light_is_the_default_and_unknown_themes_fall_back(self):
        make_poll()
        for theme in (None, 'neon'):
            html = self.client.get('/api/v1/forms/morning-poll/page/', {'theme': theme} if theme else {}).content
            self.assertIn(b'data-t="light"', html)

    def test_same_page_for_every_device(self):
        make_poll()
        first = self.client.get('/api/v1/forms/morning-poll/page/?theme=light', HTTP_CF_IPCOUNTRY='RO').content
        second = self.client.get('/api/v1/forms/morning-poll/page/?theme=light', HTTP_CF_IPCOUNTRY='DE').content
        self.assertEqual(first, second)

    def test_closed_and_missing_forms(self):
        make_poll(closes_at=timezone.now() - timedelta(minutes=1))
        html = self.client.get('/api/v1/forms/morning-poll/page/').content.decode()
        self.assertIn('"open": false', html)
        missing = self.client.get('/api/v1/forms/nope/page/')
        self.assertEqual(missing.status_code, 404)
        self.assertNotIn('X-Frame-Options', missing)
        self.assertContains(missing, 'Acest formular nu este disponibil.', status_code=404)

    def test_inline_script_and_style_stay_small(self):
        make_poll()
        html = self.client.get('/api/v1/forms/morning-poll/page/').content.decode()
        script = re.search(r'<script>\n(.*?)</script>', html, re.S).group(1)
        style = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
        self.assertLess(len(script.encode()), 6 * 1024)
        self.assertLess(len(style.encode()), 6 * 1024)
        self.assertNotRegex(html, r'(src|href)="https?://')


@override_settings(CACHES=LOCMEM_CACHE)
class FormSubmitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.poll = make_poll()
        self.question = self.poll.questions.get()

    def submit(self, slug='morning-poll', device_id='phone-1', answers=None, **headers):
        body = {'device_id': device_id, 'platform': 'android', 'app_version': '1.7.0', 'locale': 'ro-RO',
                'answers': answers if answers is not None else {str(self.question.id): 'Radio Elim'}}
        return self.client.post(f'/api/v1/forms/{slug}/submit/', json.dumps(body), content_type='text/plain',
                                **headers)

    def test_vote_is_stored_and_results_returned(self):
        with patch.object(forms_api, 'track_event') as track_event:
            response = self.submit(HTTP_CF_IPCOUNTRY='MD')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'ok')
        self.assertEqual(body['results']['total'], 1)
        self.assertEqual(body['results']['options'][0], {'label': 'Radio Elim', 'votes': 1, 'percent': 100})
        submission = FormSubmission.objects.get()
        self.assertEqual((submission.device_id, submission.platform, submission.country), ('phone-1', 'android', 'MD'))
        track_event.assert_called_once_with('phone-1', 'form_submitted', {
            'form_slug': 'morning-poll', 'form_kind': 'poll', 'platform': 'android'})

    def repeat(self, **body):
        response = self.client.post('/api/v1/forms/morning-poll/submit/', json.dumps({
            'device_id': 'phone-1', 'answers': {str(self.question.id): 'Alt post'}, **body,
        }), content_type='text/plain')
        self.assertEqual(response.status_code, 409)
        return response.json()

    def test_one_answer_per_device(self):
        self.submit()
        repeat = self.repeat()
        self.assertEqual(repeat['status'], 'already_submitted')
        self.assertEqual(repeat['results']['total'], 1)
        self.assertEqual(FormSubmission.objects.count(), 1)

    @patch.object(forms_api, 'SUBMIT_RATE_PER_DEVICE', '100/m')
    def test_a_repeat_shows_the_stored_choice_only_with_the_receipt(self):
        receipt = self.submit().json()['receipt']
        self.assertEqual(len(receipt), 22)
        self.assertNotIn('your_answer', self.repeat())
        self.assertNotIn('your_answer', self.repeat(receipt='x' * 22))
        self.assertNotIn('your_answer', self.repeat(receipt=receipt[:-1] + ('A' if receipt[-1] != 'A' else 'B')))
        self.assertNotIn('your_answer', self.repeat(receipt=['not', 'a', 'string']))
        # The vote that counts, not the new tap.
        self.assertEqual(self.repeat(receipt=receipt)['your_answer'], 'Radio Elim')

    def test_a_receipt_only_proves_its_own_submission(self):
        receipt = self.submit(device_id='phone-1').json()['receipt']
        self.submit(device_id='phone-2')
        other = self.client.post('/api/v1/forms/morning-poll/submit/', json.dumps({
            'device_id': 'phone-2', 'answers': {str(self.question.id): 'Alt post'}, 'receipt': receipt,
        }), content_type='text/plain').json()
        self.assertNotIn('your_answer', other)

    def test_receipts_are_not_stored(self):
        self.submit()
        self.assertNotIn('receipt', json.dumps(FormSubmission.objects.values().get(), default=str))

    def test_a_repeat_on_a_poll_without_results_reveals_nothing(self):
        Form.objects.filter(pk=self.poll.pk).update(show_results=False)
        receipt = self.submit().json()['receipt']
        self.assertEqual(self.repeat(receipt=receipt), {'status': 'already_submitted'})

    def test_text_answers_never_come_back(self):
        survey, questions = make_survey()
        answers = {str(questions['how_often'].id): 'Zilnic', str(questions['what'].id): ['Muzică'],
                   str(questions['rating'].id): 5, str(questions['idea'].id): 'Un text privat'}
        first = self.submit(slug=survey.slug, answers=answers)
        repeat = self.submit(slug=survey.slug, answers=answers)
        self.assertEqual(repeat.status_code, 409)
        for response in (first, repeat):
            self.assertNotIn('Un text privat', response.content.decode())

    def test_several_answers_when_allowed(self):
        Form.objects.filter(pk=self.poll.pk).update(allow_multiple_submissions=True)
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 2)

    def test_a_rejected_answer_does_not_block_the_retry(self):
        self.assertEqual(self.submit(answers={str(self.question.id): 'Nope'}).status_code, 400)
        self.assertEqual(self.submit().status_code, 200)

    def test_invalid_requests(self):
        bad = self.submit(answers={str(self.question.id): 'Radio Necunoscut'})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.json(), {'status': 'invalid', 'question_id': self.question.id, 'code': 'invalid'})
        self.assertEqual(self.submit(answers={}).json()['code'], 'required')
        self.assertEqual(self.submit(device_id='').json()['code'], 'device_id')
        self.assertEqual(self.client.post('/api/v1/forms/morning-poll/submit/', 'x', content_type='text/plain').status_code, 400)
        self.assertEqual(self.submit(slug='nope').status_code, 404)
        self.assertEqual(FormSubmission.objects.count(), 0)

    def test_closed_or_inactive_forms(self):
        Form.objects.filter(pk=self.poll.pk).update(closes_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.submit().status_code, 410)
        Form.objects.filter(pk=self.poll.pk).update(closes_at=None, is_active=False)
        self.assertEqual(self.submit().status_code, 410)

    def test_no_results_when_hidden_or_not_a_poll(self):
        Form.objects.filter(pk=self.poll.pk).update(show_results=False)
        self.assertNotIn('results', self.submit().json())
        survey, questions = make_survey()
        response = self.submit(slug=survey.slug, answers={
            str(questions['how_often'].id): 'Zilnic', str(questions['what'].id): ['Muzică'],
            str(questions['rating'].id): 5,
        })
        self.assertEqual(set(response.json()), {'status', 'receipt'})

    @patch.object(forms_api, 'SUBMIT_RATE_PER_DEVICE', '2/m')
    def test_rate_limit_per_device(self):
        Form.objects.filter(pk=self.poll.pk).update(allow_multiple_submissions=True)
        with patch('time.time', return_value=1_800_000_000):
            for index in range(2):
                self.assertEqual(self.submit(HTTP_CF_CONNECTING_IP=f'10.0.0.{index}').status_code, 200)
            limited = self.submit(HTTP_CF_CONNECTING_IP='10.0.0.9')
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(FormSubmission.objects.count(), 2)

    @patch.object(forms_api, 'SUBMIT_RATE_PER_IP', '3/m')
    def test_rate_limit_per_ip(self):
        with patch('time.time', return_value=1_800_000_000):
            for index in range(3):
                self.submit(device_id=f'phone-{index}', HTTP_CF_CONNECTING_IP='86.120.1.2')
            self.assertEqual(self.submit(device_id='phone-9', HTTP_CF_CONNECTING_IP='86.120.1.2').status_code, 429)
            self.assertEqual(self.submit(device_id='phone-9', HTTP_CF_CONNECTING_IP='86.120.9.9').status_code, 200)

    def test_production_limits(self):
        self.assertEqual((forms_api.SUBMIT_RATE_PER_IP, forms_api.SUBMIT_RATE_PER_DEVICE), ('20/m', '5/m'))


@override_settings(CACHES=LOCMEM_CACHE)
class FormResultsTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_poll_results_are_cached_briefly(self):
        poll = make_poll()
        question = poll.questions.get()
        for device, choice in (('a', 'Radio Elim'), ('b', 'Radio Elim'), ('c', 'Alt post')):
            FormSubmission.objects.create(form=poll, device_id=device, answers={str(question.id): choice})
        response = self.client.get('/api/v1/forms/morning-poll/results/')
        self.assertEqual(response['Cache-Control'], 'public, max-age=30')
        self.assertEqual(response.json()['total'], 3)
        self.assertEqual([o['percent'] for o in response.json()['options']], [67, 0, 33])

    def test_only_polls_that_show_results(self):
        make_poll(slug='hidden', show_results=False)
        make_survey()
        for slug in ('hidden', 'app-survey', 'nope'):
            self.assertEqual(self.client.get(f'/api/v1/forms/{slug}/results/').status_code, 404, slug)


@override_settings(CACHES=LOCMEM_CACHE)
class FormActionTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_announcements_can_open_a_form(self):
        make_poll()
        Announcement.objects.create(
            slug='vote', title='Votează', status='active', starts_at=timezone.now() - timedelta(hours=1),
            action_type='form', action_label='Votează', form=Form.objects.get(slug='morning-poll'),
        )
        item = next(i for i in self.client.get('/api/v1/announcements/').json()['announcements'] if i['slug'] == 'vote')
        self.assertEqual(item['button']['action'], {'type': 'form', 'form_slug': 'morning-poll'})


@override_settings(CACHES=LOCMEM_CACHE)
class FormAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(email='admin@example.com', password='x'))
        self.form, self.q = make_survey()
        FormSubmission.objects.create(form=self.form, device_id='a', answers={
            str(self.q['how_often'].id): 'Zilnic', str(self.q['what'].id): ['Muzică', 'Predici'],
            str(self.q['rating'].id): 5, str(self.q['idea'].id): 'Mai multe colinde', str(self.q['again'].id): True,
        })

    def test_results_page(self):
        response = self.client.get(reverse('admin:radio_crestin_form_view_results', args=(self.form.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mai multe colinde')
        self.assertContains(response, '1 · 100%')

    def test_csv_export(self):
        response = self.client.get(reverse('admin:radio_crestin_form_export_csv', args=(self.form.pk,)))
        lines = response.content.decode('utf-8-sig').splitlines()
        self.assertIn('Cât de des?', lines[0])
        self.assertIn('Muzică; Predici', lines[1])
        self.assertIn('yes', lines[1])

    def test_preview_opens_the_page(self):
        response = self.client.get(reverse('admin:radio_crestin_form_preview_dark', args=(self.form.pk,)))
        self.assertIn('/api/v1/forms/app-survey/page/?theme=dark#device_id=admin-preview', response['Location'])

    def test_list_and_change_pages_render(self):
        self.assertEqual(self.client.get(reverse('admin:radio_crestin_form_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:radio_crestin_form_change', args=(self.form.pk,))).status_code, 200)

    def test_a_poll_needs_one_single_choice_question(self):
        data = {
            'title': 'Poll', 'slug': 'new-poll', 'kind': 'poll', 'show_results': 'on', 'is_active': 'on',
            'questions-TOTAL_FORMS': '2', 'questions-INITIAL_FORMS': '0',
            'questions-MIN_NUM_FORMS': '0', 'questions-MAX_NUM_FORMS': '1000',
            'questions-0-order': '0', 'questions-0-type': 'single_choice', 'questions-0-text': 'A?',
            'questions-0-options': 'Da\nNu', 'questions-0-required': 'on',
            'questions-1-order': '1', 'questions-1-type': 'short_text', 'questions-1-text': 'B?',
        }
        response = self.client.post(reverse('admin:radio_crestin_form_add'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'exactly one question')
        self.assertFalse(Form.objects.filter(slug='new-poll').exists())

        data['questions-TOTAL_FORMS'] = '1'
        response = self.client.post(reverse('admin:radio_crestin_form_add'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Form.objects.get(slug='new-poll').questions.get().options, ['Da', 'Nu'])
