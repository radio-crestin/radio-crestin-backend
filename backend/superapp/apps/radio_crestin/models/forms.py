from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .announcement_categories import AnnouncementCategory
from .announcement_validators import validate_public_slug

DEFAULT_FORM_ACCENT = '#E91E63'


class FormKind(models.TextChoices):
    QUESTION = 'question', _('One question')
    POLL = 'poll', _('Poll: one choice question, results after voting')
    SURVEY = 'survey', _('Questionnaire: several questions, one per step')


class QuestionType(models.TextChoices):
    SINGLE_CHOICE = 'single_choice', _('Single choice')
    MULTIPLE_CHOICE = 'multiple_choice', _('Multiple choice')
    SHORT_TEXT = 'short_text', _('Short text')
    LONG_TEXT = 'long_text', _('Long text')
    RATING = 'rating', _('Rating 1-5')
    YES_NO = 'yes_no', _('Yes / no')


CHOICE_TYPES = (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE)


class Form(models.Model):
    """A question, poll or questionnaire, served as a small page the apps and the website open in a modal."""

    slug = models.SlugField(_("Slug"), max_length=100, unique=True, validators=[validate_public_slug])
    title = models.CharField(_("Title"), max_length=200)
    intro_markdown = models.TextField(_("Intro"), blank=True, default='', help_text=_("Inline markdown, optional."))
    kind = models.CharField(_("Kind"), max_length=16, choices=FormKind.choices, default=FormKind.SURVEY)
    category = models.ForeignKey(
        AnnouncementCategory, verbose_name=_("Category"), on_delete=models.SET_NULL, null=True, blank=True,
        related_name='forms', help_text=_("Its color is the form's accent."),
    )
    is_active = models.BooleanField(_("Active"), default=True)
    closes_at = models.DateTimeField(_("Closes at"), null=True, blank=True)
    allow_multiple_submissions = models.BooleanField(
        _("Allow several answers per device"), default=False,
    )
    show_results = models.BooleanField(_("Show results after voting"), default=True, help_text=_("Polls only."))
    thank_you_markdown = models.TextField(
        _("Thank-you text"), blank=True, default='', help_text=_("Inline markdown. Empty uses the default text."),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        managed = True
        db_table = 'forms'
        ordering = ('-created_at',)
        verbose_name = _("Form")
        verbose_name_plural = _("Forms")

    def __str__(self):
        return self.title

    @property
    def accent(self) -> str:
        return self.category.color if self.category_id else DEFAULT_FORM_ACCENT

    @property
    def shows_results(self) -> bool:
        return self.kind == FormKind.POLL and self.show_results

    def is_open(self, now=None) -> bool:
        now = now or timezone.now()
        return self.is_active and (self.closes_at is None or self.closes_at > now)


class FormQuestion(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='questions')
    order = models.PositiveIntegerField(_("Order"), default=0, db_index=True)
    type = models.CharField(_("Type"), max_length=32, choices=QuestionType.choices, default=QuestionType.SINGLE_CHOICE)
    text = models.CharField(_("Question"), max_length=300)
    hint = models.CharField(_("Hint"), max_length=200, blank=True, default='')
    required = models.BooleanField(_("Required"), default=True)
    options = models.JSONField(_("Options"), default=list, blank=True, help_text=_("Choice questions: one per line."))

    class Meta:
        managed = True
        db_table = 'form_questions'
        ordering = ('order', 'id')
        verbose_name = _("Form Question")
        verbose_name_plural = _("Form Questions")

    def __str__(self):
        return self.text
