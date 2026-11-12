from datetime import timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

BEFORE = [('radio_crestin', '0058_announcement_event_one_dismissal')]
AFTER = [('radio_crestin', '0059_announcement_status_and_filters')]
LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


@override_settings(CACHES=LOCMEM_CACHE)
class StatusMigrationTests(TransactionTestCase):
    """0059: the list became public, so announcements limited to devices or IPs must not go public."""

    serialized_rollback = True  # brings the seeded rows back for the tests that run after

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def check_restricted_announcements_become_preview(self):
        apps = self.migrate(BEFORE)
        Announcement = apps.get_model('radio_crestin', 'Announcement')
        AppUsers = apps.get_model('radio_crestin', 'AppUsers')
        Announcement.objects.filter(slug='whatsapp-versetul-zilei').delete()

        def make(slug, **fields):
            return Announcement.objects.create(slug=slug, title=slug, **fields)

        make('public', is_active=True)
        make('off', is_active=False)
        make('by-ip', is_active=True, ip_ranges=['10.0.0.0/8'])
        make('by-pasted-id', is_active=True, extra_device_ids=['web-1'])
        make('by-picked-device', is_active=True).target_devices.add(AppUsers.objects.create(
            anonymous_id='phone-1', email='phone-1@example.com'))
        make('restricted-but-off', is_active=False, ip_ranges=['10.0.0.0/8'])

        apps = self.migrate(AFTER)
        statuses = dict(apps.get_model('radio_crestin', 'Announcement').objects.values_list('slug', 'status'))
        self.assertEqual(statuses, {
            'public': 'active', 'off': 'draft', 'by-ip': 'preview', 'by-pasted-id': 'preview',
            'by-picked-device': 'preview', 'restricted-but-off': 'draft',
        })

    def check_priorities_become_positions_in_the_same_order(self):
        apps = self.migrate([('radio_crestin', '0065_embed_details')])
        Announcement = apps.get_model('radio_crestin', 'Announcement')
        Announcement.objects.update(priority=-1)  # anything already there sorts after these
        now = timezone.now()
        for slug, priority, days_ago in (('low-old', 1, 9), ('high', 9, 5), ('low-new', 1, 1), ('mid', 5, 3),
                                         ('low-new-later-row', 1, 1)):
            Announcement.objects.create(slug=slug, title=slug, priority=priority, status='active',
                                        starts_at=(now - timedelta(days=days_ago)).replace(microsecond=0))

        apps = self.migrate([('radio_crestin', '0066_announcement_position')])
        ordered = apps.get_model('radio_crestin', 'Announcement').objects.order_by('position')
        self.assertEqual(list(ordered.values_list('slug', 'position')[:5]), [
            ('high', 0), ('mid', 1), ('low-new-later-row', 2), ('low-new', 3), ('low-old', 4),
        ])

    def test_data_migrations(self):
        # One test: a second test in this class would trip guardian's post-migrate user on the reload.
        self.check_restricted_announcements_become_preview()
        self.check_priorities_become_positions_in_the_same_order()
