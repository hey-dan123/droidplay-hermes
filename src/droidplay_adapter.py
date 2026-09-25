"""Safe DroidPlay adapter used by the Omarchy QML widget.

The adapter owns process boundaries. QML supplies an allowlisted action and
optionally a media identifier; this module never accepts a shell string from
model output.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable


ALLOWED_ACTIONS = frozenset({"status", "play", "stop", "ask-hermes"})


class AdapterError(RuntimeError):
    """A bounded, user-facing adapter failure."""


def hermes_command() -> list[str]:
    configured = os.environ.get("DROIDPLAY_HERMES", "").strip()
    if configured:
        return shlex_split_command(configured)
    local = Path.home() / ".local" / "bin" / "hermes"
    if local.is_file() and os.access(local, os.X_OK):
        return [str(local)]
    discovered = shutil.which("hermes")
    if discovered:
        return [discovered]
    raise AdapterError("Hermes executable not found")


def shlex_split_command(raw: str) -> list[str]:
    # Keep the environment override bounded to a simple executable path/args;
    # the widget never needs shell syntax. Use POSIX parsing without a shell.
    import shlex

    try:
        parts = shlex.split(raw, posix=True)
    except ValueError as exc:
        raise AdapterError("Invalid Hermes command") from exc
    if not parts:
        raise AdapterError("Empty Hermes command")
    return parts


def parse_adapter_result(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise AdapterError("Adapter returned no output")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AdapterError("Adapter returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise AdapterError("Adapter result must be a JSON object")
    return value


def normalize_status(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "status": "unknown",
            "service": "unknown",
            "receiver": "",
            "error": "",
            "healthy": False,
            "errors": ["adapter result was not an object"],
        }
    status = str(value.get("status", "unknown")).strip().lower() or "unknown"
    service = str(value.get("service", "unknown")).strip() or "unknown"
    receiver = str(value.get("receiver", "")).strip()
    error = str(value.get("error", "")).strip()
    errors = [error] if error else []
    if status == "unknown" and not error:
        errors.append("adapter returned no status fields")
    if status not in {"ready", "running", "paused", "stopped", "unknown", "error"}:
        errors.append(f"unrecognized status: {status}")
    return {
        "status": status,
        "service": service,
        "receiver": receiver,
        "error": error,
        "healthy": status in {"ready", "running"} and service in {"ready", "running", "installed"},
        "errors": errors,
    }


def validate_action(action: str, media: str | None = None) -> str:
    value = str(action or "").strip().lower()
    if value not in ALLOWED_ACTIONS:
        raise AdapterError("Unsupported DroidPlay action")
    if value == "play" and not str(media or "").strip():
        raise AdapterError("A media item is required to play")
    return value


def build_prompt(status: dict[str, Any], question: str, constraints: Iterable[str] = ()) -> str:
    payload = {
        "schemaVersion": 1,
        "role": "DroidPlay strategy assistant",
        "question": str(question or "").strip(),
        "currentStatus": normalize_status(status),
        "constraints": [str(item) for item in constraints if str(item).strip()],
    }
    instructions = (
        "You are DroidPlay's strategy assistant. Give practical, concise advice "
        "for the current DroidPlay session. Do not invent receivers, media, or "
        "device state. Never claim an action was performed. If the user asks "
        "for a control action, describe the safe next step and require a human "
        "confirmation. Do not emit shell commands or credentials.\n\n"
        "Input JSON:\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )
    return instructions


def run_hermes(
    command: list[str] | None = None,
    *,
    prompt: str,
    cwd: str | None = None,
    timeout_seconds: int = 45,
    command_override: list[str] | None = None,
) -> str:
    """Run one bounded Hermes request and return stdout only.

    ``command_override`` exists solely for deterministic fake-process tests.
    It is never populated by the QML plugin or model output.
    """
    base = list(command_override) if command_override is not None else (list(command) if command else hermes_command())
    if not base:
        raise AdapterError("Hermes command is empty")
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="droidplay-hermes-", suffix=".txt", delete=False
    ) as handle:
        handle.write(prompt)
        prompt_path = handle.name
    full_command = base + [
        "chat",
        "--query-file",
        prompt_path,
        "--oneshot",
        "--quiet",
        "--format",
        "text",
        "--source",
        "tool",
        "--max-turns",
        "3",
        "--run-budget",
        str(max(5, int(timeout_seconds))),
    ]
    try:
        completed = subprocess.run(
            full_command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=max(5, int(timeout_seconds)),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdapterError(f"Hermes request failed: {exc}") from exc
    finally:
        try:
            os.unlink(prompt_path)
        except FileNotFoundError:
            pass
    if completed.returncode != 0:
        detail = str(completed.stderr or "").strip().replace("\n", " ")
        raise AdapterError(detail[:240] or f"Hermes exited with code {completed.returncode}")
    answer = str(completed.stdout or "").strip()
    if not answer:
        raise AdapterError("Hermes returned an empty answer")
    return answer


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else [])
    action = args[0] if args else "status"
    try:
        action = validate_action(action, args[1] if len(args) > 1 else None)
        if action == "ask-hermes":
            question = args[1] if len(args) > 1 else ""
            print(run_hermes(prompt=build_prompt(normalize_status({}), question)))
            return 0
        if action in {"status", "play", "stop"}:
            print(json.dumps(normalize_status({}), sort_keys=True))
            return 0
        raise AdapterError("Unsupported action")
    except AdapterError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
