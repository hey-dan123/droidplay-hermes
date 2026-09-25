# DroidPlay RTS for Omarchy

A redesign of the Mac Hammerspoon map-control experiment as a native Linux
Wayland helper for the DroidPlay `scrcpy` kiosk.

## The replacement

The old path was:

```text
macOS Hammerspoon → synthesize mouse drag → scrcpy → Android touch
```

The new path is:

```text
Linux evdev keyboard listener → normalized gesture state → ydotool/uinput
  → focused scrcpy pointer events → Android touch
```

This removes Hammerspoon and its macOS Accessibility boundary. It also removes
the fragile “move the physical cursor, re-anchor, and paste a drag” loop. The
Linux helper owns a small state machine instead:

- W/A/S/D or arrow keys are held-key pan controls.
- Diagonal movement is normalized, so panning speed does not jump when two
  axes are held.
- Pan and zoom gestures are mutually exclusive; a scroll/zoom gesture always
  ends a live pan first.
- Normal desktop keys pass through unchanged.
- Input is only accepted while the configured scrcpy window is focused.
- The helper starts a scrcpy kiosk itself with validated argv, rather than
  accepting a shell string.

## Deliberate safety boundary

The live input emitter is not enabled by merely installing this directory. It
requires all of the following:

1. `ydotool` and `ydotoold` are installed and the operator explicitly starts
   the daemon.
2. A real Android device is connected and authorized through ADB.
3. The operator configures the exact package and, preferably, a USB serial.
4. The focused window is a scrcpy window launched by this helper.

The helper never runs Hermes output as a command. Hermes advice is a separate
consumer of game state, not an input controller.

## Requirements

- Omarchy 4.0.4 or compatible Quickshell shell.
- `scrcpy` 4.0+ for virtual-display kiosk support.
- `android-platform-tools` for `adb`.
- `ydotool` and `ydotoold` for Linux uinput pointer injection.
- `python-evdev` in a user-owned virtual environment for raw keyboard events.
- User access to `/dev/input` for reading the keyboard and `/dev/uinput` for
  ydotool. Do not run the helper as root.

On Arch, install the packaged prerequisites with:

```bash
sudo pacman -S scrcpy android-platform-tools ydotool python-evdev
```

The `python-evdev` package may be absent in a future Arch repository. In that
case create a user-owned venv instead of installing packages system-wide:

```bash
python3 -m venv ~/.local/share/droidplay-rts-venv
~/.local/share/droidplay-rts-venv/bin/pip install python-evdev
```

## Configuration

Copy the example profile and edit it:

```bash
cp rts/profiles.example.json ~/.config/droidplay-rts/profiles.json
```

The JSON document is deliberately allowlisted. Unknown keys are errors rather
than silently ignored settings.

`package` must be a valid Android application package. `displaySize` accepts
`WIDTHxHEIGHT[/DPI]`. `targetSerial` is a literal ADB serial; it is passed as a
separate argument and never interpolated into a shell command.

## Tests

```bash
cd rts
python3 -m unittest discover -s tests -v
```

The tests cover key normalization, diagonal velocity, release cleanup,
profile round-tripping, unknown-key rejection, and safe scrcpy argv construction.
They do not emit synthetic input.

## Current limitation

The policy/state-machine layer and safe launch argument builder are tested.
The raw-evdev listener and live pointer emitter are intentionally not enabled
until the local device path, scrcpy version, and udev permissions are verified
on this Omarchy host. Until then this is a redesign artifact, not a claim that
RTS keyboard control is playable.
