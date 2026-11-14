"""record_listening_events: the HLS listening events streaming pods submit."""

from datetime import timedelta
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone

from ..models import AppUsers, ListeningSessions
from ..services.listener_analytics_service import ListenerAnalyticsService
from ..services.listening_events import record_listening_events
from ..tasks.delete_stale_listening_sessions import delete_stale_listening_sessions
from .helpers import make_station


def event(session_id, slug='station-a', seconds_ago=0, kind='segment_request', size=1000,
          requests=1):
    timestamp = timezone.now() - timedelta(seconds=seconds_ago)
    return SimpleNamespace(
        anonymous_session_id=session_id, station_slug=slug, ip_address='10.0.0.1',
        user_agent='player', referer='https://www.radiocrestin.ro/', event_type=kind,
        bytes_transferred=size, request_duration=0.0, status_code=200, request_count=requests,
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

    def test_a_20_s_batch_dates_the_session_by_its_requests(self):
        # What log_monitor sends for 20 s of listening: the first request,
        # then a summary per type dated by that type's latest request.
        record_listening_events([
            event('s1', seconds_ago=25, kind='playlist_request', size=300),
            event('s1', seconds_ago=13, kind='playlist_request', size=600, requests=2),
            event('s1', seconds_ago=12, size=3000, requests=3),
        ])
        session = ListeningSessions.objects.get()
        now = timezone.now()
        self.assertAlmostEqual((now - session.start_time).total_seconds(), 25, delta=2)
        self.assertAlmostEqual((now - session.last_activity).total_seconds(), 12, delta=2)
        self.assertEqual(session.duration_seconds, 13)
        self.assertEqual(
            (session.total_requests, session.playlist_requests, session.segment_requests,
             session.bytes_transferred),
            (6, 3, 3, 3900),
        )

    def test_a_listener_between_two_20_s_batches_is_still_counted(self):
        # Just before its next batch lands, a listening session's latest
        # request is up to 20 s (the batch) + 6 s (one segment) old.
        record_listening_events([event('s1', seconds_ago=27)])
        delete_stale_listening_sessions.apply()
        self.assertEqual(ListeningSessions.objects.count(), 1)
        self.assertEqual(
            ListenerAnalyticsService.get_batch_listener_counts([self.station.id], minutes=1),
            {self.station.id: 1},
        )

    def test_an_older_event_does_not_move_the_last_activity_back(self):
        record_listening_events([event('s1', seconds_ago=5)])
        latest = ListeningSessions.objects.get().last_activity
        record_listening_events([event('s1', seconds_ago=30)])
        self.assertEqual(ListeningSessions.objects.get().last_activity, latest)

    def test_a_pod_clock_ahead_does_not_start_a_session_in_the_future(self):
        record_listening_events([event('s1', seconds_ago=-30)])
        self.assertLessEqual(ListeningSessions.objects.get().start_time, timezone.now())

    def test_an_event_without_request_count_is_one_request(self):
        lone = event('s1')
        lone.request_count = None
        record_listening_events([lone])
        self.assertEqual(ListeningSessions.objects.get().total_requests, 1)

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
