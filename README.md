# axiom-ason
**v0.2.0** · ASON — Autonomous Security Optimization Network · Pre-execution policy enforcement layer for APEX · Python 3.11+ · MIT

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
  - `none` — blocks filesystem/memory writes and network tools (read-only)
  - `local` — blocks `http_get`, `http_post`, and `rag_multi_query` (local effects only)
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

Requires APEX 3.1.0 or newer. ASON translates approved steps into APEX tool
steps followed by a halt and submits `{"plan": ...}` to `POST /run`. APEX validates
the entire plan against its active registry and executes it without replanning.
Its 32-step ceiling includes the final halt (at most 31 tool calls). Schema-invalid
or unavailable tools are rejected by APEX before execution. Unclassified custom
tools are rejected by ASON; deployed tool implementations must match their stated
classification. Policy enforcement assumes callers cannot bypass ASON using the
APEX API key directly.

`accepted` reports ASON policy approval. Check `error` and
`apex_response.exit_code` for execution success. The CLI exits nonzero on policy,
transport, APEX validation, or execution failure.

## Rollback
The optional `generate_rollback` helper generates a compensating plan by traversing the run's event log in reverse and applying the reversal map (`write_file → delete_file`). `shell` invocations are flagged as non-reversible. The helper is not invoked automatically by the executor; `rollback_on_failure` currently does not trigger automatic rollback. Generated reversal plans require review and policy validation before submission; deleting a written file cannot restore overwritten contents.

## Test Suite
Offline tests cover policy, exact APEX execution, and failure propagation across these categories:
- CAT1: blast_radius rejection
- CAT2: max_steps violation
- CAT3: tool allowlist enforcement
- CAT4: malformed plan (schema-level)
- CAT5: timeout elicitation
- CAT6: concurrent isolation

```bash
python -m pytest ason/tests/ -q
```

Component CI builds matching wheels from RAG and APEX `main` plus the ASON
revision under test, then installs them together using their package metadata.
It runs the complete suite outside the checkouts with `--import-mode=importlib`
so ASON exercises the installed APEX runtime. Full portfolio/container checks
remain in `axiom-infra`.

Private RAG checkout uses this repository's `RAG_DEPLOY_KEY` Actions secret,
backed by a dedicated read-only deploy key on `axiom-rag`. All checkouts remove
credentials before builds or tests run. Fork pull requests cannot access this
secret; validate those changes from a reviewed branch in this repository.
To rotate the key, add a new read-only RAG deploy key, replace this secret, verify
CI, then remove the old key. Delete the deploy key to revoke access immediately;
these keys do not expire automatically. Never commit or log private key material.

## Usage
```bash
pip install axiom-ason
ason submit plan.json --apex-url http://127.0.0.1:8080
```

## License
MIT — [AXIOM LLC](https://axiom-llc.github.io)
