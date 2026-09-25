#!/usr/bin/env python3
"""DroidPlay adapter entrypoint for the Omarchy plugin."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from droidplay_adapter import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
