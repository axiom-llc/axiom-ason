"""Tests for AOSON executor — offline (no apex serve required)."""
import json
import unittest.mock as mock
import pytest
from aoson.schema import AOSONRequest, ApexPlan, ApexPlanStep, Policy
from aoson.executor import AOSONExecutor, _plan_to_task


def _req(steps, policy=None):
    p = ApexPlan(steps=[ApexPlanStep(tool=t, args=a) for t, a in steps])
    return AOSONRequest(plan=p, policy=policy or Policy())


def test_rejected_plan_never_submits():
    ex = AOSONExecutor()
    req = _req([("shell", {"cmd": "ls"})])
    with mock.patch("urllib.request.urlopen") as m:
        result = ex.submit(req)
    m.assert_not_called()
    assert not result["accepted"]


def test_accepted_plan_submits():
    ex = AOSONExecutor(api_key="test-key")
    req = _req([("read_file", {"path": "/tmp/x"})])
    fake_resp = mock.MagicMock()
    fake_resp.read.return_value = json.dumps({"run_id": 1, "exit_code": 0}).encode()
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = mock.MagicMock(return_value=False)
    with mock.patch("urllib.request.urlopen", return_value=fake_resp):
        result = ex.submit(req)
    assert result["accepted"]
    assert result["apex_response"]["run_id"] == 1


def test_plan_to_task_serializes():
    req = _req([("read_file", {"path": "/tmp/x"})])
    t = _plan_to_task(req)
    d = json.loads(t)
    assert d["aoson_plan"][0]["tool"] == "read_file"
    assert "aoson_policy" in d
