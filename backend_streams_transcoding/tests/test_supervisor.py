"""supervisor.sh: ffmpeg_loop keeps the real exit code, backs off
2 → 20 s and resets after a stable run; supervise restarts helpers; SIGTERM
stops a loop together with its child. Runs the real shell functions with
start_ffmpeg / backoff_sleep / report_event stubbed."""

import os
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "live_streaming" / "scripts"
SUPERVISOR = SCRIPTS / "supervisor.sh"

# Records each backoff instead of sleeping; ends the script after `limit`.
STUBS = """
set -euo pipefail
. "{supervisor}"
sleeps=0
report_event() {{ echo "event $*"; }}
backoff_sleep() {{
    echo "sleep $1"
    sleeps=$((sleeps + 1))
    if [ "$sleeps" -ge {limit} ]; then exit 0; fi
}}
"""


def run_bash(script, limit=6, timeout=30):
    return subprocess.run(
        ["bash", "-c", STUBS.format(supervisor=SUPERVISOR, limit=limit)
         + script],
        capture_output=True, text=True, timeout=timeout, check=True,
    ).stdout


def sleeps(out):
    return [int(line.split()[1]) for line in out.splitlines()
            if line.startswith("sleep ")]


class FfmpegLoopTests(unittest.TestCase):
    def test_real_exit_code_and_backoff(self):
        out = run_bash("""
FFMPEG_STABLE_RUN=1000
start_ffmpeg() { (exit 3) & FFMPEG_PID=$!; }
ffmpeg_loop
""")
        self.assertEqual(sleeps(out), [2, 4, 8, 16, 20, 20])
        # `ran` has whole-second resolution (date +%s): the instant run
        # reads 1 s when it straddles a second boundary.
        self.assertRegex(out, r"ffmpeg exited \(code=3, ran=[01]s, "
                              r"restart_count=1\); retrying in 2s")
        self.assertIn("event ffmpeg_exit --prop exit_code=3", out)

    def test_backoff_resets_after_a_stable_run(self):
        out = run_bash("""
FFMPEG_STABLE_RUN=1
runs=0
start_ffmpeg() {
    runs=$((runs + 1))
    if [ "$runs" -eq 4 ]; then (sleep 1.2) & else (exit 1) & fi
    FFMPEG_PID=$!
}
ffmpeg_loop
""", limit=5)
        self.assertEqual(sleeps(out), [2, 4, 8, 2, 4])
        self.assertIn("code=0", out)

    def test_term_stops_the_loop_and_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "ffmpeg.pid"
            proc = subprocess.Popen(["bash", "-c", f"""
set -euo pipefail
. "{SUPERVISOR}"
report_event() {{ :; }}
start_ffmpeg() {{ sleep 30 & FFMPEG_PID=$!; echo $FFMPEG_PID > "{pid_file}"; }}
ffmpeg_loop
"""])
            child = _wait_for_pid(pid_file)
            proc.send_signal(signal.SIGTERM)
            self.assertEqual(proc.wait(timeout=5), 0)
            _assert_exits(self, child)


class SuperviseTests(unittest.TestCase):
    def test_helper_is_restarted_with_its_exit_code(self):
        out = run_bash("""
FFMPEG_STABLE_RUN=1000
supervise rewriter sh -c 'exit 7'
""", limit=3)
        self.assertEqual(sleeps(out), [2, 4, 8])
        self.assertIn("supervise: rewriter exited (code=7, ran=0s); "
                      "restarting in 2s", out)
        self.assertIn("event helper_exit --prop helper=rewriter "
                      "--prop exit_code=7", out)

    def test_term_stops_supervise_and_its_helper(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "helper.pid"
            proc = subprocess.Popen(["bash", "-c", f"""
set -euo pipefail
. "{SUPERVISOR}"
report_event() {{ :; }}
supervise sleeper sh -c 'echo $$ > "{pid_file}"; exec sleep 30'
"""])
            child = _wait_for_pid(pid_file)
            proc.send_signal(signal.SIGTERM)
            self.assertEqual(proc.wait(timeout=5), 0)
            _assert_exits(self, child)


class ShellSyntaxTests(unittest.TestCase):
    def test_scripts_parse(self):
        for name in ("entrypoint.sh", "supervisor.sh"):
            subprocess.run(["bash", "-n", str(SCRIPTS / name)], check=True)
        subprocess.run(["sh", "-n", str(SCRIPTS / "cleanup.sh")], check=True)

    def test_next_retry_delay(self):
        out = subprocess.run(
            ["bash", "-c", f'. "{SUPERVISOR}"; next_retry_delay 8 20; '
                           f'next_retry_delay 16 20'],
            capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(out, ["16", "20"])


def _wait_for_pid(path, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists() and path.read_text().strip():
            return int(path.read_text())
        time.sleep(0.05)
    raise AssertionError(f"{path} never written")


def _assert_exits(test, pid, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    os.kill(pid, signal.SIGKILL)
    test.fail(f"child {pid} survived SIGTERM of its supervisor")


if __name__ == "__main__":
    unittest.main()
