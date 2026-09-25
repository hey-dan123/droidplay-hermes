"""Command-line entry point for the RTS helper.

This launcher intentionally stops before opening an input device or spawning
ydotoold. The state/policy layer is usable now; live input requires the explicit
operator flow documented in rts/README.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rts_control import build_scrcpy_args, default_profile, load_profiles


def main() -> int:
    parser = argparse.ArgumentParser(description="DroidPlay RTS control helper")
    parser.add_argument("action", choices=("show-config", "launch-args"))
    parser.add_argument("--profile", default="default")
    parser.add_argument("--config", type=Path, default=Path.home() / ".config/droidplay-rts/profiles.json")
    args = parser.parse_args()

    if args.action == "show-config":
        if args.config.exists():
            print(json.dumps(load_profiles(args.config), indent=2, sort_keys=True))
        else:
            print(json.dumps({"default": default_profile()}, indent=2, sort_keys=True))
        return 0

    profiles = load_profiles(args.config) if args.config.exists() else {"default": default_profile()}
    profile = profiles.get(args.profile)
    if profile is None:
        parser.error(f"unknown profile: {args.profile}")
    serial = str(profile.get("targetSerial", "")).strip()
    if not serial:
        parser.error("targetSerial is empty; configure an authorized ADB device first")
    print(json.dumps(build_scrcpy_args(serial, profile), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
