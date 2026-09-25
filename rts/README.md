# RTS control policy

The Mac experiment used Hammerspoon event taps and synthetic cursor motion:
WASD became a held mouse drag, and two-finger scroll became a Ctrl-drag pinch.
That is a workable Mac workaround, but it is not a good Linux/Wayland design.

The Omarchy redesign uses a compositor-native boundary:

```text
raw evdev keyboard events → normalized GestureState → focused-session gate
  → ydotool/uinput pointer events → scrcpy → Android touch
```

The policy layer is implemented and tested. The live input bridge is deliberately
not enabled from a source checkout. It must first be installed as a user service
with an explicit device-selection and focus gate, then exercised against a real
Android device. No synthetic input is emitted by tests or by `rts_helper.py`.

## Behavior contract

- Hold `W/A/S/D` or arrow keys to pan.
- Diagonal input is normalized, so a diagonal does not become 1.4× faster.
- Releasing the final movement key clears the pan state.
- Non-control keys are ignored by the policy layer.
- Pan and zoom are separate gestures; the future bridge must finish the active
  pan before starting a zoom.
- Input is accepted only while the exact scrcpy kiosk window is focused.
- Hermes advice is displayed as advice; it never chooses input commands.

## Requirements for the live bridge

- `scrcpy` 4.1 on Arch (verified in the configured repositories).
- `android-platform-tools`/`adb`.
- `ydotool` and `ydotoold` for uinput pointer injection.
- `python-evdev` for raw keyboard events.
- User membership/access for `/dev/input` and `/dev/uinput`; never run this as
  root merely to bypass permissions.

The configured Arch repositories currently report:

- `scrcpy 4.1-2`
- `ydotool 1.0.4-2`
- `python-evdev 2.0.0-1`

The binaries are not installed on this Omarchy host yet, and no authorized
Android device has been observed here. Consequently no live input claim is made.

## Configuration

The example profile is `profiles.example.json`. Copy it to:

```text
~/.config/droidplay-rts/profiles.json
```

Unknown keys fail validation. The package, display size, serial, and shortcut
modifier are passed as separate argv entries, never assembled into a shell
command.

## Test

```bash
cd rts
python3 -m unittest discover -s tests -v
python3 -m py_compile rts_control.py rts_helper.py
python3 rts_helper.py show-config
```

The helper's `launch-args` action prints validated JSON argv for review. It does
not start `scrcpy`, `adb`, or `ydotoold`.
