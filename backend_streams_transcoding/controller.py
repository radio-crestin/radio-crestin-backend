"""
Stream Controller - syncs station deployments with Django API.

Polls Django GraphQL for stations with transcoding enabled,
creates/deletes Kubernetes Deployments, Services, PVCs, and ingress rules.
Uses Deployments (not bare Pods) for automatic restart on failure.
"""

import logging
import os
import re
import sys
import time

import requests
from kubernetes import client, config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("stream-controller")

# Configuration from environment
GRAPHQL_ENDPOINT = os.environ.get("GRAPHQL_ENDPOINT", "http://web:8080/v1/graphql")
NAMESPACE = os.environ.get("NAMESPACE", "radio-crestin")
STREAMER_IMAGE = os.environ.get("STREAMER_IMAGE", "radio-crestin/live-streaming:latest")
IMAGE_PULL_SECRET = os.environ.get("IMAGE_PULL_SECRET", "")
RETENTION_DAYS = os.environ.get("RETENTION_DAYS", "7")
OPUS_BITRATE_LOW = os.environ.get("OPUS_BITRATE_LOW", "32k")
OPUS_BITRATE_HIGH = os.environ.get("OPUS_BITRATE_HIGH", "64k")
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL", "60"))
INGRESS_HOST = os.environ.get("INGRESS_HOST", "live.radiocrestin.ro")
LEGACY_INGRESS_HOST = os.environ.get("LEGACY_INGRESS_HOST", "hls.radiocrestin.ro")
PVC_STORAGE_SIZE = os.environ.get("PVC_STORAGE_SIZE", "5Gi")
PVC_STORAGE_CLASS = os.environ.get("PVC_STORAGE_CLASS", "")

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
LABEL_APP = "live-stream"

# GraphQL query to fetch stations (disabled=False is applied server-side by default)
# We fetch transcode_enabled to filter client-side
STATIONS_QUERY = """
query {
    stations(order_by: {order: asc}) {
        slug
        stream_url
        transcode_enabled
    }
}
"""


def fetch_stations() -> list[dict]:
    """Fetch active stations with transcoding enabled from Django GraphQL."""
    try:
        resp = requests.post(
            GRAPHQL_ENDPOINT,
            json={"query": STATIONS_QUERY},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            log.error("GraphQL errors: %s", data["errors"])
            return []

        stations = data.get("data", {}).get("stations", [])
        # Filter to only stations with transcoding enabled, validate slugs
        valid = []
        for s in stations:
            slug = s.get("slug", "")
            if not s.get("transcode_enabled", False):
                continue
            if SLUG_PATTERN.match(slug):
                valid.append(s)
            else:
                log.warning("Skipping station with invalid slug: %r", slug)
        return valid

    except requests.RequestException as e:
        log.error("Failed to fetch stations: %s", e)
        return []


def deployment_name(slug: str) -> str:
    return f"live-stream-{slug}"


def service_name(slug: str) -> str:
    return f"live-stream-{slug}"


def pvc_name(slug: str) -> str:
    return f"stream-{slug}"


def build_deployment_spec(slug: str, stream_url: str) -> client.V1Deployment:
    """Build Deployment spec for a station streamer with fast restart on failure."""
    labels = {"app": LABEL_APP, "station": slug}

    return client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(
            name=deployment_name(slug),
            namespace=NAMESPACE,
            labels=labels,
            annotations={"stream-url": stream_url},
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            # Recreate strategy — no overlap, fast restart
            strategy=client.V1DeploymentStrategy(type="Recreate"),
            selector=client.V1LabelSelector(match_labels=labels),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels=labels,
                    annotations={"stream-url": stream_url},
                ),
                spec=client.V1PodSpec(
                    # Fast restart: minimal backoff
                    restart_policy="Always",
                    termination_grace_period_seconds=10,
                    image_pull_secrets=[
                        client.V1LocalObjectReference(name=IMAGE_PULL_SECRET)
                    ] if IMAGE_PULL_SECRET else None,
                    containers=[
                        client.V1Container(
                            name="streamer",
                            image=STREAMER_IMAGE,
                            image_pull_policy="Always",
                            env=[
                                client.V1EnvVar(name="STATION_SLUG", value=slug),
                                client.V1EnvVar(name="STREAM_URL", value=stream_url),
                                client.V1EnvVar(name="RETENTION_DAYS", value=RETENTION_DAYS),
                                client.V1EnvVar(name="OPUS_BITRATE_LOW", value=OPUS_BITRATE_LOW),
                                client.V1EnvVar(name="OPUS_BITRATE_HIGH", value=OPUS_BITRATE_HIGH),
                            ],
                            ports=[client.V1ContainerPort(container_port=8080)],
                            volume_mounts=[
                                client.V1VolumeMount(name="data", mount_path="/data"),
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={"cpu": "50m", "memory": "64Mi"},
                                limits={"cpu": "200m", "memory": "256Mi"},
                            ),
                            # Startup probe: generous window for FFmpeg to produce first segments
                            startup_probe=client.V1Probe(
                                http_get=client.V1HTTPGetAction(path="/health", port=8080),
                                initial_delay_seconds=5,
                                period_seconds=5,
                                failure_threshold=12,  # 60s max startup
                            ),
                            # Liveness: fast detection, fast restart
                            liveness_probe=client.V1Probe(
                                http_get=client.V1HTTPGetAction(path="/health", port=8080),
                                period_seconds=10,
                                failure_threshold=2,  # 20s to detect failure
                                timeout_seconds=5,
                            ),
                            readiness_probe=client.V1Probe(
                                http_get=client.V1HTTPGetAction(path="/health", port=8080),
                                period_seconds=5,
                                failure_threshold=1,
                                timeout_seconds=3,
                            ),
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="data",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name=pvc_name(slug),
                            ),
                        ),
                    ],
                ),
            ),
        ),
    )


def build_service_spec(slug: str) -> client.V1Service:
    """Build the service spec for a station streamer."""
    return client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(
            name=service_name(slug),
            namespace=NAMESPACE,
            labels={"app": LABEL_APP, "station": slug},
        ),
        spec=client.V1ServiceSpec(
            selector={"app": LABEL_APP, "station": slug},
            ports=[
                client.V1ServicePort(port=8080, target_port=8080, protocol="TCP"),
            ],
        ),
    )


def build_pvc_spec(slug: str) -> client.V1PersistentVolumeClaim:
    """Build PVC spec for station data."""
    spec = client.V1PersistentVolumeClaimSpec(
        access_modes=["ReadWriteOnce"],
        resources=client.V1VolumeResourceRequirements(
            requests={"storage": PVC_STORAGE_SIZE},
        ),
    )
    if PVC_STORAGE_CLASS:
        spec.storage_class_name = PVC_STORAGE_CLASS

    return client.V1PersistentVolumeClaim(
        api_version="v1",
        kind="PersistentVolumeClaim",
        metadata=client.V1ObjectMeta(
            name=pvc_name(slug),
            namespace=NAMESPACE,
            labels={"app": LABEL_APP, "station": slug},
        ),
        spec=spec,
    )


def _build_paths_for_slugs(active_slugs: list[str]) -> list[client.V1HTTPIngressPath]:
    """Build ingress paths for a list of station slugs."""
    paths = []
    for slug in sorted(active_slugs):
        paths.append(
            client.V1HTTPIngressPath(
                path=f"/{slug}/(.*)",
                path_type="ImplementationSpecific",
                backend=client.V1IngressBackend(
                    service=client.V1IngressServiceBackend(
                        name=service_name(slug),
                        port=client.V1ServiceBackendPort(number=8080),
                    ),
                ),
            )
        )
    return paths


def _build_legacy_paths_for_slugs(active_slugs: list[str]) -> list[client.V1HTTPIngressPath]:
    """Build backward-compatible ingress paths: /hls/<slug>/(.*) -> station pod."""
    paths = []
    for slug in sorted(active_slugs):
        paths.append(
            client.V1HTTPIngressPath(
                path=f"/hls/{slug}/(.*)",
                path_type="ImplementationSpecific",
                backend=client.V1IngressBackend(
                    service=client.V1IngressServiceBackend(
                        name=service_name(slug),
                        port=client.V1ServiceBackendPort(number=8080),
                    ),
                ),
            )
        )
    return paths


def build_ingress(active_slugs: list[str]) -> client.V1Ingress:
    """Build ingress with per-station path routing for both new and legacy hosts."""
    new_paths = _build_paths_for_slugs(active_slugs)
    legacy_paths = _build_legacy_paths_for_slugs(active_slugs)

    rules = []
    hosts = []

    # New host: live.radiocrestin.ro/<slug>/...
    if new_paths:
        rules.append(
            client.V1IngressRule(
                host=INGRESS_HOST,
                http=client.V1HTTPIngressRuleValue(paths=new_paths),
            )
        )
        hosts.append(INGRESS_HOST)

    # Legacy host: hls.radiocrestin.ro/hls/<slug>/...
    if legacy_paths and LEGACY_INGRESS_HOST:
        rules.append(
            client.V1IngressRule(
                host=LEGACY_INGRESS_HOST,
                http=client.V1HTTPIngressRuleValue(paths=legacy_paths),
            )
        )
        if LEGACY_INGRESS_HOST not in hosts:
            hosts.append(LEGACY_INGRESS_HOST)

    tls = []
    if hosts:
        tls.append(
            client.V1IngressTLS(
                hosts=hosts,
                secret_name="live-radiocrestin-tls",
            )
        )

    return client.V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=client.V1ObjectMeta(
            name="live-streaming",
            namespace=NAMESPACE,
            annotations={
                "nginx.ingress.kubernetes.io/use-regex": "true",
                "nginx.ingress.kubernetes.io/rewrite-target": "/$1",
                "nginx.ingress.kubernetes.io/enable-cors": "true",
                "nginx.ingress.kubernetes.io/cors-allow-origin": "*",
                "nginx.ingress.kubernetes.io/cors-allow-methods": "GET, HEAD, OPTIONS",
                "nginx.ingress.kubernetes.io/cors-allow-headers": "Range, Content-Type, Accept, Origin",
            },
        ),
        spec=client.V1IngressSpec(
            ingress_class_name="nginx",
            tls=tls if tls else None,
            rules=rules if rules else None,
        ),
    )


# ── K8s state queries ──────────────────────────────────────────────

def get_existing_deployments(apps_v1: client.AppsV1Api) -> dict[str, client.V1Deployment]:
    """Get existing live-stream deployments indexed by station slug."""
    deps = apps_v1.list_namespaced_deployment(
        namespace=NAMESPACE,
        label_selector=f"app={LABEL_APP}",
    )
    result = {}
    for dep in deps.items:
        slug = dep.metadata.labels.get("station", "")
        if slug:
            result[slug] = dep
    return result


def get_existing_services(core_v1: client.CoreV1Api) -> set[str]:
    """Get existing live-stream service names."""
    services = core_v1.list_namespaced_service(
        namespace=NAMESPACE,
        label_selector=f"app={LABEL_APP}",
    )
    return {svc.metadata.labels.get("station", "") for svc in services.items}


def get_existing_pvcs(core_v1: client.CoreV1Api) -> set[str]:
    """Get existing live-stream PVC slugs."""
    pvcs = core_v1.list_namespaced_persistent_volume_claim(
        namespace=NAMESPACE,
        label_selector=f"app={LABEL_APP}",
    )
    return {pvc.metadata.labels.get("station", "") for pvc in pvcs.items}


# ── CRUD operations ────────────────────────────────────────────────

def ensure_pvc(core_v1: client.CoreV1Api, slug: str, existing_pvcs: set[str]):
    """Create PVC if it doesn't exist."""
    if slug in existing_pvcs:
        return
    log.info("Creating PVC for station: %s", slug)
    core_v1.create_namespaced_persistent_volume_claim(
        namespace=NAMESPACE,
        body=build_pvc_spec(slug),
    )


def create_deployment(apps_v1: client.AppsV1Api, slug: str, stream_url: str):
    """Create a station streamer deployment."""
    log.info("Creating deployment for station: %s", slug)
    apps_v1.create_namespaced_deployment(
        namespace=NAMESPACE,
        body=build_deployment_spec(slug, stream_url),
    )


def update_deployment(apps_v1: client.AppsV1Api, slug: str, stream_url: str):
    """Update a station streamer deployment (e.g. stream_url changed)."""
    log.info("Updating deployment for station: %s", slug)
    apps_v1.patch_namespaced_deployment(
        name=deployment_name(slug),
        namespace=NAMESPACE,
        body=build_deployment_spec(slug, stream_url),
    )


def delete_deployment(apps_v1: client.AppsV1Api, slug: str):
    """Delete a station streamer deployment."""
    log.info("Deleting deployment for station: %s", slug)
    try:
        apps_v1.delete_namespaced_deployment(
            name=deployment_name(slug),
            namespace=NAMESPACE,
        )
    except client.ApiException as e:
        if e.status != 404:
            raise


def ensure_service(core_v1: client.CoreV1Api, slug: str, existing_services: set[str]):
    """Create service if it doesn't exist."""
    if slug in existing_services:
        return
    log.info("Creating service for station: %s", slug)
    core_v1.create_namespaced_service(
        namespace=NAMESPACE,
        body=build_service_spec(slug),
    )


def delete_service(core_v1: client.CoreV1Api, slug: str):
    """Delete a station streamer service."""
    log.info("Deleting service for station: %s", slug)
    try:
        core_v1.delete_namespaced_service(
            name=service_name(slug),
            namespace=NAMESPACE,
        )
    except client.ApiException as e:
        if e.status != 404:
            raise


def update_ingress(networking_v1: client.NetworkingV1Api, active_slugs: list[str]):
    """Create or update the live-streaming ingress."""
    if not active_slugs:
        # No stations → delete ingress if it exists, otherwise do nothing
        try:
            networking_v1.delete_namespaced_ingress(
                name="live-streaming",
                namespace=NAMESPACE,
            )
            log.info("Deleted ingress (no active stations)")
        except client.ApiException as e:
            if e.status != 404:
                raise
        return

    ingress = build_ingress(active_slugs)
    try:
        networking_v1.read_namespaced_ingress(
            name="live-streaming",
            namespace=NAMESPACE,
        )
        # Ingress exists, patch it
        log.info("Updating ingress with %d station routes", len(active_slugs))
        networking_v1.patch_namespaced_ingress(
            name="live-streaming",
            namespace=NAMESPACE,
            body=ingress,
        )
    except client.ApiException as e:
        if e.status == 404:
            log.info("Creating ingress with %d station routes", len(active_slugs))
            networking_v1.create_namespaced_ingress(
                namespace=NAMESPACE,
                body=ingress,
            )
        else:
            raise


# ── Cleanup legacy bare pods ───────────────────────────────────────

def cleanup_legacy_pods(core_v1: client.CoreV1Api):
    """Delete any bare pods left over from the old controller (pre-Deployment)."""
    pods = core_v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=f"app={LABEL_APP}",
    )
    for pod in pods.items:
        # Bare pods have no ownerReferences; Deployment-managed pods do
        if not pod.metadata.owner_references:
            slug = pod.metadata.labels.get("station", "")
            log.info("Deleting legacy bare pod: %s (station: %s)", pod.metadata.name, slug)
            try:
                core_v1.delete_namespaced_pod(
                    name=pod.metadata.name,
                    namespace=NAMESPACE,
                )
            except client.ApiException as e:
                if e.status != 404:
                    log.warning("Failed to delete legacy pod %s: %s", pod.metadata.name, e)


# ── Main sync loop ─────────────────────────────────────────────────

def sync_once(
    core_v1: client.CoreV1Api,
    apps_v1: client.AppsV1Api,
    networking_v1: client.NetworkingV1Api,
):
    """Run one sync cycle."""
    # 1. Fetch desired state from Django
    desired_stations = fetch_stations()
    desired_map = {s["slug"]: s["stream_url"] for s in desired_stations}
    desired_slugs = set(desired_map.keys())

    log.info("Desired stations: %d", len(desired_slugs))

    # 2. Get current state from K8s
    existing_deployments = get_existing_deployments(apps_v1)
    existing_services = get_existing_services(core_v1)
    existing_pvcs = get_existing_pvcs(core_v1)
    existing_slugs = set(existing_deployments.keys())

    log.info("Existing deployments: %d", len(existing_slugs))

    # 3. Compute diff
    to_create = desired_slugs - existing_slugs
    to_delete = existing_slugs - desired_slugs
    to_check = desired_slugs & existing_slugs

    # Check for stream_url changes (need update)
    to_update = set()
    for slug in to_check:
        dep = existing_deployments[slug]
        current_url = dep.metadata.annotations.get("stream-url", "")
        if current_url != desired_map[slug]:
            log.info(
                "Stream URL changed for %s: %r -> %r",
                slug, current_url, desired_map[slug],
            )
            to_update.add(slug)

    # 4. Apply changes
    # Delete deployments that are no longer needed
    for slug in to_delete:
        delete_deployment(apps_v1, slug)
        delete_service(core_v1, slug)

    # Update deployments with changed stream_url
    for slug in to_update:
        update_deployment(apps_v1, slug, desired_map[slug])

    # Create new deployments
    for slug in to_create:
        ensure_pvc(core_v1, slug, existing_pvcs)
        create_deployment(apps_v1, slug, desired_map[slug])
        ensure_service(core_v1, slug, existing_services)

    # 5. Update ingress to match active stations
    active_slugs = list(desired_slugs)
    update_ingress(networking_v1, active_slugs)

    created = len(to_create)
    deleted = len(to_delete)
    updated = len(to_update)
    if created or deleted or updated:
        log.info(
            "Sync complete: created=%d, deleted=%d, updated=%d",
            created, deleted, updated,
        )
    else:
        log.info("Sync complete: no changes")


def main():
    """Main controller loop."""
    log.info("Stream controller starting")
    log.info("GraphQL endpoint: %s", GRAPHQL_ENDPOINT)
    log.info("Namespace: %s", NAMESPACE)
    log.info("Streamer image: %s", STREAMER_IMAGE)
    log.info("Sync interval: %ds", SYNC_INTERVAL)

    # Load K8s config (in-cluster when running in pod)
    try:
        config.load_incluster_config()
        log.info("Loaded in-cluster K8s config")
    except config.ConfigException:
        config.load_kube_config()
        log.info("Loaded local K8s config (development mode)")

    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    networking_v1 = client.NetworkingV1Api()

    # One-time cleanup: delete any bare pods from the old controller
    try:
        cleanup_legacy_pods(core_v1)
    except Exception:
        log.exception("Error cleaning up legacy pods")

    while True:
        try:
            sync_once(core_v1, apps_v1, networking_v1)
        except Exception:
            log.exception("Error during sync cycle")

        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
