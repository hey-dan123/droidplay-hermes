"""Safe RTS control policy for a focused scrcpy kiosk on Omarchy.

Pure state-machine and validation logic lives here. The eventual input bridge
will listen to focused-session keyboard events and emit allowlisted Android
pointer gestures. No gesture is emitted by this module during tests.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

ACTIVE_KEYS = frozenset({"W", "A", "S", "D", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"})
DEFAULT_PAN_INVERT = True
DEFAULT_PAN_SPEED = 1.0
DEFAULT_ZOOM_SPEED = 0.35
DEFAULT_TICK_MS = 12
DEFAULT_RELEASE_MS = 700
DEFAULT_MARGIN = 60

_KEY_ALIASES = {
    "w": "W",
    "a": "A",
    "s": "S",
    "d": "D",
    "up": "ArrowUp",
    "arrowup": "ArrowUp",
    "down": "ArrowDown",
    "arrowdown": "ArrowDown",
    "left": "ArrowLeft",
    "arrowleft": "ArrowLeft",
    "right": "ArrowRight",
    "arrowright": "ArrowRight",
}

_PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")
_DISPLAY_RE = re.compile(r"^\d{3,5}x\d{3,5}(?:/\d{2,4})?$")
_SERIAL_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

_CONFIG_KEYS = frozenset(
    {
        "panSpeed",
        "panInvert",
        "zoomSpeed",
        "tickMs",
        "releaseMs",
        "margin",
        "targetSerial",
        "package",
        "displaySize",
        "noAudio",
        "shortcutMod",
    }
)
_PROFILE_KEYS = frozenset(_CONFIG_KEYS | {"name"})


@dataclass(frozen=True)
class KeyEvent:
    """Normalized key transition from a compositor-native event source."""

    name: str
    down: bool
    timestamp: float


@dataclass
class GestureState:
    """Pure held-key state; it does not own timers or input devices."""

    pan_invert: bool = DEFAULT_PAN_INVERT
    held: set[str] = field(default_factory=set)
    dx: float = 0.0
    dy: float = 0.0
    panning: bool = False
    last_event_at: float | None = None

    def _recompute(self, timestamp: float) -> None:
        x = 0.0
        y = 0.0
        if "A" in self.held or "ArrowLeft" in self.held:
            x -= 1.0
        if "D" in self.held or "ArrowRight" in self.held:
            x += 1.0
        if "W" in self.held or "ArrowUp" in self.held:
            y -= 1.0
        if "S" in self.held or "ArrowDown" in self.held:
            y += 1.0
        if x and y:
            scale = 1.0 / math.sqrt(2.0)
            x *= scale
            y *= scale
        if self.pan_invert:
            x = -x
            y = -y
        self.dx = x
        self.dy = y
        self.panning = bool(x or y)
        self.last_event_at = timestamp


def parse_key_name(value: str) -> str:
    """Return an allowlisted normalized key name or raise ValueError."""

    try:
        normalized = _KEY_ALIASES[str(value).strip().lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported control key: {value!r}") from exc
    return normalized


def apply_key_event(state: GestureState, event: KeyEvent) -> None:
    """Apply a key transition and recompute the normalized pan vector."""

    name = parse_key_name(event.name)
    if event.down:
        state.held.add(name)
    else:
        state.held.discard(name)
    state._recompute(event.timestamp)


def apply_key_event_safe(state: GestureState, event: KeyEvent) -> bool:
    """Apply only control keys; unrelated desktop keys pass through unchanged."""

    try:
        name = parse_key_name(event.name)
    except ValueError:
        return False
    apply_key_event(state, KeyEvent(name, event.down, event.timestamp))
    return True


def _number(value: Any, name: str, low: float, high: float, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"{name} must be between {low:g} and {high:g}")
    return result


def _validate_keys(value: Mapping[str, Any], allowed: frozenset[str], label: str) -> None:
    unknown = set(value) - set(allowed)
    if unknown:
        raise ValueError(f"unknown {label} keys: {', '.join(sorted(unknown))}")


def _validated_record(value: Mapping[str, Any], defaults: Mapping[str, Any], allowed: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    _validate_keys(value, allowed, label)
    out = dict(defaults)
    for key, raw in value.items():
        default = defaults[key]
        if isinstance(default, bool):
            out[key] = bool(raw)
        elif isinstance(default, float):
            out[key] = _number(raw, key, 0.0, 1000.0, default)
        elif isinstance(default, int):
            out[key] = int(_number(raw, key, 0.0, 1000.0, default))
        else:
            if not isinstance(raw, str):
                raise ValueError(f"{key} must be a string")
            out[key] = raw
    return out


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a config document and reject unknown keys rather than ignoring them."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _validated_record(data, default_config(), _CONFIG_KEYS, "config")


def save_profile(path: str | Path, profile: Mapping[str, Any]) -> None:
    """Write one profile atomically after full validation."""

    name = str(profile.get("name", "default"))
    if not name or name not in {"default", "polytopia", "custom"}:
        raise ValueError(f"unsupported profile name: {name!r}")
    values = _validated_record(profile, default_profile(name), _PROFILE_KEYS, "profile")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(json.dumps({name: values}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def load_profiles(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load the small profile document used by the explicit launch panel."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("profiles must be an object")
    out: dict[str, dict[str, Any]] = {}
    for name, profile in data.items():
        if name not in {"default", "polytopia", "custom"}:
            raise ValueError(f"unsupported profile name: {name!r}")
        values = _validated_record(profile, default_profile(name), _PROFILE_KEYS, f"profile {name}")
        values["name"] = name
        out[name] = values
    if not out:
        raise ValueError("at least one profile is required")
    return out


def default_config() -> dict[str, Any]:
    return default_profile("default")


def default_profile(name: str = "default") -> dict[str, Any]:
    return {
        "name": name,
        "panSpeed": DEFAULT_PAN_SPEED,
        "panInvert": DEFAULT_PAN_INVERT,
        "zoomSpeed": DEFAULT_ZOOM_SPEED,
        "tickMs": DEFAULT_TICK_MS,
        "releaseMs": DEFAULT_RELEASE_MS,
        "margin": DEFAULT_MARGIN,
        "targetSerial": "",
        "package": "air.com.midjiwan.polytopia",
        "displaySize": "1920x1080/240",
        "noAudio": True,
        "shortcutMod": "lctrl",
    }


def build_scrcpy_args(serial: str, profile: Mapping[str, Any]) -> list[str]:
    """Build a safe argv list for a single-game virtual-display session."""

    if not isinstance(serial, str) or not _SERIAL_RE.fullmatch(serial):
        raise ValueError(f"invalid device serial: {serial!r}")
    package = profile.get("package", "")
    if not isinstance(package, str) or not _PACKAGE_RE.fullmatch(package):
        raise ValueError(f"invalid app package: {package!r}")
    display = profile.get("displaySize", "")
    if display and (not isinstance(display, str) or not _DISPLAY_RE.fullmatch(display)):
        raise ValueError(f"invalid display size: {display!r}")
    args = [
        "-s",
        serial,
        f"--new-display={display}" if display else "--new-display",
        "--no-vd-system-decorations",
        f"--start-app=+{package}",
        "--mouse-bind=----:----",
        "--keep-active",
        "--stay-awake",
        "--shortcut-mod=lctrl",
    ]
    if profile.get("noAudio", True):
        args.append("--no-audio")
    return args
