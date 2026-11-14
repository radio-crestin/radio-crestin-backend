"""Forms: answers checked against the questions, poll results, and what the page script needs."""
import base64
import hmac
from collections import Counter
from typing import Optional

from django.utils.crypto import salted_hmac

from ..models import Form, FormKind, FormSubmission, QuestionType
from ..models.forms import CHOICE_TYPES
from . import announcement_html

MAX_TEXT_LENGTH = 2000
RATING_VALUES = range(1, 6)


class AnswerError(ValueError):
    """One answer that doesn't fit its question; `code` tells the page which message to show."""

    def __init__(self, question_id: int, code: str):
        super().__init__(f'question {question_id}: {code}')
        self.question_id, self.code = question_id, code


def _is_empty(value) -> bool:
    return value is None or value == '' or value == []


def _clean_one(question, value):
    """The stored form of one answer, or AnswerError."""
    def invalid():
        return AnswerError(question.id, 'invalid')

    kind = question.type
    if kind == QuestionType.SINGLE_CHOICE:
        if not isinstance(value, str) or value not in question.options:
            raise invalid()
        return value
    if kind == QuestionType.MULTIPLE_CHOICE:
        if not isinstance(value, list) or not all(isinstance(item, str) and item in question.options for item in value):
            raise invalid()
        return [option for option in question.options if option in value]  # options order, no repeats
    if kind in (QuestionType.SHORT_TEXT, QuestionType.LONG_TEXT):
        if not isinstance(value, str):
            raise invalid()
        text = value.strip()
        if len(text) > MAX_TEXT_LENGTH:
            raise AnswerError(question.id, 'too_long')
        return text
    if kind == QuestionType.RATING:
        if isinstance(value, bool) or not isinstance(value, int) or value not in RATING_VALUES:
            raise invalid()
        return value
    if kind == QuestionType.YES_NO:
        if not isinstance(value, bool):
            raise invalid()
        return value
    raise invalid()


def clean_answers(form: Form, answers) -> dict:
    """{question_id: value} checked against every question (types, options, required).

    Unknown question ids are dropped; raises AnswerError on the first problem.
    """
    if not isinstance(answers, dict):
        raise AnswerError(0, 'invalid')
    cleaned = {}
    for question in form.questions.all():
        value = answers.get(str(question.id))
        if not _is_empty(value):
            value = _clean_one(question, value)
        if _is_empty(value):
            if question.required:
                raise AnswerError(question.id, 'required')
            continue
        cleaned[str(question.id)] = value
    return cleaned


def has_answered(form: Form, device_id: str) -> bool:
    return bool(device_id) and FormSubmission.objects.filter(form=form, device_id=device_id).exists()


def poll_results(form: Form) -> Optional[dict]:
    """Votes per option of a poll that shows its results; None otherwise."""
    if not form.shows_results:
        return None
    question = form.questions.first()
    if question is None:
        return None
    # Counted here: Postgres JSON lookups read a numeric key such as a question id as an array index.
    key = str(question.id)
    votes = Counter(
        answers.get(key) for answers in
        FormSubmission.objects.filter(form=form).values_list('answers', flat=True).iterator()
    )
    counts = [(option, votes.get(option, 0)) for option in question.options]
    total = sum(count for _, count in counts)
    return {
        'question_id': question.id,
        'total': total,
        'options': [
            {'label': option, 'votes': count, 'percent': round(100 * count / total) if total else 0}
            for option, count in counts
        ],
    }


RECEIPT_SALT = 'radio_crestin.forms.receipt'
RECEIPT_LENGTH = 22


def receipt_for(submission: FormSubmission) -> str:
    """Proof that a client made this submission: returned once on submit, never stored, recomputed to check."""
    digest = salted_hmac(RECEIPT_SALT, f'form:{submission.form_id}:{submission.pk}', algorithm='sha256').digest()
    return base64.urlsafe_b64encode(digest).decode()[:RECEIPT_LENGTH]


def previous_poll_choice(form: Form, device_id: str, receipt: str) -> Optional[str]:
    """The option this device voted earlier in a poll that shows results (for a repeat vote's 409).

    Device ids aren't secret, so the choice is only returned with the receipt of that very vote.
    """
    if not form.shows_results or not device_id or not isinstance(receipt, str) or not receipt:
        return None
    question = form.questions.first()
    submission = FormSubmission.objects.filter(form=form, device_id=device_id).order_by('-created_at').first()
    if question is None or submission is None:
        return None
    if not hmac.compare_digest(receipt.encode(), receipt_for(submission).encode()):
        return None
    choice = submission.answers.get(str(question.id))
    return choice if isinstance(choice, str) else None


def page_config(form: Form) -> dict:
    """What the page script renders: the form, its questions and the texts as HTML."""
    return {
        'slug': form.slug,
        'kind': form.kind,
        'title': form.title,
        'intro_html': announcement_html.body_html(form.intro_markdown),
        'thanks_html': announcement_html.body_html(form.thank_you_markdown),
        'open': form.is_open(),
        'multiple': form.allow_multiple_submissions,
        'results': form.shows_results,
        'questions': [
            {'id': question.id, 'type': question.type, 'text': question.text, 'hint': question.hint,
             'required': question.required, 'options': list(question.options or [])}
            for question in form.questions.all()
        ],
    }


def is_poll(form: Form) -> bool:
    return form.kind == FormKind.POLL


# ---------------------------------------------------------------- admin results

TEXT_TYPES = (QuestionType.SHORT_TEXT, QuestionType.LONG_TEXT)


def _bars(counts: list, answered: int) -> list:
    return [
        {'label': label, 'count': count, 'percent': round(100 * count / answered) if answered else 0}
        for label, count in counts
    ]


def _labels(question) -> list:
    """(stored value, label) pairs for the questions that have a fixed set of answers."""
    if question.type in CHOICE_TYPES:
        return [(option, option) for option in question.options]
    if question.type == QuestionType.RATING:
        return [(value, str(value)) for value in RATING_VALUES]
    if question.type == QuestionType.YES_NO:
        return [(True, 'Yes'), (False, 'No')]
    return []


def question_stats(form: Form) -> list:
    """Per question: how many answered, and the counts per answer (choices, rating, yes/no).

    Text answers are listed by text_answers instead, because they need paging.
    """
    questions = list(form.questions.all())
    tallies = {question.id: {} for question in questions}
    answered = dict.fromkeys(tallies, 0)
    for answers in FormSubmission.objects.filter(form=form).values_list('answers', flat=True).iterator():
        for question in questions:
            value = answers.get(str(question.id))
            if value in (None, '', []):
                continue
            answered[question.id] += 1
            for item in value if isinstance(value, list) else [value]:
                tallies[question.id][item] = tallies[question.id].get(item, 0) + 1

    return [
        {
            'question': question,
            'answered': answered[question.id],
            'bars': _bars(
                [(label, tallies[question.id].get(value, 0)) for value, label in _labels(question)],
                answered[question.id],
            ),
            'is_text': question.type in TEXT_TYPES,
        }
        for question in questions
    ]


def text_answers(form: Form) -> list:
    """(created_at, question text, answer) for every text answer, newest first."""
    questions = {str(question.id): question.text for question in form.questions.all() if question.type in TEXT_TYPES}
    rows = []
    for created_at, answers in FormSubmission.objects.filter(form=form).values_list('created_at', 'answers'):
        rows.extend((created_at, text, answers[key]) for key, text in questions.items() if answers.get(key))
    return rows


def csv_rows(form: Form):
    """The header, then one row per submission with one column per question."""
    questions = list(form.questions.all())
    yield ['created_at', 'device_id', 'platform', 'app_version', 'locale', 'country', *[q.text for q in questions]]
    for submission in FormSubmission.objects.filter(form=form).order_by('created_at').iterator():
        yield [
            submission.created_at.isoformat(), submission.device_id, submission.platform, submission.app_version,
            submission.locale, submission.country,
            *[_csv_value(submission.answers.get(str(question.id))) for question in questions],
        ]


def _csv_value(value) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if isinstance(value, list):
        return '; '.join(value)
    return str(value)
