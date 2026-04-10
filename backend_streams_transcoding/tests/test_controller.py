"""
Unit tests for the stream controller.

Tests slug validation, pod/service/PVC spec building, ingress generation,
and the sync logic with mocked K8s API.
"""

import re
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

import sys
import os

# Add parent dir to path so we can import controller
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import controller


class TestSlugValidation(unittest.TestCase):
    """Test slug pattern validation."""

    def test_valid_slugs(self):
        valid = ["radio-emanuel", "station-01", "abc", "a1", "test-station-name"]
        for slug in valid:
            self.assertTrue(
                controller.SLUG_PATTERN.match(slug),
                f"Slug should be valid: {slug}",
            )

    def test_invalid_slugs(self):
        invalid = [
            "",
            "-starts-with-dash",
            "ends-with-dash-",
            "UPPERCASE",
            "has spaces",
            "special!chars",
            "a",  # single char doesn't match pattern (needs 2+)
            "../path-traversal",
            "slug_with_underscores",
        ]
        for slug in invalid:
            self.assertIsNone(
                controller.SLUG_PATTERN.match(slug),
                f"Slug should be invalid: {slug}",
            )


class TestNaming(unittest.TestCase):
    """Test resource naming conventions."""

    def test_pod_name(self):
        self.assertEqual(controller.pod_name("radio-emanuel"), "live-stream-radio-emanuel")

    def test_service_name(self):
        self.assertEqual(controller.service_name("radio-emanuel"), "live-stream-radio-emanuel")

    def test_pvc_name(self):
        self.assertEqual(controller.pvc_name("radio-emanuel"), "stream-radio-emanuel")


class TestBuildPodSpec(unittest.TestCase):
    """Test pod spec generation."""

    def test_pod_has_correct_metadata(self):
        pod = controller.build_pod_spec("test-station", "https://stream.example.com/live")
        self.assertEqual(pod.metadata.name, "live-stream-test-station")
        self.assertEqual(pod.metadata.labels["app"], "live-stream")
        self.assertEqual(pod.metadata.labels["station"], "test-station")
        self.assertEqual(pod.metadata.annotations["stream-url"], "https://stream.example.com/live")

    def test_pod_has_correct_env_vars(self):
        pod = controller.build_pod_spec("test-station", "https://stream.example.com/live")
        container = pod.spec.containers[0]
        env_map = {e.name: e.value for e in container.env}
        self.assertEqual(env_map["STATION_SLUG"], "test-station")
        self.assertEqual(env_map["STREAM_URL"], "https://stream.example.com/live")

    def test_pod_has_pvc_volume(self):
        pod = controller.build_pod_spec("test-station", "https://stream.example.com/live")
        volume = pod.spec.volumes[0]
        self.assertEqual(volume.name, "data")
        self.assertEqual(volume.persistent_volume_claim.claim_name, "stream-test-station")

    def test_pod_has_probes(self):
        pod = controller.build_pod_spec("test-station", "https://stream.example.com/live")
        container = pod.spec.containers[0]
        self.assertIsNotNone(container.liveness_probe)
        self.assertIsNotNone(container.readiness_probe)
        self.assertEqual(container.liveness_probe.http_get.path, "/health")
        self.assertEqual(container.liveness_probe.http_get.port, 8080)

    def test_pod_has_resource_limits(self):
        pod = controller.build_pod_spec("test-station", "https://stream.example.com/live")
        container = pod.spec.containers[0]
        self.assertIn("cpu", container.resources.requests)
        self.assertIn("memory", container.resources.limits)

    def test_pod_restart_policy(self):
        pod = controller.build_pod_spec("test-station", "https://stream.example.com/live")
        self.assertEqual(pod.spec.restart_policy, "Always")


class TestBuildServiceSpec(unittest.TestCase):
    """Test service spec generation."""

    def test_service_selects_correct_pod(self):
        svc = controller.build_service_spec("test-station")
        self.assertEqual(svc.spec.selector["app"], "live-stream")
        self.assertEqual(svc.spec.selector["station"], "test-station")

    def test_service_port(self):
        svc = controller.build_service_spec("test-station")
        self.assertEqual(svc.spec.ports[0].port, 8080)
        self.assertEqual(svc.spec.ports[0].target_port, 8080)


class TestBuildPVCSpec(unittest.TestCase):
    """Test PVC spec generation."""

    def test_pvc_name_and_labels(self):
        pvc = controller.build_pvc_spec("test-station")
        self.assertEqual(pvc.metadata.name, "stream-test-station")
        self.assertEqual(pvc.metadata.labels["station"], "test-station")

    def test_pvc_access_mode(self):
        pvc = controller.build_pvc_spec("test-station")
        self.assertIn("ReadWriteOnce", pvc.spec.access_modes)


class TestBuildIngress(unittest.TestCase):
    """Test ingress spec generation."""

    def test_ingress_with_stations(self):
        ingress = controller.build_ingress(["radio-a", "radio-b"])
        self.assertEqual(ingress.metadata.name, "live-streaming")
        # Should have rules for both new and legacy hosts
        self.assertIsNotNone(ingress.spec.rules)
        self.assertGreaterEqual(len(ingress.spec.rules), 1)

    def test_ingress_empty_stations(self):
        ingress = controller.build_ingress([])
        # No rules when no stations
        self.assertIsNone(ingress.spec.rules)

    def test_ingress_has_regex_annotation(self):
        ingress = controller.build_ingress(["radio-a"])
        self.assertEqual(
            ingress.metadata.annotations["nginx.ingress.kubernetes.io/use-regex"],
            "true",
        )

    def test_ingress_has_rewrite_target(self):
        ingress = controller.build_ingress(["radio-a"])
        self.assertEqual(
            ingress.metadata.annotations["nginx.ingress.kubernetes.io/rewrite-target"],
            "/$1",
        )

    def test_ingress_paths_are_sorted(self):
        ingress = controller.build_ingress(["z-station", "a-station"])
        new_paths = ingress.spec.rules[0].http.paths
        self.assertEqual(new_paths[0].path, "/a-station/(.*)")
        self.assertEqual(new_paths[1].path, "/z-station/(.*)")

    def test_ingress_has_tls(self):
        ingress = controller.build_ingress(["radio-a"])
        self.assertIsNotNone(ingress.spec.tls)
        self.assertGreater(len(ingress.spec.tls), 0)

    def test_legacy_paths_have_hls_prefix(self):
        ingress = controller.build_ingress(["radio-a"])
        # Find the legacy host rule
        legacy_rule = None
        for rule in ingress.spec.rules:
            if rule.host == controller.LEGACY_INGRESS_HOST:
                legacy_rule = rule
                break
        self.assertIsNotNone(legacy_rule, "Should have a legacy host rule")
        self.assertEqual(legacy_rule.http.paths[0].path, "/hls/radio-a/(.*)")


class TestFetchStations(unittest.TestCase):
    """Test station fetching with mocked HTTP."""

    @patch("controller.requests.post")
    def test_valid_response(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "data": {
                "stations": [
                    {"slug": "radio-a", "stream_url": "https://stream-a.com", "transcode_enabled": True},
                    {"slug": "radio-b", "stream_url": "https://stream-b.com", "transcode_enabled": True},
                ]
            }
        }
        stations = controller.fetch_stations()
        self.assertEqual(len(stations), 2)
        self.assertEqual(stations[0]["slug"], "radio-a")

    @patch("controller.requests.post")
    def test_filters_transcode_disabled(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "data": {
                "stations": [
                    {"slug": "radio-a", "stream_url": "https://stream.com", "transcode_enabled": True},
                    {"slug": "radio-b", "stream_url": "https://stream.com", "transcode_enabled": False},
                ]
            }
        }
        stations = controller.fetch_stations()
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]["slug"], "radio-a")

    @patch("controller.requests.post")
    def test_filters_invalid_slugs(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "data": {
                "stations": [
                    {"slug": "valid-slug", "stream_url": "https://stream.com", "transcode_enabled": True},
                    {"slug": "INVALID", "stream_url": "https://stream.com", "transcode_enabled": True},
                    {"slug": "../traversal", "stream_url": "https://stream.com", "transcode_enabled": True},
                ]
            }
        }
        stations = controller.fetch_stations()
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]["slug"], "valid-slug")

    @patch("controller.requests.post")
    def test_graphql_error(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "errors": [{"message": "something went wrong"}]
        }
        stations = controller.fetch_stations()
        self.assertEqual(stations, [])

    @patch("controller.requests.post")
    def test_network_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("Connection refused")
        stations = controller.fetch_stations()
        self.assertEqual(stations, [])


class TestSyncOnce(unittest.TestCase):
    """Test the sync_once logic with mocked K8s clients."""

    def _mock_pod(self, slug, stream_url):
        pod = MagicMock()
        pod.metadata.name = f"live-stream-{slug}"
        pod.metadata.labels = {"app": "live-stream", "station": slug}
        pod.metadata.annotations = {"stream-url": stream_url}
        return pod

    def _mock_service(self, slug):
        svc = MagicMock()
        svc.metadata.name = f"live-stream-{slug}"
        svc.metadata.labels = {"app": "live-stream", "station": slug}
        return svc

    def _mock_pvc(self, slug):
        pvc = MagicMock()
        pvc.metadata.name = f"stream-{slug}"
        pvc.metadata.labels = {"app": "live-stream", "station": slug}
        return pvc

    @patch("controller.fetch_stations")
    @patch("controller.update_ingress")
    def test_creates_new_station(self, mock_update_ingress, mock_fetch):
        mock_fetch.return_value = [
            {"slug": "radio-new", "stream_url": "https://stream.com"}
        ]

        core_v1 = MagicMock()
        networking_v1 = MagicMock()

        # No existing resources
        core_v1.list_namespaced_pod.return_value.items = []
        core_v1.list_namespaced_service.return_value.items = []
        core_v1.list_namespaced_persistent_volume_claim.return_value.items = []

        controller.sync_once(core_v1, networking_v1)

        # Should create PVC, pod, and service
        core_v1.create_namespaced_persistent_volume_claim.assert_called_once()
        core_v1.create_namespaced_pod.assert_called_once()
        core_v1.create_namespaced_service.assert_called_once()
        mock_update_ingress.assert_called_once()

    @patch("controller.fetch_stations")
    @patch("controller.update_ingress")
    def test_deletes_removed_station(self, mock_update_ingress, mock_fetch):
        mock_fetch.return_value = []  # No stations wanted

        core_v1 = MagicMock()
        networking_v1 = MagicMock()

        # One existing pod
        core_v1.list_namespaced_pod.return_value.items = [
            self._mock_pod("radio-old", "https://old.com")
        ]
        core_v1.list_namespaced_service.return_value.items = [
            self._mock_service("radio-old")
        ]
        core_v1.list_namespaced_persistent_volume_claim.return_value.items = [
            self._mock_pvc("radio-old")
        ]

        controller.sync_once(core_v1, networking_v1)

        # Should delete pod and service (but not PVC — kept for archive)
        core_v1.delete_namespaced_pod.assert_called_once()
        core_v1.delete_namespaced_service.assert_called_once()
        core_v1.delete_namespaced_persistent_volume_claim.assert_not_called()

    @patch("controller.fetch_stations")
    @patch("controller.update_ingress")
    def test_recreates_on_url_change(self, mock_update_ingress, mock_fetch):
        mock_fetch.return_value = [
            {"slug": "radio-a", "stream_url": "https://new-url.com"}
        ]

        core_v1 = MagicMock()
        networking_v1 = MagicMock()

        # Existing pod with old URL
        core_v1.list_namespaced_pod.return_value.items = [
            self._mock_pod("radio-a", "https://old-url.com")
        ]
        core_v1.list_namespaced_service.return_value.items = [
            self._mock_service("radio-a")
        ]
        core_v1.list_namespaced_persistent_volume_claim.return_value.items = [
            self._mock_pvc("radio-a")
        ]

        controller.sync_once(core_v1, networking_v1)

        # Should delete old pod and create new one
        core_v1.delete_namespaced_pod.assert_called_once()
        core_v1.create_namespaced_pod.assert_called_once()

    @patch("controller.fetch_stations")
    @patch("controller.update_ingress")
    def test_no_changes_when_in_sync(self, mock_update_ingress, mock_fetch):
        mock_fetch.return_value = [
            {"slug": "radio-a", "stream_url": "https://stream.com"}
        ]

        core_v1 = MagicMock()
        networking_v1 = MagicMock()

        # Existing pod with same URL
        core_v1.list_namespaced_pod.return_value.items = [
            self._mock_pod("radio-a", "https://stream.com")
        ]
        core_v1.list_namespaced_service.return_value.items = [
            self._mock_service("radio-a")
        ]
        core_v1.list_namespaced_persistent_volume_claim.return_value.items = [
            self._mock_pvc("radio-a")
        ]

        controller.sync_once(core_v1, networking_v1)

        # Should not create or delete anything
        core_v1.create_namespaced_pod.assert_not_called()
        core_v1.delete_namespaced_pod.assert_not_called()
        core_v1.create_namespaced_service.assert_not_called()
        # But ingress is still updated
        mock_update_ingress.assert_called_once()


if __name__ == "__main__":
    unittest.main()
