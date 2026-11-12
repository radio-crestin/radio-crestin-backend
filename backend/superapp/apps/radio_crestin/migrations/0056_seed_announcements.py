from django.db import migrations
from django.utils import timezone

# Romanian names produced with `codex exec` (see the announcements spec, "Copy").
CATEGORIES = [
    ('community', 'Comunitate', '#0F6E63'),
    ('event', 'Eveniment', '#7C3AED'),
    ('new', 'Noutate', '#2563EB'),
    ('important', 'Important', '#C2410C'),
    ('prayer', 'Rugăciune', '#9D174D'),
]

# Romanian copy produced with `codex exec` for the announcements design.
WHATSAPP_SLUG = 'whatsapp-versetul-zilei'
WHATSAPP_TITLE = 'Versetul zilei pe WhatsApp'
WHATSAPP_BODY = 'Primește un verset biblic **în fiecare zi, la 7:30**, direct pe telefonul tău.'
WHATSAPP_BUTTON = 'Primește versetul zilei'
WHATSAPP_LINK = 'https://chat.whatsapp.com/I78qjRg1RaI5UKTvEwZdNm'


def seed(apps, schema_editor):
    AnnouncementCategory = apps.get_model('radio_crestin', 'AnnouncementCategory')
    Announcement = apps.get_model('radio_crestin', 'Announcement')
    AnnouncementSettings = apps.get_model('radio_crestin', 'AnnouncementSettings')

    categories = {}
    for ordering, (slug, name, color) in enumerate(CATEGORIES):
        categories[slug], _ = AnnouncementCategory.objects.get_or_create(
            slug=slug, defaults={'name': name, 'color': color, 'ordering': ordering},
        )

    if not AnnouncementSettings.objects.exists():
        AnnouncementSettings.objects.create(rotation_mode='rotate', autoplay_seconds=8, max_per_load=5)

    Announcement.objects.get_or_create(
        slug=WHATSAPP_SLUG,
        defaults={
            'is_active': True,
            'priority': 10,
            'category': categories['community'],
            'icon_name': 'whatsapp',
            'title': WHATSAPP_TITLE,
            'body_markdown': WHATSAPP_BODY,
            'action_type': 'external',
            'action_label': WHATSAPP_BUTTON,
            'action_url': WHATSAPP_LINK,
            'web_link_target': 'new_tab',
            'dismissible': True,
            'starts_at': timezone.now(),
            'platforms': [],
        },
    )


def unseed(apps, schema_editor):
    apps.get_model('radio_crestin', 'Announcement').objects.filter(slug=WHATSAPP_SLUG).delete()
    apps.get_model('radio_crestin', 'AnnouncementCategory').objects.filter(
        slug__in=[slug for slug, _, _ in CATEGORIES],
    ).delete()
    apps.get_model('radio_crestin', 'AnnouncementSettings').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0055_announcements'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
