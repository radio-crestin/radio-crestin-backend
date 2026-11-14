"""record_listening_events: the HLS listening events streaming pods submit."""

from datetime import timedelta
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone

from ..models import AppUsers, ListeningSessions
from ..services.listening_events import record_listening_events
from .helpers import make_station


def event(session_id, slug='station-a', seconds_ago=0, kind='segment_request', size=1000):
    timestamp = timezone.now() - timedelta(seconds=seconds_ago)
    return SimpleNamespace(
        anonymous_session_id=session_id, station_slug=slug, ip_address='10.0.0.1',
        user_agent='player', referer='https://www.radiocrestin.ro/', event_type=kind,
        bytes_transferred=size, request_duration=0.0, status_code=200, request_count=1,
        timestamp=timestamp.isoformat(),
    )


class RecordListeningEventsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('station-a')
        make_station('station-b')

    def test_first_event_opens_a_session_for_a_new_listener(self):
        self.assertEqual(record_listening_events([event('s1', kind='playlist_request', size=500)]), 1)
        session = ListeningSessions.objects.get()
        self.assertEqual(session.user, AppUsers.objects.get(anonymous_id='s1'))
        self.assertEqual(session.station, self.station)
        self.assertEqual(
            (session.total_requests, session.playlist_requests, session.segment_requests,
             session.bytes_transferred, session.ip_address, session.user_agent),
            (1, 1, 0, 500, '10.0.0.1', 'player'),
        )

    def test_later_batches_continue_the_session(self):
        record_listening_events([event('s1', seconds_ago=20)])
        record_listening_events([event('s1', seconds_ago=10), event('s1')])
        session = ListeningSessions.objects.get()
        self.assertEqual((session.total_requests, session.segment_requests, session.bytes_transferred),
                         (3, 3, 3000))
        self.assertEqual(AppUsers.objects.filter(anonymous_id='s1').count(), 1)

    def test_listener_back_after_the_timeout_gets_a_new_session(self):
        record_listening_events([event('s1')])
        ListeningSessions.objects.update(last_activity=timezone.now() - timedelta(minutes=6))
        record_listening_events([event('s1')])
        self.assertEqual(ListeningSessions.objects.count(), 2)

    def test_one_listener_on_two_stations_has_two_sessions(self):
        record_listening_events([event('s1'), event('s1', slug='station-b')])
        self.assertEqual(ListeningSessions.objects.filter(user__anonymous_id='s1').count(), 2)

    def test_unknown_station_and_unreadable_timestamp_are_skipped(self):
        bad_time = event('s2')
        bad_time.timestamp = 'yesterday'
        recorded = record_listening_events([event('s1', slug='no-such-station'), bad_time, event('s3')])
        self.assertEqual(recorded, 1)
        self.assertEqual(list(ListeningSessions.objects.values_list('anonymous_session_id', flat=True)), ['s3'])

    def test_a_batch_costs_the_same_queries_whatever_its_size(self):
        listeners = [f's{n}' for n in range(7)]
        record_listening_events([event(sid) for sid in listeners])
        # stations, users, sessions, the update, and the transaction
        with self.assertNumQueries(6):
            record_listening_events([event(sid) for sid in listeners])
        self.assertEqual(set(ListeningSessions.objects.values_list('total_requests', flat=True)), {2})
