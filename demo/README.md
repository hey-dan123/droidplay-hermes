# Demo

Open `demo/index.html` directly in a browser.

The demo is a static, illustrative console for DroidPlay Hermes. It includes:

- a bar/status presentation
- a simulated receiver and adapter state
- a Hermes strategy question flow
- an explicit advisory-only safety boundary

It does not connect to DroidPlay, ADB, Hermes, GitHub, or any network service.

`demo/demo_adapter.py` is a deterministic local fixture for future integration
work. It is not used by the browser page.
