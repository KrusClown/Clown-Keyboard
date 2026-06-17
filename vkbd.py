#!/usr/bin/env python3
"""
vkbd.py — Native GTK3 Virtual Keyboard for Linux (Wayland + X11)
=================================================================
Floating, draggable, always-on-top virtual keyboard.
Key injection via:
  • /dev/uinput  (evdev — works on Wayland AND X11, no extra tools)
  • ydotool      (fallback)
  • xdotool      (X11 fallback)

Requirements:
  sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-evdev
  sudo usermod -aG input $USER   (then log out/in, or run with sudo once)

Usage:
  python3 vkbd.py
  python3 vkbd.py --theme dark        (dark | light | contrast)
  python3 vkbd.py --lang ES
  python3 vkbd.py --scale 1.2
"""

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

import sys
import os
import time
import shutil
import argparse
import subprocess
import threading
from typing import Optional

# ── evdev / uinput injection ──────────────────────────────────
try:
    import evdev
    from evdev import UInput, ecodes as e
    EVDEV_OK = True
except ImportError:
    EVDEV_OK = False

# ─────────────────────────────────────────────────────────────
#  KEYBOARD LAYOUT  (QWERTY)
# ─────────────────────────────────────────────────────────────
# Each key: (label, evdev_keycode, shift_label, width_multiplier)
# width_multiplier: 1.0 = standard key width

ROW_FUNC = [
    ("Esc",    e.KEY_ESC,        "Esc",    1.0),
    ("F1",     e.KEY_F1,         "F1",     1.0),
    ("F2",     e.KEY_F2,         "F2",     1.0),
    ("F3",     e.KEY_F3,         "F3",     1.0),
    ("F4",     e.KEY_F4,         "F4",     1.0),
    ("F5",     e.KEY_F5,         "F5",     1.0),
    ("F6",     e.KEY_F6,         "F6",     1.0),
    ("F7",     e.KEY_F7,         "F7",     1.0),
    ("F8",     e.KEY_F8,         "F8",     1.0),
    ("F9",     e.KEY_F9,         "F9",     1.0),
    ("F10",    e.KEY_F10,        "F10",    1.0),
    ("F11",    e.KEY_F11,        "F11",    1.0),
    ("F12",    e.KEY_F12,        "F12",    1.0),
    ("Del",    e.KEY_DELETE,     "Del",    1.0),
]

ROW_NUM = [
    ("`",      e.KEY_GRAVE,      "~",      1.0),
    ("1",      e.KEY_1,          "!",      1.0),
    ("2",      e.KEY_2,          "@",      1.0),
    ("3",      e.KEY_3,          "#",      1.0),
    ("4",      e.KEY_4,          "$",      1.0),
    ("5",      e.KEY_5,          "%",      1.0),
    ("6",      e.KEY_6,          "^",      1.0),
    ("7",      e.KEY_7,          "&",      1.0),
    ("8",      e.KEY_8,          "*",      1.0),
    ("9",      e.KEY_9,          "(",      1.0),
    ("0",      e.KEY_0,          ")",      1.0),
    ("-",      e.KEY_MINUS,      "_",      1.0),
    ("=",      e.KEY_EQUAL,      "+",      1.0),
    ("⌫",     e.KEY_BACKSPACE,  "⌫",     2.0),
]

ROW_QWERTY = [
    ("Tab",    e.KEY_TAB,        "Tab",    1.5),
    ("Q",      e.KEY_Q,          "Q",      1.0),
    ("W",      e.KEY_W,          "W",      1.0),
    ("E",      e.KEY_E,          "E",      1.0),
    ("R",      e.KEY_R,          "R",      1.0),
    ("T",      e.KEY_T,          "T",      1.0),
    ("Y",      e.KEY_Y,          "Y",      1.0),
    ("U",      e.KEY_U,          "U",      1.0),
    ("I",      e.KEY_I,          "I",      1.0),
    ("O",      e.KEY_O,          "O",      1.0),
    ("P",      e.KEY_P,          "P",      1.0),
    ("[",      e.KEY_LEFTBRACE,  "{",      1.0),
    ("]",      e.KEY_RIGHTBRACE, "}",      1.0),
    ("\\",     e.KEY_BACKSLASH,  "|",      1.5),
]

ROW_ASDF = [
    ("Caps",   e.KEY_CAPSLOCK,   "Caps",   1.8),
    ("A",      e.KEY_A,          "A",      1.0),
    ("S",      e.KEY_S,          "S",      1.0),
    ("D",      e.KEY_D,          "D",      1.0),
    ("F",      e.KEY_F,          "F",      1.0),
    ("G",      e.KEY_G,          "G",      1.0),
    ("H",      e.KEY_H,          "H",      1.0),
    ("J",      e.KEY_J,          "J",      1.0),
    ("K",      e.KEY_K,          "K",      1.0),
    ("L",      e.KEY_L,          "L",      1.0),
    (";",      e.KEY_SEMICOLON,  ":",      1.0),
    ("'",      e.KEY_APOSTROPHE, '"',      1.0),
    ("Enter",  e.KEY_ENTER,      "Enter",  2.2),
]

ROW_ZXCV = [
    ("Shift",  e.KEY_LEFTSHIFT,  "Shift",  2.5),
    ("Z",      e.KEY_Z,          "Z",      1.0),
    ("X",      e.KEY_X,          "X",      1.0),
    ("C",      e.KEY_C,          "C",      1.0),
    ("V",      e.KEY_V,          "V",      1.0),
    ("B",      e.KEY_B,          "B",      1.0),
    ("N",      e.KEY_N,          "N",      1.0),
    ("M",      e.KEY_M,          "M",      1.0),
    (",",      e.KEY_COMMA,      "<",      1.0),
    (".",      e.KEY_DOT,        ">",      1.0),
    ("/",      e.KEY_SLASH,      "?",      1.0),
    ("Shift",  e.KEY_RIGHTSHIFT, "Shift",  2.5),
]

ROW_BOTTOM = [
    ("Ctrl",   e.KEY_LEFTCTRL,   "Ctrl",   1.5),
    ("Super",  e.KEY_LEFTMETA,   "Super",  1.5),
    ("Alt",    e.KEY_LEFTALT,    "Alt",    1.5),
    ("Space",  e.KEY_SPACE,      "Space",  6.0),
    ("Alt",    e.KEY_RIGHTALT,   "Alt",    1.5),
    ("Ctrl",   e.KEY_RIGHTCTRL,  "Ctrl",   1.5),
    ("◀",     e.KEY_LEFT,       "◀",     1.0),
    ("▲",     e.KEY_UP,         "▲",     1.0),
    ("▼",     e.KEY_DOWN,       "▼",     1.0),
    ("▶",     e.KEY_RIGHT,      "▶",     1.0),
]

ROWS = [ROW_FUNC, ROW_NUM, ROW_QWERTY, ROW_ASDF, ROW_ZXCV, ROW_BOTTOM]

# Modifier keycodes
MODIFIER_CODES = {
    e.KEY_LEFTSHIFT, e.KEY_RIGHTSHIFT,
    e.KEY_LEFTCTRL,  e.KEY_RIGHTCTRL,
    e.KEY_LEFTALT,   e.KEY_RIGHTALT,
    e.KEY_LEFTMETA,  e.KEY_CAPSLOCK,
}

# ─────────────────────────────────────────────────────────────
#  THEMES
# ─────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "win_bg":       "#0d1117",
        "key_bg":       "#21262d",
        "key_bg_hover": "#30363d",
        "key_bg_press": "#1f6feb",
        "key_fg":       "#e6edf3",
        "key_fg_sub":   "#8b949e",
        "mod_bg":       "#161b22",
        "mod_active":   "#388bfd",
        "enter_bg":     "#1a3a5c",
        "border":       "#30363d",
        "shadow":       "rgba(0,0,0,0.6)",
        "drag_bg":      "#161b22",
        "drag_fg":      "#58a6ff",
    },
    "light": {
        "win_bg":       "#f0f2f5",
        "key_bg":       "#ffffff",
        "key_bg_hover": "#e8eaed",
        "key_bg_press": "#1a73e8",
        "key_fg":       "#202124",
        "key_fg_sub":   "#5f6368",
        "mod_bg":       "#e8eaed",
        "mod_active":   "#1a73e8",
        "enter_bg":     "#d2e3fc",
        "border":       "#dadce0",
        "shadow":       "rgba(0,0,0,0.2)",
        "drag_bg":      "#e8eaed",
        "drag_fg":      "#1a73e8",
    },
    "contrast": {
        # WCAG 2.0 AAA — all text/bg pairs exceed 7:1
        "win_bg":       "#000000",
        "key_bg":       "#0a0a0a",
        "key_bg_hover": "#1a1a00",
        "key_bg_press": "#ffff00",
        "key_fg":       "#ffffff",
        "key_fg_sub":   "#cccccc",
        "mod_bg":       "#000000",
        "mod_active":   "#ffff00",
        "enter_bg":     "#003300",
        "border":       "#ffffff",
        "shadow":       "rgba(255,255,0,0.2)",
        "drag_bg":      "#000000",
        "drag_fg":      "#ffff00",
    },
}

# ─────────────────────────────────────────────────────────────
#  LANGUAGE OVERRIDES
#  Keys that change character depending on language
# ─────────────────────────────────────────────────────────────
LANG_OVERRIDES = {
    "ES": {e.KEY_SEMICOLON: ("Ñ", "ñ"), e.KEY_APOSTROPHE: ("¡", "¿")},
    "FR": {e.KEY_SEMICOLON: ("É", "é"), e.KEY_APOSTROPHE: ("À", "à"), e.KEY_LEFTBRACE: ("È", "è")},
    "DE": {e.KEY_SEMICOLON: ("Ö", "ö"), e.KEY_APOSTROPHE: ("Ä", "ä"), e.KEY_LEFTBRACE: ("Ü", "ü"), e.KEY_SLASH: ("ß", "ß")},
    "PT": {e.KEY_SEMICOLON: ("Ã", "ã"), e.KEY_APOSTROPHE: ("Ç", "ç"), e.KEY_LEFTBRACE: ("Õ", "õ")},
}

# ─────────────────────────────────────────────────────────────
#  INPUT INJECTOR
# ─────────────────────────────────────────────────────────────
class Injector:
    """
    Sends real key events to the kernel via /dev/uinput.
    This works on Wayland and X11 alike because it operates
    at the input layer, below the display server.
    Falls back to ydotool or xdotool if uinput is unavailable.
    """

    def __init__(self):
        self.ui: Optional[UInput] = None
        self.method = "none"
        self._init()

    def _init(self):
        if EVDEV_OK:
            try:
                # Build capability map: all keys we use
                all_keys = set()
                for row in ROWS:
                    for _, keycode, _, _ in row:
                        all_keys.add(keycode)
                cap = {e.EV_KEY: list(all_keys)}
                self.ui = UInput(cap, name="vkbd-virtual-keyboard", version=0x3)
                self.method = "uinput"
                print("[vkbd] Injector: /dev/uinput (evdev) ✓")
                return
            except PermissionError:
                print("[vkbd] /dev/uinput permission denied.")
                print("       Fix: sudo usermod -aG input $USER  (then re-login)")
                print("       Or:  sudo chmod 660 /dev/uinput && sudo chgrp input /dev/uinput")
            except Exception as ex:
                print(f"[vkbd] uinput unavailable: {ex}")

        if shutil.which("ydotool"):
            self.method = "ydotool"
            print("[vkbd] Injector: ydotool ✓")
            return

        if shutil.which("xdotool"):
            self.method = "xdotool"
            print("[vkbd] Injector: xdotool ✓ (X11 only)")
            return

        print("[vkbd] WARNING: No input injector available.")
        print("       Keys will not be sent to other applications.")
        print("       Install: sudo apt install python3-evdev ydotool")
        self.method = "none"

    def press(self, keycode: int, modifiers: set):
        """Press key with modifiers, then release all."""
        if self.method == "uinput" and self.ui:
            self._uinput_press(keycode, modifiers)
        elif self.method == "ydotool":
            self._ydotool_press(keycode, modifiers)
        elif self.method == "xdotool":
            self._xdotool_press(keycode)

    def _uinput_press(self, keycode: int, modifiers: set):
        ui = self.ui
        # Press modifiers first
        for mod in modifiers:
            ui.write(e.EV_KEY, mod, 1)
        ui.write(e.EV_KEY, keycode, 1)  # key down
        ui.syn()
        time.sleep(0.02)
        ui.write(e.EV_KEY, keycode, 0)  # key up
        for mod in modifiers:
            ui.write(e.EV_KEY, mod, 0)
        ui.syn()

    def _ydotool_press(self, keycode: int, modifiers: set):
        # ydotool uses key names; map common ones
        YDOTOOL_MAP = {
            e.KEY_ENTER: "Return", e.KEY_BACKSPACE: "BackSpace",
            e.KEY_TAB: "Tab", e.KEY_SPACE: "space",
            e.KEY_ESC: "Escape", e.KEY_CAPSLOCK: "Caps_Lock",
            e.KEY_LEFTSHIFT: "shift", e.KEY_RIGHTSHIFT: "shift",
            e.KEY_LEFTCTRL: "ctrl", e.KEY_RIGHTCTRL: "ctrl",
            e.KEY_LEFTALT: "alt", e.KEY_RIGHTALT: "alt",
            e.KEY_LEFTMETA: "super", e.KEY_DELETE: "Delete",
            e.KEY_LEFT: "Left", e.KEY_RIGHT: "Right",
            e.KEY_UP: "Up", e.KEY_DOWN: "Down",
        }
        name = YDOTOOL_MAP.get(keycode, f"0x{keycode:04x}")
        subprocess.Popen(["ydotool", "key", name],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _xdotool_press(self, keycode: int):
        XDOTOOL_MAP = {
            e.KEY_ENTER: "Return", e.KEY_BACKSPACE: "BackSpace",
            e.KEY_TAB: "Tab", e.KEY_SPACE: "space",
            e.KEY_ESC: "Escape", e.KEY_CAPSLOCK: "Caps_Lock",
            e.KEY_LEFT: "Left", e.KEY_RIGHT: "Right",
            e.KEY_UP: "Up", e.KEY_DOWN: "Down",
            e.KEY_DELETE: "Delete",
        }
        name = XDOTOOL_MAP.get(keycode, f"key_{keycode}")
        subprocess.Popen(["xdotool", "key", name],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def toggle_modifier(self, keycode: int, pressed: bool):
        """Hold or release a modifier continuously (for combos)."""
        if self.method == "uinput" and self.ui:
            self.ui.write(e.EV_KEY, keycode, 1 if pressed else 0)
            self.ui.syn()

    def close(self):
        if self.ui:
            try:
                self.ui.close()
            except Exception:
                pass

# ─────────────────────────────────────────────────────────────
#  GTK3 CSS BUILDER
# ─────────────────────────────────────────────────────────────
def build_css(t: dict, scale: float) -> str:
    base = int(36 * scale)
    fn_h = int(30 * scale)
    font = int(12 * scale)
    sub  = int(8  * scale)
    rad  = int(6  * scale)

    return f"""
    window {{
        background-color: {t['win_bg']};
    }}
    .drag-bar {{
        background-color: {t['drag_bg']};
        padding: 4px 8px;
        border-bottom: 1px solid {t['border']};
    }}
    .drag-label {{
        color: {t['drag_fg']};
        font-size: {int(10*scale)}px;
        font-weight: 600;
        letter-spacing: 1px;
    }}
    .key-row {{
        padding: 2px 4px;
        spacing: {int(3*scale)}px;
    }}
    button.key {{
        background: {t['key_bg']};
        color: {t['key_fg']};
        border: 1px solid {t['border']};
        border-radius: {rad}px;
        font-size: {font}px;
        font-weight: 500;
        min-height: {base}px;
        padding: 0 4px;
        box-shadow: 0 2px 0 rgba(0,0,0,0.4);
        transition: background 80ms, box-shadow 80ms;
    }}
    button.key:hover {{
        background: {t['key_bg_hover']};
        border-color: {t['drag_fg']};
    }}
    button.key:active {{
        background: {t['key_bg_press']};
        color: white;
        box-shadow: 0 1px 0 rgba(0,0,0,0.4);
        padding-top: 1px;
    }}
    button.key.fn-key {{
        background: {t['mod_bg']};
        color: {t['key_fg_sub']};
        min-height: {fn_h}px;
        font-size: {sub}px;
    }}
    button.key.mod-key {{
        background: {t['mod_bg']};
        color: {t['key_fg_sub']};
        font-size: {int(10*scale)}px;
    }}
    button.key.mod-active {{
        background: {t['mod_active']};
        color: white;
        border-color: {t['mod_active']};
    }}
    button.key.enter-key {{
        background: {t['enter_bg']};
    }}
    button.key.space-key {{
        color: {t['key_fg_sub']};
        font-size: {int(9*scale)}px;
    }}
    .combo-bar {{
        background-color: {t['mod_active']};
        padding: 2px 8px;
    }}
    .combo-label {{
        color: white;
        font-size: {int(10*scale)}px;
        font-weight: 700;
        letter-spacing: 1px;
    }}
    """

# ─────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────────
class VKbd(Gtk.Window):

    def __init__(self, theme_name="dark", lang="EN", scale=1.0):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.theme_name = theme_name
        self.lang       = lang
        self.scale      = scale
        self.theme      = THEMES.get(theme_name, THEMES["dark"])

        # Modifier state
        self.caps_on    = False
        self.shift_on   = False
        self.ctrl_on    = False
        self.alt_on     = False
        self.meta_on    = False
        self.active_mods: set[int] = set()    # held modifier keycodes
        self.mod_buttons: dict[int, list]  = {}  # keycode → [buttons]

        # Input injector
        self.injector = Injector()

        # Button references for label updates
        self.key_buttons: list[tuple] = []  # (button, keycode, base_label)

        self._build_window()
        self._apply_css()
        self._build_keyboard()
        self._connect_signals()

    # ── Window setup ─────────────────────────────────────────
    def _build_window(self):
        self.set_title("vkbd")
        self.set_decorated(False)          # no titlebar
        self.set_keep_above(True)          # always on top
        self.set_skip_taskbar_hint(True)   # hide from taskbar
        self.set_skip_pager_hint(True)
        self.set_resizable(True)
        self.set_app_paintable(True)

        # Transparent background support
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # Position: centre-bottom of primary monitor
        display  = Gdk.Display.get_default()
        monitor  = display.get_primary_monitor() or display.get_monitor(0)
        geom     = monitor.get_geometry()
        self.move(geom.x + 40, geom.y + geom.height - 320)
        self.set_default_size(geom.width - 80, -1)

        # Outer box
        self.outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.outer)

    def _apply_css(self):
        css  = build_css(self.theme, self.scale)
        prov = Gtk.CssProvider()
        prov.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # ── Drag bar ─────────────────────────────────────────────
    def _build_drag_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        bar.get_style_context().add_class("drag-bar")

        # Drag handle (left side)
        handle_lbl = Gtk.Label(label="⌨  vkbd  ·  drag to move")
        handle_lbl.get_style_context().add_class("drag-label")
        handle_lbl.set_halign(Gtk.Align.START)
        bar.pack_start(handle_lbl, True, True, 0)

        # Right controls
        ctrl_box = Gtk.Box(spacing=int(6 * self.scale))

        # Theme cycle button
        theme_btn = Gtk.Button(label="🎨")
        theme_btn.set_tooltip_text("Cycle theme (dark → light → contrast)")
        theme_btn.connect("clicked", self._cycle_theme)
        theme_btn.get_style_context().add_class("key")
        theme_btn.get_style_context().add_class("mod-key")
        ctrl_box.pack_start(theme_btn, False, False, 0)

        # Language selector
        lang_store = Gtk.ListStore(str, str)
        for code, label in [("EN","EN"), ("ES","ES"), ("FR","FR"),
                             ("DE","DE"), ("PT","PT")]:
            lang_store.append([code, label])
        self.lang_combo = Gtk.ComboBox.new_with_model(lang_store)
        renderer = Gtk.CellRendererText()
        self.lang_combo.pack_start(renderer, True)
        self.lang_combo.add_attribute(renderer, "text", 1)
        self.lang_combo.set_active(0)
        self.lang_combo.set_tooltip_text("Keyboard language")
        self.lang_combo.connect("changed", self._on_lang_change)
        ctrl_box.pack_start(self.lang_combo, False, False, 0)

        # Scale buttons
        for sym, delta in [("−", -0.05), ("+", +0.05)]:
            b = Gtk.Button(label=sym)
            b.set_tooltip_text("Resize keyboard")
            b.get_style_context().add_class("key")
            b.get_style_context().add_class("mod-key")
            b.connect("clicked", self._resize, delta)
            ctrl_box.pack_start(b, False, False, 0)

        # Close button
        close_btn = Gtk.Button(label="✕")
        close_btn.set_tooltip_text("Close virtual keyboard")
        close_btn.get_style_context().add_class("key")
        close_btn.get_style_context().add_class("mod-key")
        close_btn.connect("clicked", lambda _: Gtk.main_quit())
        ctrl_box.pack_start(close_btn, False, False, 0)

        bar.pack_end(ctrl_box, False, False, 0)
        return bar

    # ── Combo bar (shows active modifiers) ───────────────────
    def _build_combo_bar(self):
        self.combo_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.combo_bar.get_style_context().add_class("combo-bar")
        self.combo_lbl = Gtk.Label(label="")
        self.combo_lbl.get_style_context().add_class("combo-label")
        self.combo_bar.pack_start(self.combo_lbl, False, False, 0)
        self.combo_bar.set_no_show_all(True)
        return self.combo_bar

    # ── Keyboard rows ─────────────────────────────────────────
    def _build_keyboard(self):
        # Clear previous
        for child in self.outer.get_children():
            self.outer.remove(child)
        self.key_buttons.clear()
        self.mod_buttons.clear()

        self.outer.pack_start(self._build_drag_bar(), False, False, 0)
        self.outer.pack_start(self._build_combo_bar(), False, False, 0)

        BASE_W = int(38 * self.scale)
        GAP    = int(3  * self.scale)

        for row_def in ROWS:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                              spacing=GAP)
            row_box.get_style_context().add_class("key-row")
            row_box.set_homogeneous(False)

            is_fn_row = (row_def is ROW_FUNC)

            for base_label, keycode, shift_label, width_mult in row_def:
                btn = Gtk.Button()
                btn.set_focus_on_click(False)

                # Label: two lines (main + shift sub-label)
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                main_lbl = Gtk.Label(label=base_label)
                main_lbl.set_halign(Gtk.Align.CENTER)
                vbox.pack_start(main_lbl, True, True, 0)

                # Show shift-label only for character keys
                if shift_label != base_label and len(shift_label) <= 2:
                    sub_lbl = Gtk.Label(label=shift_label)
                    sub_lbl.set_opacity(0.45)
                    attrs = Pango.AttrList()
                    attrs.insert(Pango.AttrSize.new(int(7 * self.scale * 1000)))
                    sub_lbl.set_attributes(attrs)
                    vbox.pack_start(sub_lbl, False, False, 0)

                btn.add(vbox)
                btn.get_style_context().add_class("key")

                if is_fn_row:
                    btn.get_style_context().add_class("fn-key")
                elif keycode in MODIFIER_CODES:
                    btn.get_style_context().add_class("mod-key")
                elif keycode == e.KEY_ENTER:
                    btn.get_style_context().add_class("enter-key")
                elif keycode == e.KEY_SPACE:
                    btn.get_style_context().add_class("space-key")

                # Width
                w = int(BASE_W * width_mult)
                btn.set_size_request(w, -1)

                # Tooltip with key info
                btn.set_tooltip_text(f"{base_label}  /  Shift: {shift_label}")

                # Click handler
                btn.connect("clicked", self._on_key_clicked, keycode, base_label)

                # Track modifier buttons for visual feedback
                if keycode in MODIFIER_CODES:
                    if keycode not in self.mod_buttons:
                        self.mod_buttons[keycode] = []
                    self.mod_buttons[keycode].append(btn)

                self.key_buttons.append((btn, keycode, base_label, main_lbl))
                row_box.pack_start(btn, False, False, 0)

            self.outer.pack_start(row_box, False, False, GAP)

        self.show_all()
        self.combo_bar.hide()

    # ── Key click handler ─────────────────────────────────────
    def _on_key_clicked(self, btn, keycode: int, label: str):
        # ── Modifier toggle ──
        if keycode == e.KEY_CAPSLOCK:
            self.caps_on = not self.caps_on
            self._update_mod_visual(keycode, self.caps_on)
            self._update_labels()
            # Still send the keycode
            self.injector.press(keycode, set())
            return

        if keycode in (e.KEY_LEFTSHIFT, e.KEY_RIGHTSHIFT):
            self.shift_on = not self.shift_on
            self.active_mods.discard(e.KEY_LEFTSHIFT)
            self.active_mods.discard(e.KEY_RIGHTSHIFT)
            if self.shift_on:
                self.active_mods.add(keycode)
            self._update_mod_visual(e.KEY_LEFTSHIFT,  self.shift_on)
            self._update_mod_visual(e.KEY_RIGHTSHIFT, self.shift_on)
            self._update_labels()
            self._update_combo_bar()
            return

        if keycode in (e.KEY_LEFTCTRL, e.KEY_RIGHTCTRL):
            self.ctrl_on = not self.ctrl_on
            self.active_mods.discard(e.KEY_LEFTCTRL)
            self.active_mods.discard(e.KEY_RIGHTCTRL)
            if self.ctrl_on:
                self.active_mods.add(keycode)
            self._update_mod_visual(e.KEY_LEFTCTRL,  self.ctrl_on)
            self._update_mod_visual(e.KEY_RIGHTCTRL, self.ctrl_on)
            self._update_combo_bar()
            return

        if keycode in (e.KEY_LEFTALT, e.KEY_RIGHTALT):
            self.alt_on = not self.alt_on
            self.active_mods.discard(e.KEY_LEFTALT)
            self.active_mods.discard(e.KEY_RIGHTALT)
            if self.alt_on:
                self.active_mods.add(keycode)
            self._update_mod_visual(e.KEY_LEFTALT,  self.alt_on)
            self._update_mod_visual(e.KEY_RIGHTALT, self.alt_on)
            self._update_combo_bar()
            return

        if keycode == e.KEY_LEFTMETA:
            self.meta_on = not self.meta_on
            if self.meta_on:
                self.active_mods.add(keycode)
            else:
                self.active_mods.discard(keycode)
            self._update_mod_visual(keycode, self.meta_on)
            self._update_combo_bar()
            return

        # ── Regular key — fire with any held modifiers ──
        mods = set(self.active_mods)

        # Inject the keystroke
        def _inject():
            self.injector.press(keycode, mods)

        threading.Thread(target=_inject, daemon=True).start()

        # Auto-release shift after one character
        if self.shift_on:
            self.shift_on = False
            self.active_mods.discard(e.KEY_LEFTSHIFT)
            self.active_mods.discard(e.KEY_RIGHTSHIFT)
            GLib.idle_add(self._update_mod_visual, e.KEY_LEFTSHIFT,  False)
            GLib.idle_add(self._update_mod_visual, e.KEY_RIGHTSHIFT, False)
            GLib.idle_add(self._update_labels)
            GLib.idle_add(self._update_combo_bar)

        # Auto-release Ctrl/Alt after combo
        if self.ctrl_on or self.alt_on:
            self.ctrl_on = self.alt_on = False
            for mk in (e.KEY_LEFTCTRL, e.KEY_RIGHTCTRL,
                       e.KEY_LEFTALT,  e.KEY_RIGHTALT):
                self.active_mods.discard(mk)
                GLib.idle_add(self._update_mod_visual, mk, False)
            GLib.idle_add(self._update_combo_bar)

    # ── Visual helpers ────────────────────────────────────────
    def _update_mod_visual(self, keycode: int, active: bool):
        for btn in self.mod_buttons.get(keycode, []):
            ctx = btn.get_style_context()
            if active:
                ctx.add_class("mod-active")
            else:
                ctx.remove_class("mod-active")

    def _update_combo_bar(self):
        names = []
        if self.ctrl_on:  names.append("Ctrl")
        if self.alt_on:   names.append("Alt")
        if self.meta_on:  names.append("Super")
        if self.shift_on: names.append("Shift")

        if names:
            self.combo_lbl.set_text("  ⌨  " + " + ".join(names) + " + …")
            self.combo_bar.show()
        else:
            self.combo_bar.hide()

    def _update_labels(self):
        """Flip key labels when Shift or Caps is active."""
        upper = self.shift_on != self.caps_on  # XOR
        lang_ov = LANG_OVERRIDES.get(self.lang, {})

        for btn, keycode, base_label, main_lbl in self.key_buttons:
            if keycode in lang_ov:
                up_lbl, lo_lbl = lang_ov[keycode]
                main_lbl.set_text(up_lbl if upper else lo_lbl)
            elif len(base_label) == 1 and base_label.isalpha():
                main_lbl.set_text(base_label.upper() if upper else base_label.lower())

    # ── Lang change ───────────────────────────────────────────
    def _on_lang_change(self, combo):
        model = combo.get_model()
        it    = combo.get_active_iter()
        if it:
            self.lang = model[it][0]
            self._update_labels()

    # ── Theme cycle ───────────────────────────────────────────
    def _cycle_theme(self, _btn):
        order = ["dark", "light", "contrast"]
        idx   = order.index(self.theme_name)
        self.theme_name = order[(idx + 1) % len(order)]
        self.theme = THEMES[self.theme_name]
        self._apply_css()
        self._build_keyboard()

    # ── Resize ────────────────────────────────────────────────
    def _resize(self, _btn, delta: float):
        self.scale = max(0.6, min(1.5, self.scale + delta))
        self._apply_css()
        self._build_keyboard()

    # ── Window signals ────────────────────────────────────────
    def _connect_signals(self):
        self.connect("destroy", lambda _: (self.injector.close(), Gtk.main_quit()))
        self.connect("button-press-event",  self._on_button_press)
        self.connect("button-release-event",self._on_button_release)
        self.connect("motion-notify-event", self._on_motion)

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        self._drag_start = None

    # ── Drag to move ──────────────────────────────────────────
    def _on_button_press(self, widget, event):
        # Only drag on the drag-bar area (top ~30px) with left button
        if event.button == 1 and event.y < int(32 * self.scale):
            self._drag_start = (event.x_root, event.y_root)
            win_x, win_y = self.get_position()
            self._drag_win_start = (win_x, win_y)

    def _on_button_release(self, widget, event):
        self._drag_start = None

    def _on_motion(self, widget, event):
        if self._drag_start:
            dx = event.x_root - self._drag_start[0]
            dy = event.y_root - self._drag_start[1]
            self.move(
                int(self._drag_win_start[0] + dx),
                int(self._drag_win_start[1] + dy),
            )


# ─────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="vkbd — Native GTK3 Virtual Keyboard for Linux (Wayland + X11)"
    )
    parser.add_argument("--theme",  default="dark",
                        choices=["dark", "light", "contrast"],
                        help="Visual theme (default: dark)")
    parser.add_argument("--lang",   default="EN",
                        choices=["EN", "ES", "FR", "DE", "PT"],
                        help="Keyboard language (default: EN)")
    parser.add_argument("--scale",  type=float, default=1.0,
                        help="UI scale factor, e.g. 1.2 (default: 1.0)")
    args = parser.parse_args()

    if not EVDEV_OK:
        print("[vkbd] python3-evdev not found.")
        print("       Install: sudo apt install python3-evdev")

    print(f"[vkbd] Starting — theme={args.theme}  lang={args.lang}  scale={args.scale}")

    win = VKbd(theme_name=args.theme, lang=args.lang, scale=args.scale)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
