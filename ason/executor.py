"""ASON executor — submits validated APEX plans via apex serve HTTP API."""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from .schema import ASONRequest, ASONResult
from .validator import validate


class ASONExecutor:
    def __init__(self, apex_url: str = "http://127.0.0.1:8080", api_key: str | None = None):
        self.apex_url = apex_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-Apex-Key"] = self.api_key
        return h

    def submit(self, req: ASONRequest) -> dict:
        result: ASONResult = validate(req)
        if not result.accepted:
            return {"accepted": False, "violations": result.violations, "apex_response": None}

        payload = json.dumps({"plan": _apex_plan(req)}).encode()
        http_req = urllib.request.Request(
            f"{self.apex_url}/run",
            data=payload,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_req, timeout=310) as resp:
                apex_response = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return {"accepted": True, "violations": [], "apex_response": None, "error": str(exc)}
        except Exception as exc:
            return {"accepted": True, "violations": [], "apex_response": None, "error": str(exc)}

        return {"accepted": True, "violations": [], "apex_response": apex_response}


def _apex_plan(req: ASONRequest) -> dict:
    """Translate the approved steps to APEX's exact-execution representation."""
    return {
        "goal": "Execute ASON-approved plan",
        "steps": [
            {"type": "tool", "name": step.tool, "args": step.args}
            for step in req.plan.steps
        ] + [{"type": "halt", "reason": "ASON-approved plan complete"}],
    }
