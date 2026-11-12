import csv

import unfold.decorators
from django import forms
from django.contrib import admin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.widgets import UnfoldAdminTextareaWidget

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import Form, FormKind, FormQuestion, FormSubmission, QuestionType
from ..models.forms import CHOICE_TYPES
from ..services import forms as form_service

TEXT_ANSWERS_PER_PAGE = 50


class OptionsField(forms.CharField):
    """Choice options typed one per line."""

    def prepare_value(self, value):
        return '\n'.join(value) if isinstance(value, (list, tuple)) else value

    def to_python(self, value):
        lines = [line.strip() for line in (super().to_python(value) or '').splitlines()]
        return list(dict.fromkeys(line for line in lines if line))


class FormQuestionAdminForm(forms.ModelForm):
    options = OptionsField(
        label=_('Options'), required=False, widget=UnfoldAdminTextareaWidget(attrs={'rows': 4}),
        help_text=_('Choice questions: one option per line.'),
    )

    class Meta:
        model = FormQuestion
        fields = ['order', 'type', 'text', 'hint', 'required', 'options']

    def clean(self):
        data = super().clean()
        options = data.get('options') or []
        if data.get('type') in CHOICE_TYPES and len(options) < 2:
            self.add_error('options', _('Write at least two options, one per line.'))
        if data.get('type') not in CHOICE_TYPES:
            data['options'] = []
        return data


class FormQuestionFormSet(TabularInline.formset):
    """A poll is one single-choice question; "one question" is exactly one question."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        kept = [form.cleaned_data for form in self.forms
                if form.cleaned_data and not form.cleaned_data.get('DELETE')]
        kind = self.instance.kind
        if not kept:
            raise forms.ValidationError(_('Add at least one question.'))
        if kind in (FormKind.POLL, FormKind.QUESTION) and len(kept) != 1:
            raise forms.ValidationError(_('This kind of form has exactly one question.'))
        if kind == FormKind.POLL and kept[0].get('type') != QuestionType.SINGLE_CHOICE:
            raise forms.ValidationError(_('A poll question must be single choice.'))


class FormQuestionInline(TabularInline):
    model = FormQuestion
    form = FormQuestionAdminForm
    formset = FormQuestionFormSet
    extra = 0
    ordering_field = 'order'
    hide_ordering_field = True
    fields = ['order', 'type', 'text', 'hint', 'required', 'options']


@admin.register(Form, site=superapp_admin_site)
class FormAdmin(SuperAppModelAdmin):
    list_display = ['title', 'slug', 'kind', 'is_active', 'closes_at', 'submission_count', 'created_at']
    list_filter = ['kind', 'is_active']
    search_fields = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['category']
    inlines = [FormQuestionInline]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'kind', 'category', 'intro_markdown')}),
        (_('Answers'), {'fields': (
            ('is_active', 'closes_at'), 'allow_multiple_submissions', 'show_results', 'thank_you_markdown',
        )}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    actions_detail = ['view_results', 'export_csv', 'preview_light', 'preview_dark']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(submission_total=Count('submissions'))

    @admin.display(description=_('Answers'), ordering='submission_total')
    def submission_count(self, obj):
        return obj.submission_total

    def _page_url(self, request, form: Form, theme: str) -> str:
        page = reverse('api_v1_form_page', args=(form.slug,))
        return request.build_absolute_uri(f'{page}?theme={theme}#device_id=admin-preview&platform=web')

    @unfold.decorators.action(description=_('Preview (light)'), attrs={'target': '_blank'})
    def preview_light(self, request, object_id):
        return redirect(self._page_url(request, get_object_or_404(Form, pk=object_id), 'light'))

    @unfold.decorators.action(description=_('Preview (dark)'), attrs={'target': '_blank'})
    def preview_dark(self, request, object_id):
        return redirect(self._page_url(request, get_object_or_404(Form, pk=object_id), 'dark'))

    @unfold.decorators.action(description=_('Results'))
    def view_results(self, request, object_id):
        form = get_object_or_404(Form, pk=object_id)
        page = Paginator(form_service.text_answers(form), TEXT_ANSWERS_PER_PAGE).get_page(request.GET.get('page'))
        return TemplateResponse(request, 'admin/radio_crestin/form/results.html', {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': _('Results: %(title)s') % {'title': form.title},
            'form_obj': form,
            'total': form.submissions.count(),
            'stats': form_service.question_stats(form),
            'text_page': page,
            'change_url': reverse('admin:radio_crestin_form_change', args=(form.pk,)),
            'csv_url': reverse('admin:radio_crestin_form_export_csv', args=(form.pk,)),
        })

    @unfold.decorators.action(description=_('Export answers (CSV)'))
    def export_csv(self, request, object_id):
        form = get_object_or_404(Form, pk=object_id)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="form-{form.slug}.csv"'
        response.write('﻿')  # so spreadsheet apps read the diacritics as UTF-8
        writer = csv.writer(response)
        for row in form_service.csv_rows(form):
            writer.writerow(row)
        return response


@admin.register(FormSubmission, site=superapp_admin_site)
class FormSubmissionAdmin(SuperAppModelAdmin):
    list_display = ['form', 'device_id', 'platform', 'country', 'created_at']
    list_filter = ['form', 'platform']
    search_fields = ['device_id', 'form__slug']
    readonly_fields = ['form', 'device_id', 'platform', 'app_version', 'locale', 'country', 'answers', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
