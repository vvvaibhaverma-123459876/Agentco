from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runtime import cancel_attempt, execute_capability_request, get_attempt


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m agentco_capability")
    sub = parser.add_subparsers(dest="command", required=True)
    execute = sub.add_parser("execute")
    execute.add_argument("--request", required=True, type=Path)
    get = sub.add_parser("get")
    get.add_argument("--attempt-id", required=True)
    cancel = sub.add_parser("cancel")
    cancel.add_argument("--attempt-id", required=True)
    args = parser.parse_args()

    try:
        if args.command == "execute":
            response = execute_capability_request(json.loads(args.request.read_text()))
        elif args.command == "get":
            response = get_attempt(args.attempt_id)
            if response is None:
                print(json.dumps({"status": "unsupported", "error": "attempt not found"}, sort_keys=True))
                return 2
        else:
            response = cancel_attempt(args.attempt_id)
        print(json.dumps(response, indent=2, sort_keys=True))
        return 0 if response.get("status") in {"completed", "cancelled"} else 2
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
