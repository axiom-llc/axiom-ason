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

        payload = json.dumps({"task": _plan_to_task(req)}).encode()
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


def _plan_to_task(req: ASONRequest) -> str:
    """Serialize ASONRequest to a task string apex run() can execute."""
    steps = [{"tool": s.tool, "args": s.args} for s in req.plan.steps]
    policy = req.policy.model_dump()
    return json.dumps({"ason_plan": steps, "ason_policy": policy})
