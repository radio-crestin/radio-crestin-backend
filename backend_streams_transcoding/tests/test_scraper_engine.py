"""
Unit tests for scraper_engine GraphQL response parsing.

Reproduces PostHog issue 019ed33d / 019edb54: JSONDecodeError
"Expecting value: line 1 column 1 (char 0)" raised by `_graphql_request` when
Django (behind nginx) returns a non-JSON body — e.g. an HTML 502/503 page
during a restart/deploy. The parser must degrade to {} instead of raising.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import scraper_engine  # noqa: E402

parse = scraper_engine._parse_graphql_response


class TestParseGraphqlResponse:
    def test_valid_json_returns_data_payload(self):
        raw = b'{"data": {"streaming_station_configs": [{"station_id": 1}]}}'
        assert parse(200, raw) == {"streaming_station_configs": [{"station_id": 1}]}

    def test_html_503_body_returns_empty_dict_not_raises(self):
        raw = (
            b"<html>\r\n<head><title>503 Service Temporarily Unavailable</title>"
            b"</head>\r\n<body>\r\n<center><h1>503</h1></center>\r\n</body>\r\n</html>\r\n"
        )
        assert parse(503, raw) == {}

    def test_html_with_200_status_returns_empty_dict(self):
        # proxy / captive-portal HTML returned with a 200 status
        assert parse(200, b"<html>not json</html>") == {}

    def test_empty_body_returns_empty_dict(self):
        assert parse(200, b"") == {}
        assert parse(200, b"   \r\n  ") == {}

    def test_graphql_null_data_returns_empty_dict(self):
        # GraphQL error shape: {"data": null, "errors": [...]}
        raw = b'{"data": null, "errors": [{"message": "boom"}]}'
        assert parse(200, raw) == {}

    def test_4xx_status_returns_empty_dict(self):
        assert parse(404, b'{"data": {"x": 1}}') == {}

    def test_non_object_json_returns_empty_dict(self):
        assert parse(200, b"[1, 2, 3]") == {}

    def test_the_exact_reported_jsondecodeerror_input_is_handled(self):
        # "Expecting value: line 1 column 1 (char 0)" originates from parsing an
        # empty / non-JSON first byte. Confirm we degrade instead of raising.
        try:
            result = parse(200, b"")
        except Exception as e:  # pragma: no cover
            pytest.fail(f"parser raised instead of degrading: {e!r}")
        assert result == {}
