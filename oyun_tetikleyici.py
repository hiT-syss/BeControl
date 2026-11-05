import ctypes
from ctypes import wintypes
import os

import pydirectinput as direct

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
user32.IsWindowVisible.argtypes = (wintypes.HWND,)
user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = (CALLBACK, wintypes.LPARAM)

MOUSE = {"left click": (2, 4), "right click": (8, 16), "middle click": (32, 64)}
KEYS = tuple(sorted(key for key, value in direct.KEYBOARD_MAPPING.items() if value is not None)) + tuple(MOUSE)
direct.PAUSE = 0

direct.FAILSAFE = False
MODIFIERS = {"shift", "shiftleft", "shiftright", "ctrl", "ctrlleft", "ctrlright",
             "alt", "altleft", "altright", "win", "winleft", "winright"}


def key_order(key):
    return key not in MODIFIERS, key


def process_id(window):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(window, ctypes.byref(pid))
    return pid.value


def open_windows():
    windows = {}

    @CALLBACK
    def collect(window, _):
        if not user32.IsWindowVisible(window):
            return True
        length = user32.GetWindowTextLengthW(window)
        pid = process_id(window)
        if length and pid != os.getpid():
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(window, title, len(title))
            if title.value.strip():
                windows[f"{title.value}  [{window:X}]"] = (window, pid)
        return True

    user32.EnumWindows(collect, 0)
    return dict(sorted(windows.items(), key=lambda entry: entry[0].casefold()))


def is_focused(target):
    window = user32.GetForegroundWindow()
    return bool(window and target and (window, process_id(window)) == target)


def send(key, down):
    if key in MOUSE:
        user32.mouse_event(MOUSE[key][0 if down else 1], 0, 0, 0, 0)
    else:
        (direct.keyDown if down else direct.keyUp)(key, _pause=False)


class Trigger:
    def __init__(self):
        self.held = set()
        self.previous = set()
        self.deadlines = {}
        self.ready = False

    def reset(self):
        for key in sorted(self.held, key=key_order, reverse=True):
            send(key, False)
            self.held.remove(key)
        self.previous.clear()
        self.deadlines.clear()
        self.ready = False

    def update(self, bindings, gestures, tilt, steering, now):
        if not self.ready:
            
            self.previous = {(side, mask) for side, mask in gestures.items()}
            self.ready = True
        active = {(side, mask) for side, mask in gestures.items()}
        desired = set()
        for side, mask, keys, mode in bindings:
            gesture = (side, mask)
            if gesture not in active:
                self.deadlines.pop(gesture, None)
                continue
            if mode == "Hold":
                desired.update(keys)
                continue
            if gesture not in self.previous:
                self.deadlines[gesture] = now
            start = self.deadlines.get(gesture)
            if start is not None:
                elapsed = now - start
                if elapsed < 0.1 or (mode == "Repeat" and elapsed % 0.35 < 0.1):
                    desired.update(keys)
        for key in sorted(self.held - desired, key=key_order, reverse=True):
            send(key, False)
            self.held.remove(key)
        for key in sorted(desired - self.held, key=key_order):
            send(key, True)
            self.held.add(key)
        self.previous = active
        if steering and gestures.get("Red") == 9 and abs(tilt) > 0.05:
            move = int((tilt - (0.05 if tilt > 0 else -0.05)) * 600)
            user32.mouse_event(1, move, 0, 0, 0)
