
import unfold
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule
from django_celery_results.admin import TaskResult, GroupResult, TaskResultAdmin, GroupResultAdmin
from unfold.decorators import action

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from superapp.apps.tasks.management.commands.truncate_all_tasks import drop_all_tasks


# Celery Tasks
@admin.register(TaskResult, site=superapp_admin_site)
class BasePortalTaskResultAdmin(TaskResultAdmin, SuperAppModelAdmin):
    actions_list = [
        "drop_all_tasks_action",
    ]
    list_display = ('task_id', 'periodic_task_name', 'task_name', 'date_created', 'date_done',
                    'status', 'worker')

    date_hierarchy = 'date_created'
    ordering = ('-date_created',)

    @unfold.decorators.action(description=_("Drop all tasks"))
    def drop_all_tasks_action(self, request):
        drop_all_tasks()
        self.message_user(request, f"Dropped all tasks.")
        return redirect(reverse_lazy("admin:django_celery_results_taskresult_changelist"))


@admin.register(GroupResult, site=superapp_admin_site)
class BasePortalResultAdmin(GroupResultAdmin, SuperAppModelAdmin):
    pass


# Celery Beat
@admin.register(PeriodicTask, site=superapp_admin_site)
class PeriodicTaskAdminBase(SuperAppModelAdmin):
    pass


@admin.register(IntervalSchedule, site=superapp_admin_site)
class IntervalScheduleAdminBase(SuperAppModelAdmin):
    pass


@admin.register(CrontabSchedule, site=superapp_admin_site)
class CrontabScheduleAdminBase(SuperAppModelAdmin):
    pass


@admin.register(SolarSchedule, site=superapp_admin_site)
class SolarScheduleAdminBase(SuperAppModelAdmin):
    pass


@admin.register(ClockedSchedule, site=superapp_admin_site)
class ClockedScheduleAdminBase(SuperAppModelAdmin):
    pass
