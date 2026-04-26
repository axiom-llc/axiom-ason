# axiom-aoson

**v0.1.0** · AOSON — Autonomous Security Optimization Network · Decision and optimization engine for APEX · Python 3.11+ · MIT

## System Boundary

- **APEX** — execution / control plane
- **AOSON** — decision / optimization engine
- **RAG** — grounding / retrieval substrate

## APEX Contract

AOSON submits schema-valid plans to APEX:

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

## License

MIT — [AXIOM LLC](https://axiom-llc.github.io)
