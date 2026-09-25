# DroidPlay Hermes — project instructions

This repository is an Omarchy shell plugin plus a small, explicit Python adapter.

## Boundaries

- QML renders state and collects a user question. It must not build shell strings.
- Python owns subprocess boundaries, JSON validation, and Hermes invocation.
- Hermes output is advisory text. It is never a command, ADB argument, or proof
  that a device action happened.
- Unknown and unreadable states remain visible; do not turn them into healthy.
- The MVP is status + advice only. `play` and `stop` require a separately
  reviewed, authenticated DroidPlay bridge and explicit human confirmation.

## Verify before publishing

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
/usr/lib/qt6/bin/qmlformat -n src/*.qml
```

After installing locally, verify the actual shell effect with
`omarchy plugin list --json` and `omarchy-shell shell debugBarGeometry`, not
only a zero exit code.
