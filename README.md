# axiom-ason
**v0.1.0** · ASON — Autonomous Security Optimization Network · Pre-execution policy enforcement layer for APEX · Python 3.11+ · MIT

## System Boundary
- **APEX** — execution / control plane
- **ASON** — policy enforcement / decision layer
- **RAG** — grounding / retrieval substrate

## What ASON Does
ASON validates and governs plan submission to APEX before any execution begins. Plans that violate policy are rejected at the API boundary — not at runtime.

Enforcement at validation time:
- `len(plan.steps) ≤ policy.max_steps`
- No step invokes a tool in the blocked set (`shell` by default)
- If `allowed_tools` is non-empty, every step's tool must appear in it
- `blast_radius` classification blocks tools by impact envelope:
  - `none` — blocks `write_file`, `delete_file`, `http_get`, `http_post` (read-only)
  - `local` — blocks `http_get`, `http_post` (filesystem only)
  - `network` — no additional blocks

## APEX Contract
ASON submits schema-valid plans to APEX:

```json
{
  "plan": { "...schema-valid APEX plan..." },
  "policy": {
    "max_steps": 16,
    "allowed_tools": ["read_file", "http_get"],
    "blast_radius": "local|network|none",
    "rollback_on_failure": true
  }
}
```

Validated plans are submitted to `POST /run` via the APEX HTTP API. Rejected plans never reach the executor.

## Rollback
On execution failure, ASON generates a compensating plan by traversing the run's event log in reverse and applying the reversal map (`write_file → delete_file`). `shell` invocations are flagged as non-reversible. The rollback plan is itself policy-validated before submission.

## Test Suite
40 tests, 0 failures across 6 adversarial categories:
- CAT1: blast_radius rejection
- CAT2: max_steps violation
- CAT3: tool allowlist enforcement
- CAT4: malformed plan (schema-level)
- CAT5: timeout elicitation
- CAT6: concurrent isolation

```bash
python -m pytest ason/tests/ -q
```

## Usage
```bash
pip install axiom-ason
ason submit plan.json --apex-url http://127.0.0.1:8080
```

## License
MIT — [AXIOM LLC](https://axiom-llc.github.io)
