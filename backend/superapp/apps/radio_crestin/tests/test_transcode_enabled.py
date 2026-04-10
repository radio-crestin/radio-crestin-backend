from django.test import TestCase

from ..models import Stations


class TranscodeEnabledModelTests(TestCase):
    """Tests for the transcode_enabled field and generate_hls_stream backward compat property."""

    @classmethod
    def setUpTestData(cls):
        cls.station_enabled = Stations.objects.create(
            slug="station-enabled",
            title="Enabled Station",
            order=1,
            station_order=1.0,
            website="https://example.com",
            stream_url="https://stream.example.com/live",
            transcode_enabled=True,
        )
        cls.station_disabled = Stations.objects.create(
            slug="station-disabled",
            title="Disabled Station",
            order=2,
            station_order=2.0,
            website="https://example2.com",
            stream_url="https://stream.example2.com/live",
            transcode_enabled=False,
        )

    def test_transcode_enabled_default_is_true(self):
        station = Stations.objects.create(
            slug="station-default",
            title="Default Station",
            order=3,
            station_order=3.0,
            website="https://example3.com",
            stream_url="https://stream.example3.com/live",
        )
        self.assertTrue(station.transcode_enabled)

    def test_transcode_enabled_true(self):
        self.assertTrue(self.station_enabled.transcode_enabled)

    def test_transcode_enabled_false(self):
        self.assertFalse(self.station_disabled.transcode_enabled)

    def test_generate_hls_stream_property_reads_transcode_enabled(self):
        """Backward-compat property should return the same value as transcode_enabled."""
        self.assertTrue(self.station_enabled.generate_hls_stream)
        self.assertFalse(self.station_disabled.generate_hls_stream)

    def test_generate_hls_stream_property_setter(self):
        """Setting generate_hls_stream should update transcode_enabled."""
        station = Stations.objects.create(
            slug="station-setter-test",
            title="Setter Test",
            order=4,
            station_order=4.0,
            website="https://example4.com",
            stream_url="https://stream.example4.com/live",
            transcode_enabled=True,
        )
        station.generate_hls_stream = False
        self.assertFalse(station.transcode_enabled)
        self.assertFalse(station.generate_hls_stream)

    def test_transcode_enabled_persists_to_database(self):
        """Verify the field is properly saved and retrieved from DB."""
        station = Stations.objects.create(
            slug="station-persist-test",
            title="Persist Test",
            order=5,
            station_order=5.0,
            website="https://example5.com",
            stream_url="https://stream.example5.com/live",
            transcode_enabled=False,
        )
        # Refresh from DB
        station.refresh_from_db()
        self.assertFalse(station.transcode_enabled)
        self.assertFalse(station.generate_hls_stream)

    def test_filter_by_transcode_enabled(self):
        """Verify we can filter stations by transcode_enabled."""
        enabled = Stations.objects.filter(transcode_enabled=True)
        disabled = Stations.objects.filter(transcode_enabled=False)
        self.assertIn(self.station_enabled, enabled)
        self.assertIn(self.station_disabled, disabled)
        self.assertNotIn(self.station_disabled, enabled)
        self.assertNotIn(self.station_enabled, disabled)
