"""Local demo adapter used only by demo/index.html.

It returns deterministic illustrative state and never touches DroidPlay, ADB,
Hermes, or the network.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from droidplay_adapter import AdapterError, build_prompt, run_hermes, validate_action  # noqa: E402


DEMO_STATUS = {
    "status": "running",
    "service": "droidplay-adapter",
    "receiver": "Living Room",
    "error": "",
    "healthy": True,
    "errors": [],
}


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    try:
        action = validate_action(action, sys.argv[2] if len(sys.argv) > 2 else None)
        if action == "status":
            print(json.dumps(DEMO_STATUS, sort_keys=True))
            return 0
        if action == "ask-hermes":
            question = sys.argv[2] if len(sys.argv) > 2 else ""
            context = json.loads(sys.argv[3]) if len(sys.argv) > 3 else DEMO_STATUS
            if os.environ.get("DROIDPLAY_DEMO_REAL_HERMES") == "1":
                print(run_hermes(prompt=build_prompt(context, question)))
            else:
                print("Demo advice: prefer the reversible move, refresh status, and keep the next action behind human review.")
            return 0
        raise AdapterError("Control actions are disabled in the demo")
    except (AdapterError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
