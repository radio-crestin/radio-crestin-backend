"""log_monitor: nginx's session log (the listener analytics' source) is
handed over to a fresh file once it passes NGINX_SESSION_LOG_MAX_BYTES, so it
never grows in the container layer, and no line is lost or read twice. A
stand-in nginx appends numbered lines and reopens its log on USR1, like
nginx's master does."""

import importlib
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "live_streaming" / "scripts"
sys.path.insert(0, str(SCRIPTS))

LINES = 4000
FAKE_NGINX = """
import os, signal, sys, time
log, pid_file, lines = sys.argv[1], sys.argv[2], int(sys.argv[3])
out = open(log, "a", buffering=1)
def reopen(*_):
    global out
    out.close()
    out = open(log, "a", buffering=1)
signal.signal(signal.SIGUSR1, reopen)
with open(pid_file + ".tmp", "w") as handle:
    handle.write(str(os.getpid()))
os.replace(pid_file + ".tmp", pid_file)
for i in range(lines):
    out.write('1.2.3.4 - - [30/Oct/2026:14:46:00 +0000] "GET /aac/%d.ts?s=s%d HTTP/1.1" 200 1 "-" "ua" '
              'session_id="s%d" ref="-" real_ip="-" cf_ip="-"\\n' % (i, i, i))
    time.sleep(0.0005)
while True:  # like nginx: keeps running (and reopening on USR1)
    time.sleep(0.1)
"""


class RotateTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.log = os.path.join(self.dir.name, "session.log")
        self.pid_file = os.path.join(self.dir.name, "nginx.pid")
        env = {"NGINX_SESSION_LOG": self.log, "NGINX_PID_FILE": self.pid_file, "NGINX_SESSION_LOG_MAX_BYTES": "20000"}
        saved = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        self.addCleanup(lambda: [os.environ.pop(k) if v is None else os.environ.__setitem__(k, v) for k, v in saved.items()])
        import log_monitor
        self.lm = importlib.reload(log_monitor)

    def test_hands_over_the_log_without_losing_a_line(self):
        open(self.log, "w").close()  # nginx creates it at start; log_monitor tails from its end
        tail = threading.Thread(target=self.lm._tail_log, daemon=True)
        tail.start()
        time.sleep(1.5)
        writer = subprocess.Popen([sys.executable, "-c", FAKE_NGINX, self.log, self.pid_file, str(LINES)])
        self.addCleanup(writer.kill)
        deadline = time.monotonic() + 30
        while len(self.lm._batch_queue) < LINES and time.monotonic() < deadline:
            time.sleep(0.2)
        self.lm._running = False
        tail.join(timeout=5)
        sessions = [event["anonymous_session_id"] for event in self.lm._batch_queue]
        self.assertEqual(sessions, ["s%d" % i for i in range(LINES)])
        self.assertLess(os.path.getsize(self.log), self.lm.LOG_MAX_BYTES)
        self.assertFalse(os.path.exists(self.log + ".old"))

    def test_keeps_the_log_when_nginx_cannot_be_told(self):
        with open(self.log, "w") as handle:
            handle.write("line 0\n")
        with self.assertRaises(OSError):
            self.lm._rotate(0)  # no pid file
        self.assertTrue(os.path.exists(self.log))
        self.assertFalse(os.path.exists(self.log + ".old"))


if __name__ == "__main__":
    unittest.main()
