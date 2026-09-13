# AXIOM ASON

ASON is AXIOM's pre-execution policy enforcement layer for APEX. Version
`0.2.0` is current source and requires Python 3.11+ plus APEX 3.1.0 or newer.
It validates caller-supplied plans; it is not a natural-language planner and
does not independently execute tools.

## System boundary

- **APEX** — execution/runtime.
- **ASON** — pre-execution policy enforcement.
- **RAG** — retrieval/storage HTTP service and library.

## Policy enforcement
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
Supply an ASON request to `ASONExecutor.submit` or `ason submit`:

```json
{
  "plan": {"steps": [{"tool": "read_file", "args": {"path": "/tmp/input.txt"}}]},
  "policy": {
    "max_steps": 16,
    "allowed_tools": ["read_file"],
    "blast_radius": "local",
    "rollback_on_failure": false
  }
}
```

ASON validates every step against the supplied policy before making an HTTP
request. It then sends this distinct APEX request body to `POST /run`, with
`Content-Type: application/json` and `X-Apex-Key` when configured:

```json
{
  "plan": {
    "goal": "Execute ASON-approved plan",
    "steps": [
      {"type": "tool", "name": "read_file", "args": {"path": "/tmp/input.txt"}},
      {"type": "halt", "reason": "ASON-approved plan complete"}
    ]
  }
}
```

Tool order, names, and JSON arguments are preserved. The adapter adds only the
fixed goal, tool-step tags, and terminal halt; it sends neither `task` nor
`policy`. APEX's separate `{"task": ...}` interface retains planning for direct
callers, but ASON never uses it. ASON governs the submitted policy; it does not
construct a natural-language plan or transmit a durable approval identity.

Requires APEX 3.1.0 or newer. ASON translates approved steps into APEX tool
steps followed by a halt and submits `{"plan": ...}` to `POST /run`. APEX validates
the entire plan against its active registry and executes it without replanning.
Its 32-step ceiling includes the final halt (at most 31 tool calls). Schema-invalid
or unavailable tools are rejected by APEX before execution. Unclassified custom
tools are rejected by ASON; deployed tool implementations must match their stated
classification. Policy enforcement assumes callers cannot bypass ASON using the
APEX API key directly and that trusted application code chooses the policy.
APEX schema validation is not a second policy engine.

`accepted` reports ASON policy approval. Check `error` and
`apex_response.exit_code` for execution success. The CLI exits nonzero on policy,
transport, APEX validation, or execution failure.

The integration suite checks equality of the submitted plan, APEX response,
recorded plan, and executed tool arguments with replanning disabled. It also
checks that later policy violations prevent submission and later APEX schema
errors prevent earlier effects. This establishes the current submission boundary;
recorded-plan replay is also checked with replanning disabled, and dry/simulate
replay does not execute tools. Live replay uses APEX's durable same-run recovery:
completed steps reuse recorded results, while ambiguous dispatch states block
further execution. ASON does not durably bind policy-approval identity to that
recovery record; these checks therefore do not establish durable approval
binding or a stronger external-effect guarantee.

## Rollback
The optional `generate_rollback` helper inspects run events in reverse order. It returns `None` for `write_file` and emits explicit manual-review guidance: automatic compensation is unavailable until compensation authority, durable preimage, concurrency/version safety, and outcome reconciliation contracts are defined. It never generates `delete_file` as an inverse of `write_file`. `shell` invocations retain their manual-review warning; other operations have no automatic inverse. `None` means no rollback plan is available, not that compensation succeeded. The helper is not invoked automatically by the executor; `rollback_on_failure` currently does not trigger automatic rollback.

## Installation

The current APEX/RAG architecture is unreleased. Do not use a bare
`pip install axiom-ason` as a path to this integrated source state. For local
development, use matching sibling checkouts:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install ../axiom-rag
python -m pip install -e ../axiom-apex
python -m pip install -e .
```

This does not create or imply a published APEX/RAG artifact. See the owning
APEX and RAG release documentation for their separate authorization gates.

## Validation
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

The current CI workflow still references the `RAG_DEPLOY_KEY` Actions secret
for its `axiom-rag` checkout and uses `persist-credentials: false`. All AXIOM
repositories are currently public, so that key is no longer a repository-
visibility requirement; removing the workflow reference and credential is a
separate validated cleanup task. CI records dependency revisions and verifies
that checkout credentials are removed before package build and test execution.

## Usage
```bash
ason submit plan.json --apex-url http://127.0.0.1:8080
```

## Related AXIOM components

- [APEX](https://github.com/axiom-llc/axiom-apex) — execution/runtime.
- [RAG](https://github.com/axiom-llc/axiom-rag) — required by current APEX source.
- [Infra](https://github.com/axiom-llc/axiom-infra) — local portfolio integration.

## License

No license file is currently present in this repository; confirm distribution
terms before reuse.
