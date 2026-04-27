"""Tests for ASON rollback handler."""
import json
import sqlite3
import tempfile
from pathlib import Path
import pytest
from ason.schema import Policy
from ason.rollback import generate_rollback


def _make_db(events: list[tuple]) -> Path:
    """Create a temp runs.db with given (run_id, step, tool, args_json) rows."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = Path(tmp.name)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE events (id INTEGER PRIMARY KEY, run_id TEXT, step INTEGER, tool TEXT, args_json TEXT)"
        )
        conn.executemany(
            "INSERT INTO events (run_id, step, tool, args_json) VALUES (?,?,?,?)",
            events,
        )
    return path


def test_no_db_returns_none(tmp_path):
    assert generate_rollback("run-1", db_path=tmp_path / "nonexistent.db") is None


def test_unknown_run_id_returns_none():
    db = _make_db([("run-1", 0, "read_file", json.dumps({"path": "/tmp/x"}))])
    assert generate_rollback("run-99", db_path=db) is None


def test_no_reversible_steps_returns_none():
    db = _make_db([("run-1", 0, "read_file", json.dumps({"path": "/tmp/x"}))])
    assert generate_rollback("run-1", db_path=db) is None


def test_write_file_generates_delete():
    db = _make_db([("run-1", 0, "write_file", json.dumps({"path": "/tmp/out.txt"}))])
    req = generate_rollback("run-1", db_path=db)
    assert req is not None
    assert len(req.plan.steps) == 1
    step = req.plan.steps[0]
    assert step.tool == "delete_file"
    assert step.args["path"] == "/tmp/out.txt"


def test_rollback_policy():
    db = _make_db([("run-1", 0, "write_file", json.dumps({"path": "/tmp/f"}))])
    req = generate_rollback("run-1", db_path=db)
    assert req.policy.blast_radius == "local"
    assert req.policy.rollback_on_failure is False


def test_steps_reversed_order():
    db = _make_db([
        ("run-1", 0, "write_file", json.dumps({"path": "/tmp/a"})),
        ("run-1", 1, "write_file", json.dumps({"path": "/tmp/b"})),
    ])
    req = generate_rollback("run-1", db_path=db)
    paths = [s.args["path"] for s in req.plan.steps]
    assert paths == ["/tmp/b", "/tmp/a"]


def test_write_file_missing_path_skipped(capsys):
    db = _make_db([("run-1", 0, "write_file", json.dumps({}))])
    req = generate_rollback("run-1", db_path=db)
    assert req is None
    assert "skipped" in capsys.readouterr().err


def test_shell_step_flagged_not_reversed(capsys):
    db = _make_db([("run-1", 0, "shell", json.dumps({"cmd": "rm -rf /tmp/x"}))])
    req = generate_rollback("run-1", db_path=db)
    assert req is None
    assert "manual review" in capsys.readouterr().err
