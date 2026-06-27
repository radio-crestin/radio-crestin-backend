"""
Regression test for PostHog issue 019df0f0:
"RuntimeError: Never call result.get() within a task!"

The `automated_backup` Celery task must NOT block on another task's result via
`.apply_async(...).get()` or `.delay(...).get()` — waiting on a subtask from
inside a task can deadlock the worker pool and raises that RuntimeError.

This is a static (AST) check, so it runs with the stdlib only — no Django or
Celery import required (the backend app can't be imported without a configured
Django environment). It lives in backend/tests/ (outside the `superapp` package)
so pytest imports it standalone:

    python3 -m pytest backend/tests/test_backup_no_sync_subtask.py
"""

import ast
from pathlib import Path

BACKUP_PY = (
    Path(__file__).resolve().parents[1]
    / "superapp" / "apps" / "backups" / "tasks" / "backup.py"
)


def _automated_backup_node(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "automated_backup":
            return node
    return None


def test_backup_py_parses_and_defines_automated_backup():
    assert BACKUP_PY.exists(), f"backup.py not found at {BACKUP_PY}"
    tree = ast.parse(BACKUP_PY.read_text())
    assert _automated_backup_node(tree) is not None


def test_automated_backup_does_not_block_on_a_subtask_result():
    tree = ast.parse(BACKUP_PY.read_text())
    fn = _automated_backup_node(tree)
    assert fn is not None, "automated_backup task not found"

    offenders = []
    for node in ast.walk(fn):
        # Match  <expr>.apply_async(...).get(...)  or  <expr>.delay(...).get(...)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
        ):
            inner = node.func.value
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr in ("apply_async", "delay")
            ):
                offenders.append(ast.dump(node))

    assert not offenders, (
        "automated_backup blocks on a subtask result (deadlock risk / "
        "RuntimeError 'Never call result.get() within a task'): " + repr(offenders)
    )
