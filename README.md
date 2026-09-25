# DroidPlay Hermes

An Omarchy shell plugin for a safer, more useful DroidPlay workflow.

The plugin is intentionally **status + advice first**. It does not pretend that
an Android AirPlay sender, an ADB bridge, and an Omarchy shell are the same
process. The bridge is a small allowlisted adapter:

```text
Omarchy bar widget → droidplay-adapter → DroidPlay/ADB/remote helper
                                  └────→ Hermes one-shot strategy request
```

## What is implemented

- Omarchy-compatible `bar-widget` manifest.
- A compact bar label with explicit `ready`, `unknown`, `error`, and
  `checking` states.
- A keyboard-friendly popup with **Refresh status**, **Ask Hermes**, and
  **Show last advice**.
- A Python adapter with a narrow JSON contract and safe subprocess handling.
- Hermes requests use `--query-file` and bounded one-shot arguments.
- Pure Python tests cover malformed output, unknown state, shell-like user
  text, action allowlisting, and fake Hermes execution.
- No secrets, network server, raw ADB command, or LLM-generated shell command
  is part of the MVP.

## Install from the checkout

```bash
omarchy plugin add file:///path/to/droidplay-hermes --yes
omarchy plugin enable droidplay-hermes --section right
```

For a remote checkout:

```bash
omarchy plugin add https://github.com/hey-dan123/droidplay-hermes.git --enable --yes
```

`droidplay-adapter` must be on `PATH`, or set the widget setting
`droidplayCommand` to an absolute executable path. The adapter is deliberately
not shipped as a raw shell alias: a local installation can point the setting
at a reviewed wrapper reviewed by the machine owner.

## Adapter contract

The adapter must accept exactly one action and write one JSON document to
stdout:

```json
{"status":"ready","service":"running","receiver":"Living Room","error":""}
```

Accepted actions:

- `status`
- `play` (requires a media argument)
- `stop`
- `ask-hermes` (handled by the built-in bridge, not sent to DroidPlay)

The plugin starts with status and advice only. `play`/`stop` are reserved for
a future explicit confirmation surface. Hermes output is advisory only and
never interpreted as a command.

## Hermes

The adapter locates Hermes in this order:

1. `DROIDPLAY_HERMES` environment variable.
2. `~/.local/bin/hermes`.
3. `hermes` on `PATH`.

It invokes:

```text
hermes chat --query-file <temporary-file> --oneshot --quiet --format text \
  --source tool --max-turns 3 --run-budget <configured-seconds>
```

The query is JSON containing the question, current DroidPlay status, and
constraints. `stderr` is never parsed as the answer. The temporary prompt is
removed in a `finally` block.

## Test

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
/usr/lib/qt6/bin/qmlformat -n src/*.qml
```

`qmlformat -n` is a syntax smoke test; it does not replace loading the plugin
inside the live Omarchy shell.

## Scope boundary

The supplied `hey-dan123/droidplay` URL is not publicly available. The public
DroidPlay lineage is an Android AirPlay sender (GPL-3.0), not an Omarchy
plugin. This repository starts with a clean-room Omarchy integration and a
documented adapter boundary. It does not copy Android source, branding, or
media implementation.

**Before enabling control actions, provide and review an authenticated bridge
to the actual DroidPlay app. The current MVP is read-only/advice-only.**
