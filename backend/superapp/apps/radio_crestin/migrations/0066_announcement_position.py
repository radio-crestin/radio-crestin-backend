import django.core.validators
from django.db import migrations, models

import superapp.apps.radio_crestin.models.announcement_settings


def priority_to_position(apps, schema_editor):
    """Keeps today's order: highest priority first, then newest start, then newest row."""
    Announcement = apps.get_model('radio_crestin', 'Announcement')
    ordered = Announcement.objects.order_by('-priority', '-starts_at', '-id').values_list('id', flat=True)
    for position, announcement_id in enumerate(ordered):
        Announcement.objects.filter(id=announcement_id).update(position=position)


def position_to_priority(apps, schema_editor):
    Announcement = apps.get_model('radio_crestin', 'Announcement')
    ordered = list(Announcement.objects.order_by('position', 'id').values_list('id', flat=True))
    for index, announcement_id in enumerate(ordered):
        Announcement.objects.filter(id=announcement_id).update(priority=len(ordered) - index)


class Migration(migrations.Migration):
    # The data copy and the schema changes can't share one Postgres transaction
    # ("pending trigger events"), so each operation runs on its own.
    atomic = False

    dependencies = [
        ('radio_crestin', '0065_embed_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='position',
            field=models.PositiveIntegerField(
                blank=True, db_index=True, default=0,
                help_text='Order in the card, lowest first: drag the rows in the Announcements list. New ones go last.',
                verbose_name='Position',
            ),
            preserve_default=False,
        ),
        migrations.RunPython(priority_to_position, position_to_priority),
        migrations.RemoveField(
            model_name='announcement',
            name='priority',
        ),
        migrations.AlterModelOptions(
            name='announcement',
            options={'managed': True, 'ordering': ('position', 'id'), 'verbose_name': 'Announcement',
                     'verbose_name_plural': 'Announcements'},
        ),
        migrations.AddField(
            model_name='announcementsettings',
            name='autoplay_seconds',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='0 keeps it off: people page through the announcements themselves. Otherwise 3 to 60: the '
                          'card moves to the next announcement after this many seconds, until someone pages or '
                          'closes one, and stops at the last.',
                validators=[superapp.apps.radio_crestin.models.announcement_settings.validate_autoplay_seconds],
                verbose_name='Move on by itself after (seconds)',
            ),
        ),
        migrations.AlterField(
            model_name='announcementsettings',
            name='rotation_mode',
            field=models.CharField(
                choices=[('fixed', 'Fixed: server order'), ('rotate', 'Rotate: next one first on each load'),
                         ('random', 'Random first, then server order')],
                default='rotate',
                help_text='Which announcement each visit starts with. Fixed: always the first in the list. Rotate: '
                          'the next one on every visit, so each gets its turn. Random: any of them. The order itself '
                          'is the drag-and-drop order of the Announcements list.',
                max_length=16, verbose_name='Rotation mode',
            ),
        ),
    ]
