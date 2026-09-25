"""Tests for the Omarchy RTS keyboard control policy.

These tests deliberately exercise pure state-machine functions first. The actual
Wayland input emitter is an integration seam and must stay behind an explicit
focused-session gate.
"""

import json
import tempfile
import unittest
from pathlib import Path

from rts_control import (
    ACTIVE_KEYS,
    DEFAULT_PAN_INVERT,
    GestureState,
    KeyEvent,
    apply_key_event,
    apply_key_event_safe,
    build_scrcpy_args,
    load_config,
    load_profiles,
    parse_key_name,
    save_profile,
)


class KeyNameTests(unittest.TestCase):
    def test_parses_wasd_and_arrows(self):
        self.assertEqual(parse_key_name("w"), "W")
        self.assertEqual(parse_key_name("A"), "A")
        self.assertEqual(parse_key_name("arrowup"), "ArrowUp")
        self.assertEqual(parse_key_name("left"), "ArrowLeft")

    def test_rejects_unknown_key(self):
        with self.assertRaises(ValueError):
            parse_key_name("Q")


class StateMachineTests(unittest.TestCase):
    def test_hold_pan_accumulates_axes(self):
        state = GestureState(pan_invert=False)
        apply_key_event(state, KeyEvent("w", True, timestamp=1.0))
        apply_key_event(state, KeyEvent("d", True, timestamp=1.01))
        self.assertAlmostEqual(state.dx, 0.70710678, places=6)
        self.assertAlmostEqual(state.dy, -0.70710678, places=6)
        self.assertTrue(state.panning)

    def test_release_stops_pan_and_clears_axis(self):
        state = GestureState()
        apply_key_event(state, KeyEvent("w", True, timestamp=1.0))
        apply_key_event(state, KeyEvent("w", False, timestamp=1.1))
        self.assertEqual(state.dx, 0.0)
        self.assertEqual(state.dy, 0.0)
        self.assertFalse(state.panning)

    def test_diagonal_is_normalized(self):
        state = GestureState(pan_invert=False)
        apply_key_event(state, KeyEvent("w", True, timestamp=1.0))
        apply_key_event(state, KeyEvent("d", True, timestamp=1.1))
        self.assertAlmostEqual(state.dx, 0.70710678, places=6)
        self.assertAlmostEqual(state.dy, -0.70710678, places=6)

    def test_pan_direction_can_be_inverted(self):
        state = GestureState(pan_invert=DEFAULT_PAN_INVERT)
        apply_key_event(state, KeyEvent("w", True, timestamp=1.0))
        self.assertEqual(state.dy, 1.0)

    def test_non_control_key_is_ignored(self):
        state = GestureState()
        self.assertFalse(apply_key_event_safe(state, KeyEvent("q", True, timestamp=1.0)))
        self.assertFalse(state.panning)
        self.assertEqual(state.dx, 0.0)
        self.assertEqual(state.dy, 0.0)


class ScrcpyArgsTests(unittest.TestCase):
    def test_builds_kiosk_args_without_shell_string(self):
        args = build_scrcpy_args(
            "192.0.2.10:5555",
            {
                "package": "air.com.midjiwan.polytopia",
                "displaySize": "1920x1080/240",
                "noAudio": True,
            },
        )
        self.assertEqual(args[:2], ["-s", "192.0.2.10:5555"])
        self.assertIn("--new-display=1920x1080/240", args)
        self.assertIn("--no-vd-system-decorations", args)
        self.assertIn("--start-app=+air.com.midjiwan.polytopia", args)
        self.assertIn("--keep-active", args)
        self.assertIn("--no-audio", args)
        self.assertIn("--shortcut-mod=lctrl", args)
        self.assertTrue(all(isinstance(arg, str) for arg in args))

    def test_rejects_invalid_package(self):
        with self.assertRaises(ValueError):
            build_scrcpy_args("serial", {"package": "bad; touch /tmp/pwned"})

    def test_rejects_invalid_display_size(self):
        with self.assertRaises(ValueError):
            build_scrcpy_args("serial", {"package": "air.com.midjiwan.polytopia", "displaySize": "oops"})


class ConfigTests(unittest.TestCase):
    def test_load_config_rejects_unknown_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"wibble": True}))
            with self.assertRaises(ValueError):
                load_config(path)

    def test_load_config_rejects_string_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"panInvert": "false"}))
            with self.assertRaises(ValueError):
                load_config(path)

    def test_profile_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            save_profile(
                path,
                {
                    "name": "default",
                    "panSpeed": 0.75,
                    "panInvert": False,
                    "zoomSpeed": 0.4,
                    "targetSerial": "emulator-5554",
                },
            )
            profile = load_profiles(path).get("default")
            self.assertEqual(profile["panSpeed"], 0.75)
            self.assertFalse(profile["panInvert"])


if __name__ == "__main__":
    unittest.main()
