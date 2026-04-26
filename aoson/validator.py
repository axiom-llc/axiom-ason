"""AOSON plan validator — enforces policy against APEX contract."""
from __future__ import annotations
from .schema import AOSONRequest, AOSONResult

_BLOCKED_TOOLS = {"shell"}  # tools never permitted regardless of policy


def validate(req: AOSONRequest) -> AOSONResult:
    violations: list[str] = []

    if len(req.plan.steps) > req.policy.max_steps:
        violations.append(
            f"plan has {len(req.plan.steps)} steps; policy max_steps={req.policy.max_steps}"
        )

    allowed = set(req.policy.allowed_tools)
    for i, step in enumerate(req.plan.steps):
        if step.tool in _BLOCKED_TOOLS:
            violations.append(f"step {i}: tool '{step.tool}' is unconditionally blocked")
        elif allowed and step.tool not in allowed:
            violations.append(f"step {i}: tool '{step.tool}' not in allowed_tools")

    if violations:
        return AOSONResult(accepted=False, violations=violations, risk_level="high", summary="policy violations detected")

    return AOSONResult(accepted=True, risk_level="none", summary="plan accepted")
