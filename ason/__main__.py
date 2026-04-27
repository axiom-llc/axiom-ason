"""ASON CLI entry point."""
from __future__ import annotations
import json
import os
import sys


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "submit":
        from ason.schema import ASONRequest
        from ason.executor import ASONExecutor
        if len(sys.argv) < 3:
            print("usage: ason submit <json_file_or_-> [--apex-url URL]", file=sys.stderr)
            sys.exit(1)
        src = sys.argv[2]
        raw = sys.stdin.read() if src == "-" else open(src).read()
        apex_url = "http://127.0.0.1:8080"
        if "--apex-url" in sys.argv:
            apex_url = sys.argv[sys.argv.index("--apex-url") + 1]
        req = ASONRequest.model_validate(json.loads(raw))
        ex = ASONExecutor(apex_url=apex_url, api_key=os.environ.get("APEX_API_KEY"))
        result = ex.submit(req)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("accepted") else 1)

    print("ASON 0.1.0")
    print("subcommands: submit")
    sys.exit(0)


if __name__ == "__main__":
    main()
