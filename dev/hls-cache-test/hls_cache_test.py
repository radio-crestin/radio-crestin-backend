#!/usr/bin/env python3
"""
HLS Cache Consistency & Latency Tester

Fetches live proxy lists from two GitHub sources, deduplicates them, then
downloads an HLS .ts segment through every proxy to verify cache consistency
and measure latency.

Sources:
  - roosterkid/openproxylist  (HTTPS proxies with country/ISP metadata)
  - TheSpeedX/SOCKS-List      (plain HTTP proxies, large list)

Usage:
    pip install httpx rich
    python hls_cache_test.py
    python hls_cache_test.py --url https://hls.radiocrestin.ro/hls/radio-eldad/1771843825.ts
    python hls_cache_test.py --timeout 15 --concurrency 50
    python hls_cache_test.py --max-proxies 200
"""

import argparse
import asyncio
import hashlib
import re
import time
from dataclasses import dataclass, field

import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn

TARGET_URL = "https://hls.radiocrestin.ro/hls/radio-eldad/1771843825.ts"

PROXY_SOURCES = {
    "roosterkid": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS.txt",
    "speedx": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
}

CACHE_HEADERS = [
    "x-cache",
    "x-cache-status",
    "cf-cache-status",
    "x-varnish",
    "age",
    "cache-control",
    "x-served-by",
    "x-cdn",
    "via",
    "x-proxy-cache",
]

console = Console()


@dataclass
class ProxyResult:
    proxy: str
    source: str = ""
    country: str = ""
    isp: str = ""
    success: bool = False
    status_code: int = 0
    latency_connect: float = 0.0
    latency_ttfb: float = 0.0
    latency_total: float = 0.0
    content_hash: str = ""
    content_size: int = 0
    cache_headers: dict = field(default_factory=dict)
    error: str = ""


@dataclass
class ProxyEntry:
    ip: str
    port: str
    source: str
    country: str = ""
    isp: str = ""

    @property
    def url(self) -> str:
        return f"http://{self.ip}:{self.port}"

    @property
    def key(self) -> str:
        return f"{self.ip}:{self.port}"


def parse_roosterkid(text: str) -> list[ProxyEntry]:
    """
    Parse roosterkid format:
    🇧🇩 114.130.175.18:8080 301ms BD [Bangladesh Telegraph & Telephone Board]
    """
    entries = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(
            r'^[^\d]*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)\s+\d+ms\s+(\w{2})\s+\[(.+?)\]',
            line,
        )
        if m:
            entries.append(ProxyEntry(
                ip=m.group(1), port=m.group(2), source="roosterkid",
                country=m.group(3), isp=m.group(4),
            ))
    return entries


def parse_speedx(text: str) -> list[ProxyEntry]:
    """
    Parse SpeedX format (plain IP:PORT per line).
    """
    entries = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)$', line)
        if m:
            entries.append(ProxyEntry(
                ip=m.group(1), port=m.group(2), source="speedx",
            ))
    return entries


async def fetch_all_proxies() -> list[ProxyEntry]:
    """Download both proxy lists, parse and deduplicate."""
    console.print("[yellow]Fetching proxy lists...[/yellow]")

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
        responses = await asyncio.gather(
            client.get(PROXY_SOURCES["roosterkid"]),
            client.get(PROXY_SOURCES["speedx"]),
            return_exceptions=True,
        )

    all_entries: list[ProxyEntry] = []

    # roosterkid
    if isinstance(responses[0], Exception):
        console.print(f"  [red]roosterkid failed: {responses[0]}[/red]")
    else:
        responses[0].raise_for_status()
        rk = parse_roosterkid(responses[0].text)
        console.print(f"  roosterkid: [bold]{len(rk)}[/bold] proxies")
        all_entries.extend(rk)

    # speedx
    if isinstance(responses[1], Exception):
        console.print(f"  [red]speedx failed: {responses[1]}[/red]")
    else:
        responses[1].raise_for_status()
        sx = parse_speedx(responses[1].text)
        console.print(f"  speedx:     [bold]{len(sx)}[/bold] proxies")
        all_entries.extend(sx)

    # Deduplicate by IP:PORT, preferring roosterkid (has metadata)
    seen = {}
    for entry in all_entries:
        if entry.key not in seen:
            seen[entry.key] = entry
        elif entry.source == "roosterkid" and seen[entry.key].source != "roosterkid":
            seen[entry.key] = entry  # prefer the one with metadata

    deduped = list(seen.values())
    console.print(f"  Deduplicated: [bold]{len(deduped)}[/bold] unique proxies")
    return deduped


async def fetch_via_proxy(
    entry: ProxyEntry, url: str, timeout: float, progress: Progress, task_id
) -> ProxyResult:
    """Download the URL through a single proxy."""
    result = ProxyResult(
        proxy=entry.url,
        source=entry.source,
        country=entry.country,
        isp=entry.isp,
    )

    t_start = time.monotonic()
    try:
        async with httpx.AsyncClient(
            proxy=entry.url,
            timeout=httpx.Timeout(timeout),
            verify=False,
            follow_redirects=True,
        ) as client:
            t_before = time.monotonic()
            response = await client.get(url)
            t_after = time.monotonic()
            content = response.content
            t_done = time.monotonic()

        result.success = True
        result.status_code = response.status_code
        result.latency_connect = t_before - t_start
        result.latency_ttfb = t_after - t_before
        result.latency_total = t_done - t_start
        result.content_hash = hashlib.sha256(content).hexdigest()
        result.content_size = len(content)

        for header in CACHE_HEADERS:
            value = response.headers.get(header)
            if value:
                result.cache_headers[header] = value

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        result.latency_total = time.monotonic() - t_start
    finally:
        progress.advance(task_id)

    return result


async def direct_fetch(url: str, timeout: float = 30.0) -> ProxyResult:
    """Download directly (no proxy) as baseline."""
    result = ProxyResult(proxy="DIRECT", source="direct", country="--", isp="direct")

    t_start = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            verify=False,
            follow_redirects=True,
        ) as client:
            t_before = time.monotonic()
            response = await client.get(url)
            t_after = time.monotonic()
            content = response.content
            t_done = time.monotonic()

        result.success = True
        result.status_code = response.status_code
        result.latency_connect = t_before - t_start
        result.latency_ttfb = t_after - t_before
        result.latency_total = t_done - t_start
        result.content_hash = hashlib.sha256(content).hexdigest()
        result.content_size = len(content)

        for header in CACHE_HEADERS:
            value = response.headers.get(header)
            if value:
                result.cache_headers[header] = value

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        result.latency_total = time.monotonic() - t_start

    return result


def get_cache_status(r: ProxyResult) -> str:
    return (
        r.cache_headers.get("x-cache-status")
        or r.cache_headers.get("cf-cache-status")
        or r.cache_headers.get("x-cache")
        or r.cache_headers.get("x-proxy-cache")
        or ("-" if r.success else "")
    )


def print_results(results: list[ProxyResult], baseline: ProxyResult):
    """Render rich tables with all results."""
    console.print()
    console.rule("[bold blue]HLS Cache Test Results[/bold blue]")

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    # --- Successful results table ---
    table = Table(title=f"Successful Probes ({len(successful)} + baseline)", show_lines=True)
    table.add_column("#", style="dim", width=5)
    table.add_column("Src", width=4)
    table.add_column("CC", width=3)
    table.add_column("Proxy", style="cyan", max_width=22)
    table.add_column("ISP", max_width=28)
    table.add_column("HTTP", justify="center", width=5)
    table.add_column("TTFB", justify="right", width=8)
    table.add_column("Total", justify="right", width=8)
    table.add_column("Size", justify="right", width=10)
    table.add_column("SHA256", justify="center", width=14)
    table.add_column("Cache", width=14)
    table.add_column("Match", justify="center", width=6)

    if baseline.success:
        table.add_row(
            "BL", "--", baseline.country, "direct", "no proxy",
            f"[green]{baseline.status_code}[/green]",
            f"{baseline.latency_ttfb * 1000:.0f}ms",
            f"{baseline.latency_total * 1000:.0f}ms",
            f"{baseline.content_size:,}",
            baseline.content_hash[:12],
            get_cache_status(baseline),
            "[green]REF[/green]",
        )

    for i, r in enumerate(sorted(successful, key=lambda x: x.latency_total), 1):
        match_ok = r.content_hash == baseline.content_hash if baseline.success else None
        match_str = "[green]YES[/green]" if match_ok else "[red]NO[/red]" if match_ok is False else "[yellow]?[/yellow]"
        src = "RK" if r.source == "roosterkid" else "SX"

        table.add_row(
            str(i), src, r.country or "??", r.proxy.replace("http://", ""),
            (r.isp[:28] if r.isp else "-"),
            f"[green]{r.status_code}[/green]",
            f"{r.latency_ttfb * 1000:.0f}ms",
            f"{r.latency_total * 1000:.0f}ms",
            f"{r.content_size:,}",
            r.content_hash[:12],
            get_cache_status(r),
            match_str,
        )

    console.print(table)

    # --- Cache headers detail ---
    headers_found = [r for r in [baseline] + successful if r.cache_headers]
    if headers_found:
        console.print()
        detail = Table(title="Cache Headers Detail", show_lines=True)
        detail.add_column("Proxy", style="cyan", max_width=22)
        detail.add_column("CC", width=3)
        detail.add_column("Header", style="yellow", width=18)
        detail.add_column("Value", max_width=60)

        for r in headers_found:
            label = "direct" if r.proxy == "DIRECT" else r.proxy.replace("http://", "")
            for header, value in r.cache_headers.items():
                detail.add_row(label, r.country or "??", header, value)

        console.print(detail)

    # --- Failed summary (count by error type, not full list) ---
    if failed:
        console.print()
        error_types: dict[str, int] = {}
        for r in failed:
            err_type = r.error.split(":")[0] if r.error else "Unknown"
            error_types[err_type] = error_types.get(err_type, 0) + 1

        err_table = Table(title=f"Failed Probes Summary ({len(failed)} total)", show_lines=False)
        err_table.add_column("Error Type", style="red", width=35)
        err_table.add_column("Count", justify="right", width=8)
        err_table.add_column("% of Failed", justify="right", width=12)

        for err_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
            pct = count / len(failed) * 100
            err_table.add_row(err_type, str(count), f"{pct:.1f}%")

        console.print(err_table)

    # --- Summary ---
    all_probed = [baseline] + results if baseline.success else results
    all_success = [r for r in all_probed if r.success]

    console.print()
    console.rule("[bold]Summary[/bold]")
    console.print(f"  Total probes:       {len(all_probed)}")
    console.print(f"  Successful:         [green]{len(all_success)}[/green]")
    console.print(f"  Failed:             [red]{len(failed)}[/red]")
    console.print(f"  Success rate:       {len(all_success)/len(all_probed)*100:.1f}%")

    # Source breakdown
    rk_ok = sum(1 for r in successful if r.source == "roosterkid")
    sx_ok = sum(1 for r in successful if r.source == "speedx")
    rk_fail = sum(1 for r in failed if r.source == "roosterkid")
    sx_fail = sum(1 for r in failed if r.source == "speedx")
    console.print(f"  roosterkid:         [green]{rk_ok}[/green] ok / [red]{rk_fail}[/red] fail")
    console.print(f"  speedx:             [green]{sx_ok}[/green] ok / [red]{sx_fail}[/red] fail")

    if all_success:
        hashes = set(r.content_hash for r in all_success)

        console.print(f"  Unique hashes:      {len(hashes)}")

        if len(hashes) == 1:
            console.print(f"  Content integrity:  [bold green]ALL IDENTICAL[/bold green]  (sha256: {list(hashes)[0][:24]}...)")
        else:
            console.print(f"  Content integrity:  [bold red]MISMATCH DETECTED — {len(hashes)} different versions[/bold red]")
            for h in sorted(hashes):
                sources = [f"{r.country or '??'}:{r.proxy.replace('http://', '')}" for r in all_success if r.content_hash == h]
                console.print(f"    {h[:24]}... ({len(sources)} sources)")

        proxy_success = [r for r in successful]
        if proxy_success:
            p_lat = sorted([r.latency_total * 1000 for r in proxy_success])
            p_ttfb = sorted([r.latency_ttfb * 1000 for r in proxy_success])
            p50 = p_lat[len(p_lat) // 2]
            p95 = p_lat[int(len(p_lat) * 0.95)]
            p99 = p_lat[int(len(p_lat) * 0.99)]

            console.print(f"  Latency (total):    min={min(p_lat):.0f}ms  p50={p50:.0f}ms  p95={p95:.0f}ms  p99={p99:.0f}ms  max={max(p_lat):.0f}ms")
            console.print(f"  Latency (TTFB):     min={min(p_ttfb):.0f}ms  avg={sum(p_ttfb)/len(p_ttfb):.0f}ms  max={max(p_ttfb):.0f}ms")

        countries = {}
        for r in all_success:
            if r.proxy == "DIRECT":
                continue
            cc = r.country or "??"
            countries.setdefault(cc, []).append(r)
        if countries:
            console.print(f"  Countries reached:  {len(countries)} ({', '.join(sorted(countries))})")

    console.print()


async def main():
    parser = argparse.ArgumentParser(description="HLS Cache Consistency & Latency Tester")
    parser.add_argument("--url", default=TARGET_URL, help="URL of HLS segment to test")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout in seconds")
    parser.add_argument("--concurrency", type=int, default=50, help="Max concurrent proxy requests")
    parser.add_argument("--max-proxies", type=int, default=0, help="Limit number of proxies to test (0 = all)")
    args = parser.parse_args()

    console.rule("[bold blue]HLS Cache Consistency & Latency Tester[/bold blue]")
    console.print(f"  Target:      {args.url}")
    console.print(f"  Timeout:     {args.timeout}s")
    console.print(f"  Concurrency: {args.concurrency}")
    if args.max_proxies > 0:
        console.print(f"  Max proxies: {args.max_proxies}")
    console.print()

    # 1. Fetch proxy lists
    entries = await fetch_all_proxies()
    if not entries:
        console.print("[red]No proxies found. Exiting.[/red]")
        return

    if args.max_proxies > 0:
        entries = entries[:args.max_proxies]
        console.print(f"  Limited to first [bold]{len(entries)}[/bold] proxies")

    # 2. Direct baseline
    console.print()
    console.print("[yellow]Fetching baseline (direct, no proxy)...[/yellow]")
    baseline = await direct_fetch(args.url, timeout=args.timeout)
    if baseline.success:
        console.print(f"  [green]OK[/green] {baseline.status_code} | {baseline.content_size:,} bytes | {baseline.latency_total*1000:.0f}ms | sha256:{baseline.content_hash[:24]}...")
    else:
        console.print(f"  [red]FAILED: {baseline.error}[/red]")

    # 3. Test all proxies with progress bar
    console.print()
    sem = asyncio.Semaphore(args.concurrency)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("[dim]{task.fields[status]}[/dim]"),
        console=console,
    ) as progress:
        task_id = progress.add_task(
            f"Testing {len(entries)} proxies",
            total=len(entries),
            status="starting...",
        )

        done_count = {"ok": 0, "fail": 0}

        async def bounded_fetch(entry: ProxyEntry) -> ProxyResult:
            async with sem:
                result = await fetch_via_proxy(entry, args.url, args.timeout, progress, task_id)
                if result.success:
                    done_count["ok"] += 1
                else:
                    done_count["fail"] += 1
                progress.update(task_id, status=f"ok={done_count['ok']} fail={done_count['fail']}")
                return result

        tasks = [bounded_fetch(e) for e in entries]
        results = await asyncio.gather(*tasks)

    print_results(list(results), baseline)


if __name__ == "__main__":
    asyncio.run(main())
