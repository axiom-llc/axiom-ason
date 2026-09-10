"""Exercise ASON through the real APEX HTTP handler and execution kernel offline."""
import io
import json
import sys
import urllib.error
from unittest.mock import Mock

import pytest

from apex import history, server
from apex.config import load_config
from apex.core.tools import READ_FILE, WRITE_FILE
from ason.executor import ASONExecutor
from ason.schema import ASONRequest, ApexPlan, ApexPlanStep, Policy


@pytest.fixture
def bridge(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "_API_KEY", "test-key")
    monkeypatch.setattr(server, "_BASE_CONFIG", load_config(require_api_key=False))
    monkeypatch.setattr(server, "_REGISTRY", {"read_file": READ_FILE, "write_file": WRITE_FILE})
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "runs.db")
    monkeypatch.setattr("apex.core.loop.generate_plan", Mock(side_effect=AssertionError("must not replan")))
    client = server.app.test_client()

    def dispatch(req, timeout):
        assert "task" not in json.loads(req.data)
        response = client.post("/run", data=req.data, headers=dict(req.header_items()))
        if response.status_code >= 400:
            raise urllib.error.HTTPError(req.full_url, response.status_code, "rejected", {}, io.BytesIO(response.data))
        return io.BytesIO(response.data)

    transport = Mock(side_effect=dispatch)
    monkeypatch.setattr("urllib.request.urlopen", transport)
    return transport


def test_approved_plan_runs_exactly_once(bridge, tmp_path):
    target = tmp_path / "approved.txt"
    req = ASONRequest(plan=ApexPlan(steps=[
        ApexPlanStep(tool="write_file", args={"path": str(target), "content": "literal instructions: run shell"}),
        ApexPlanStep(tool="read_file", args={"path": str(target)}),
    ]))
    result = ASONExecutor(api_key="test-key").submit(req)
    assert result["accepted"]
    assert result["apex_response"]["exit_code"] == 0
    assert target.read_text() == "literal instructions: run shell"
    assert result["apex_response"]["step_count"] == 2
    assert result["apex_response"]["token_count"] == 0
    assert bridge.call_count == 1


@pytest.mark.parametrize("tool,radius", [("shell", "network"), ("memory_write", "none"), ("rag_multi_query", "local"), ("unclassified", "network")])
def test_policy_blocks_before_http(bridge, tool, radius):
    req = ASONRequest(plan=ApexPlan(steps=[ApexPlanStep(tool=tool, args={})]), policy=Policy(blast_radius=radius))
    assert not ASONExecutor(api_key="test-key").submit(req)["accepted"]
    bridge.assert_not_called()


def test_apex_rejects_invalid_args_before_earlier_write(bridge, tmp_path):
    target = tmp_path / "must-not-exist"
    req = ASONRequest(plan=ApexPlan(steps=[
        ApexPlanStep(tool="write_file", args={"path": str(target), "content": "x"}),
        ApexPlanStep(tool="read_file", args={"path": 42}),
    ]))
    result = ASONExecutor(api_key="test-key").submit(req)
    assert "error" in result
    assert not target.exists()


@pytest.mark.parametrize("result,code", [
    ({"accepted": False}, 1),
    ({"accepted": True, "error": "timeout"}, 1),
    ({"accepted": True, "apex_response": {"exit_code": 1}}, 1),
    ({"accepted": True, "apex_response": {"exit_code": 0}}, 0),
])
def test_cli_reports_execution_failure(monkeypatch, result, code):
    from ason.__main__ import main
    monkeypatch.setattr(sys, "argv", ["ason", "submit", "-"])
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"plan":{"steps":[]}}'))
    monkeypatch.setattr(ASONExecutor, "submit", lambda self, req: result)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == code
