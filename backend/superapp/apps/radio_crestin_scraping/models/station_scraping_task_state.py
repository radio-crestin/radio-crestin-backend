from django.db import models
from django.utils.translation import gettext_lazy as _

from superapp.apps.radio_crestin.models import Stations


class StationScrapingTaskState(models.Model):
    """Track the state of scraping tasks to prevent race conditions and data override"""
    
    station = models.OneToOneField(
        Stations,
        on_delete=models.CASCADE,
        related_name='scraping_task_state',
        verbose_name=_('Station')
    )
    
    # Current task information
    current_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Current Task ID')
    )
    
    current_task_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Current Task Started At')
    )
    
    # Track which fetchers have been processed
    processed_fetcher_states = models.JSONField(
        default=dict,
        help_text=_('JSON tracking state of each fetcher: {fetcher_id: {status, priority, data, timestamp}}'),
        verbose_name=_('Processed Fetcher States')
    )
    
    # Last successful update
    last_successful_update_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Successful Update At')
    )
    
    last_successful_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Last Successful Task ID')
    )
    
    # Creation and update timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Station Scraping Task State')
        verbose_name_plural = _('Station Scraping Task States')
        db_table = 'station_scraping_task_states'
        
    def __str__(self):
        return f"Task State for {self.station.title}"