"""log_monitor: a batch of HLS requests becomes a few events per listening
session, each dated by a real request, so the batch length shifts no time
Django records."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import log_monitor as lm  # noqa: E402


def request(session, second, kind="segment_request", size=1000):
    return {
        "anonymous_session_id": session,
        "station_slug": "station-a",
        "timestamp": f"2027-01-15T08:00:{second:02d}+00:00",
        "event_type": kind,
        "bytes_transferred": size,
    }


def summary(event):
    return (event["anonymous_session_id"], event["timestamp"][17:19],
            event["event_type"], event["request_count"], event["bytes_transferred"])


class ConsolidateTests(unittest.TestCase):
    def test_a_lone_request_is_sent_as_it_is(self):
        events = lm.consolidate([request("s1", 4, "playlist_request", 300)])
        self.assertEqual([summary(e) for e in events],
                         [("s1", "04", "playlist_request", 1, 300)])

    def test_first_request_then_one_summary_per_type(self):
        queue = [
            request("s1", 1, "playlist_request", 300),
            request("s1", 2),
            request("s1", 7, "playlist_request", 300),
            request("s1", 8),
            request("s1", 13, "playlist_request", 300),
            request("s1", 14),
        ]
        events = lm.consolidate(queue)
        self.assertEqual([summary(e) for e in events], [
            ("s1", "01", "playlist_request", 1, 300),
            ("s1", "13", "playlist_request", 2, 600),
            ("s1", "14", "segment_request", 3, 3000),
        ])
        # nothing lost
        self.assertEqual(sum(e["request_count"] for e in events), len(queue))

    def test_sessions_are_kept_apart_and_sent_in_time_order(self):
        queue = [request("s2", 9), request("s1", 3), request("s1", 15), request("s2", 1)]
        events = lm.consolidate(queue)
        self.assertEqual([(e["anonymous_session_id"], e["timestamp"][17:19]) for e in events],
                         [("s2", "01"), ("s1", "03"), ("s2", "09"), ("s1", "15")])

    def test_the_queued_requests_are_not_modified(self):
        queue = [request("s1", 1), request("s1", 2)]
        lm.consolidate(queue)
        self.assertEqual([e["bytes_transferred"] for e in queue], [1000, 1000])
        self.assertNotIn("request_count", queue[0])


if __name__ == "__main__":
    unittest.main()
