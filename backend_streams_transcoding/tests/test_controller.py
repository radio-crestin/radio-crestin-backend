"""
Unit tests for the stream controller.

Tests slug validation, deployment/service/PVC spec building, ingress generation,
and the sync logic with mocked K8s API.
"""

import unittest
from unittest.mock import MagicMock, patch

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

    def test_deployment_name(self):
        self.assertEqual(controller.deployment_name("radio-emanuel"), "live-stream-radio-emanuel")

    def test_service_name(self):
        self.assertEqual(controller.service_name("radio-emanuel"), "live-stream-radio-emanuel")

    def test_pvc_name(self):
        self.assertEqual(controller.pvc_name("radio-emanuel"), "stream-radio-emanuel")


class TestBuildDeploymentSpec(unittest.TestCase):
    """Test deployment spec generation."""

    def test_deployment_has_correct_metadata(self):
        dep = controller.build_deployment_spec("test-station", "https://stream.example.com/live")
        self.assertEqual(dep.metadata.name, "live-stream-test-station")
        self.assertEqual(dep.metadata.labels["app"], "live-stream")
        self.assertEqual(dep.metadata.labels["station"], "test-station")
        self.assertEqual(dep.metadata.annotations["stream-url"], "https://stream.example.com/live")

    def test_deployment_has_correct_env_vars(self):
        dep = controller.build_deployment_spec("test-station", "https://stream.example.com/live")
        container = dep.spec.template.spec.containers[0]
        env_map = {e.name: e.value for e in container.env}
        self.assertEqual(env_map["STATION_SLUG"], "test-station")
        self.assertEqual(env_map["STREAM_URL"], "https://stream.example.com/live")

    def test_deployment_has_emptydir_volume_by_default(self):
        dep = controller.build_deployment_spec("test-station", "https://stream.example.com/live")
        volume = dep.spec.template.spec.volumes[0]
        self.assertEqual(volume.name, "data")
        self.assertIsNotNone(volume.empty_dir)

    def test_deployment_has_probes(self):
        dep = controller.build_deployment_spec("test-station", "https://stream.example.com/live")
        container = dep.spec.template.spec.containers[0]
        self.assertIsNotNone(container.liveness_probe)
        self.assertIsNotNone(container.readiness_probe)
        self.assertIsNotNone(container.startup_probe)
        self.assertEqual(container.liveness_probe.http_get.path, "/health")

    def test_deployment_has_resource_limits(self):
        dep = controller.build_deployment_spec("test-station", "https://stream.example.com/live")
        container = dep.spec.template.spec.containers[0]
        self.assertIn("cpu", container.resources.requests)
        self.assertIn("memory", container.resources.limits)

    def test_deployment_uses_rolling_update_strategy(self):
        # RollingUpdate so a new pod is ready before the old one is killed —
        # avoids dropping listeners during image rollouts.
        dep = controller.build_deployment_spec("test-station", "https://stream.example.com/live")
        self.assertEqual(dep.spec.strategy.type, "RollingUpdate")
        self.assertEqual(dep.spec.strategy.rolling_update.max_surge, 1)
        self.assertEqual(dep.spec.strategy.rolling_update.max_unavailable, 0)

    def test_deployment_has_termination_grace_period(self):
        # Grace period must exceed the preStop sleep (5s) so connection draining completes.
        dep = controller.build_deployment_spec("test-station", "https://stream.example.com/live")
        self.assertEqual(dep.spec.template.spec.termination_grace_period_seconds, 30)

    def test_deployment_has_label_selector(self):
        dep = controller.build_deployment_spec("test-station", "https://stream.example.com/live")
        self.assertEqual(dep.spec.selector.match_labels["app"], "live-stream")
        self.assertEqual(dep.spec.selector.match_labels["station"], "test-station")

    def test_liveness_probe_fast_failure_detection(self):
        dep = controller.build_deployment_spec("test-station", "https://stream.example.com/live")
        container = dep.spec.template.spec.containers[0]
        # 2 failures × 5s period = 10s to detect failure after staleness.
        self.assertEqual(container.liveness_probe.failure_threshold, 2)
        self.assertEqual(container.liveness_probe.period_seconds, 5)


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


class TestBuildStationIngress(unittest.TestCase):
    """Test per-station ingress spec generation."""

    def test_ingress_metadata(self):
        ingress = controller.build_station_ingress("radio-a")
        self.assertEqual(ingress.metadata.name, "live-stream-radio-a")
        self.assertEqual(ingress.metadata.labels["station"], "radio-a")
        self.assertEqual(ingress.metadata.labels["app"], "live-stream")

    def test_ingress_has_regex_annotation(self):
        ingress = controller.build_station_ingress("radio-a")
        self.assertEqual(
            ingress.metadata.annotations["nginx.ingress.kubernetes.io/use-regex"],
            "true",
        )

    def test_ingress_has_rewrite_target(self):
        ingress = controller.build_station_ingress("radio-a")
        self.assertEqual(
            ingress.metadata.annotations["nginx.ingress.kubernetes.io/rewrite-target"],
            "/$1",
        )

    def test_ingress_has_new_host_path(self):
        # New host carries both the clean `/<slug>/...` route and a compat
        # `/hls/<slug>/...` route (graphql/types.py:hls_stream_url emits the
        # `/hls/` form, and pre-deploy mobile-app builds have it cached).
        ingress = controller.build_station_ingress("radio-a")
        new_rule = next(r for r in ingress.spec.rules if r.host == controller.INGRESS_HOST)
        paths = [p.path for p in new_rule.http.paths]
        self.assertIn("/radio-a/(.*)", paths)
        self.assertIn("/hls/radio-a/(.*)", paths)

    def test_ingress_has_legacy_host_path(self):
        # Legacy URL pattern (kept for backward compat): hls.radiocrestin.ro/hls/<slug>/...
        ingress = controller.build_station_ingress("radio-a")
        legacy_rule = next(
            (r for r in ingress.spec.rules if r.host == controller.LEGACY_INGRESS_HOST),
            None,
        )
        self.assertIsNotNone(legacy_rule, "Legacy host rule must be present for hls.radiocrestin.ro")
        paths = [p.path for p in legacy_rule.http.paths]
        self.assertIn("/hls/radio-a/(.*)", paths)

    def test_ingress_has_tls(self):
        ingress = controller.build_station_ingress("radio-a")
        self.assertIsNotNone(ingress.spec.tls)
        self.assertGreater(len(ingress.spec.tls), 0)

    def test_ingress_routes_to_station_service(self):
        ingress = controller.build_station_ingress("radio-a")
        for rule in ingress.spec.rules:
            for path in rule.http.paths:
                self.assertEqual(path.backend.service.name, "live-stream-radio-a")
                self.assertEqual(path.backend.service.port.number, 8080)


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

    def _mock_deployment(self, slug, stream_url, image=None):
        dep = MagicMock()
        dep.metadata.name = f"live-stream-{slug}"
        dep.metadata.labels = {"app": "live-stream", "station": slug}
        dep.metadata.annotations = {"stream-url": stream_url}
        container = MagicMock()
        container.image = image or controller.STREAMER_IMAGE
        dep.spec.template.spec.containers = [container]
        return dep

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

    def _mock_ingress(self, slug):
        ing = MagicMock()
        ing.metadata.name = f"live-stream-{slug}"
        ing.metadata.labels = {"app": "live-stream", "station": slug}
        return ing

    def _setup_kube_mocks(self, deployments=(), services=(), pvcs=(), ingresses=()):
        core_v1 = MagicMock()
        apps_v1 = MagicMock()
        networking_v1 = MagicMock()
        apps_v1.list_namespaced_deployment.return_value.items = list(deployments)
        core_v1.list_namespaced_service.return_value.items = list(services)
        core_v1.list_namespaced_persistent_volume_claim.return_value.items = list(pvcs)
        networking_v1.list_namespaced_ingress.return_value.items = list(ingresses)
        return core_v1, apps_v1, networking_v1

    @patch("controller.ensure_listing_ingress")
    @patch("controller.ensure_listing_deployment")
    @patch("controller.fetch_stations")
    def test_creates_new_station(self, mock_fetch, _mock_listing_dep, _mock_listing_ing):
        mock_fetch.return_value = [
            {"slug": "radio-new", "stream_url": "https://stream.com", "transcode_enabled": True}
        ]
        core_v1, apps_v1, networking_v1 = self._setup_kube_mocks()

        controller.sync_once(core_v1, apps_v1, networking_v1)

        apps_v1.create_namespaced_deployment.assert_called_once()
        core_v1.create_namespaced_service.assert_called_once()
        # New per-station ingress is created (not a single shared ingress patch).
        networking_v1.create_namespaced_ingress.assert_called_once()

    @patch("controller.ensure_listing_ingress")
    @patch("controller.ensure_listing_deployment")
    @patch("controller.fetch_stations")
    def test_deletes_removed_station(self, mock_fetch, _mock_listing_dep, _mock_listing_ing):
        # Simulate fetch returning no NEW stations but one to remove.
        # NB: an empty fetch result is treated as "API down — skip sync" by the
        # controller, so we need at least one desired station alongside the orphan.
        mock_fetch.return_value = [
            {"slug": "radio-keep", "stream_url": "https://keep.com", "transcode_enabled": True}
        ]
        core_v1, apps_v1, networking_v1 = self._setup_kube_mocks(
            deployments=[
                self._mock_deployment("radio-keep", "https://keep.com"),
                self._mock_deployment("radio-old", "https://old.com"),
            ],
            services=[self._mock_service("radio-keep"), self._mock_service("radio-old")],
            ingresses=[self._mock_ingress("radio-keep"), self._mock_ingress("radio-old")],
        )

        controller.sync_once(core_v1, apps_v1, networking_v1)

        # The orphan (radio-old) is removed; the kept one is left alone.
        apps_v1.delete_namespaced_deployment.assert_called_once()
        core_v1.delete_namespaced_service.assert_called_once()
        # PVCs are intentionally NOT deleted (kept for archive).
        core_v1.delete_namespaced_persistent_volume_claim.assert_not_called()
        # Orphan ingress is removed too. (sync_once calls delete twice for
        # removed stations: once in the to_delete loop, once in the orphan
        # ingress cleanup pass — both target the same ingress, so >=1.)
        self.assertTrue(networking_v1.delete_namespaced_ingress.called)
        for call_args in networking_v1.delete_namespaced_ingress.call_args_list:
            self.assertEqual(call_args.kwargs.get("name"), "live-stream-radio-old")

    @patch("controller.ensure_listing_ingress")
    @patch("controller.ensure_listing_deployment")
    @patch("controller.fetch_stations")
    def test_updates_on_url_change(self, mock_fetch, _mock_listing_dep, _mock_listing_ing):
        mock_fetch.return_value = [
            {"slug": "radio-a", "stream_url": "https://new-url.com", "transcode_enabled": True}
        ]
        core_v1, apps_v1, networking_v1 = self._setup_kube_mocks(
            deployments=[self._mock_deployment("radio-a", "https://old-url.com")],
            services=[self._mock_service("radio-a")],
            ingresses=[self._mock_ingress("radio-a")],
        )

        controller.sync_once(core_v1, apps_v1, networking_v1)

        # Should patch the deployment (not delete+create).
        apps_v1.patch_namespaced_deployment.assert_called_once()
        apps_v1.delete_namespaced_deployment.assert_not_called()
        apps_v1.create_namespaced_deployment.assert_not_called()

    @patch("controller.ensure_listing_ingress")
    @patch("controller.ensure_listing_deployment")
    @patch("controller.fetch_stations")
    def test_no_changes_when_in_sync(self, mock_fetch, _mock_listing_dep, _mock_listing_ing):
        mock_fetch.return_value = [
            {"slug": "radio-a", "stream_url": "https://stream.com", "transcode_enabled": True}
        ]
        core_v1, apps_v1, networking_v1 = self._setup_kube_mocks(
            deployments=[self._mock_deployment("radio-a", "https://stream.com")],
            services=[self._mock_service("radio-a")],
            ingresses=[self._mock_ingress("radio-a")],
        )

        controller.sync_once(core_v1, apps_v1, networking_v1)

        # Nothing should be created, deleted, or patched when fully in sync.
        apps_v1.create_namespaced_deployment.assert_not_called()
        apps_v1.delete_namespaced_deployment.assert_not_called()
        apps_v1.patch_namespaced_deployment.assert_not_called()
        networking_v1.create_namespaced_ingress.assert_not_called()
        networking_v1.delete_namespaced_ingress.assert_not_called()


if __name__ == "__main__":
    unittest.main()
