# ============================================================
#   AXION PAD MINI RGB — Firmware v1.0.0 (avec LEDs NeoPixel)
#   6 touches (matrice 2×3), RGB WS2812B
#   Utilisez code.py si vous n'avez PAS soudé les LEDs.
#
#   Brochage RP2040 :
#     Rangées  : GP6 (rang 0), GP5 (rang 1)
#     Colonnes : GP7, GP8, GP9
#     NeoPixel : GP4 (6 LEDs — une par touche)
#                Adaptez NUM_LEDS si votre câblage est différent.
# ============================================================
import time
import sys
import math
import board
import digitalio
import adafruit_matrixkeypad
import usb_hid
import supervisor
import neopixel
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

DEVICE_ID = "AXIONPAD:MINI_RGB"
NUM_LEDS  = 6

# ── NeoPixel ──────────────────────────────────────────────────
pixels = neopixel.NeoPixel(board.GP4, NUM_LEDS, brightness=0.8, auto_write=False)

# ── Matrice 2×3 ───────────────────────────────────────────────
rows = [digitalio.DigitalInOut(x) for x in (board.GP6, board.GP5)]
cols = [digitalio.DigitalInOut(x) for x in (board.GP7, board.GP8, board.GP9)]
key_matrix = [[1, 2, 3], [4, 5, 6]]
keypad = adafruit_matrixkeypad.Matrix_Keypad(rows, cols, key_matrix)

kbd = Keyboard(usb_hid.devices)

KEY_MAP = {
    0: [Keycode.F13], 1: [Keycode.F14], 2: [Keycode.F15],
    3: [Keycode.F16], 4: [Keycode.F17], 5: [Keycode.F18],
}

# ── État RGB ──────────────────────────────────────────────────
rgb_mode   = "OFF"
rgb_color1 = (124, 58, 237)
rgb_color2 = (0, 120, 255)
rgb_speed  = 80
rgb_bright = 200
rgb_phase  = 0.0

def _parse_color(s):
    p = s.split(",")
    return (int(p[0]), int(p[1]), int(p[2]))

def _scale(color, f):
    return tuple(max(0, min(255, int(c * f))) for c in color)

def _update_rgb():
    global rgb_phase
    f = rgb_bright / 255.0
    if rgb_mode == "OFF":
        pixels.fill((0, 0, 0)); pixels.show()
    elif rgb_mode == "STATIC":
        pixels.fill(_scale(rgb_color1, f)); pixels.show()
    elif rgb_mode == "BREATHING":
        bv = (math.sin(rgb_phase) + 1.0) / 2.0
        pixels.fill(_scale(rgb_color1, f * bv)); pixels.show()
        rgb_phase += (rgb_speed / 255.0) * 0.05
        if rgb_phase > 2 * math.pi: rgb_phase -= 2 * math.pi
    elif rgb_mode == "WAVE":
        step = (2 * math.pi) / NUM_LEDS
        for i in range(NUM_LEDS):
            t = (math.sin(rgb_phase + i * step) + 1.0) / 2.0
            r = int(rgb_color1[0] * (1-t) + rgb_color2[0] * t)
            g = int(rgb_color1[1] * (1-t) + rgb_color2[1] * t)
            b = int(rgb_color1[2] * (1-t) + rgb_color2[2] * t)
            pixels[i] = _scale((r, g, b), f)
        pixels.show()
        rgb_phase += (rgb_speed / 255.0) * 0.03
        if rgb_phase > 2 * math.pi: rgb_phase -= 2 * math.pi

def _process_command(cmd):
    global rgb_mode, rgb_color1, rgb_color2, rgb_speed, rgb_bright, poll_slow
    try:
        if cmd == "WHO_ARE_YOU":
            print(DEVICE_ID)
        elif cmd == "POLL:LOW":
            poll_slow = True
        elif cmd == "POLL:HIGH":
            poll_slow = False
        elif cmd.startswith("RGB:"):
            parts = cmd[4:].split(":")
            mode = parts[0]
            if mode == "OFF":
                rgb_mode = "OFF"
            elif mode == "STATIC" and len(parts) >= 2:
                rgb_mode = "STATIC"; rgb_color1 = _parse_color(parts[1])
            elif mode == "BREATHING" and len(parts) >= 3:
                rgb_mode = "BREATHING"; rgb_color1 = _parse_color(parts[1]); rgb_speed = int(parts[2])
            elif mode == "WAVE" and len(parts) >= 4:
                rgb_mode = "WAVE"; rgb_color1 = _parse_color(parts[1]); rgb_color2 = _parse_color(parts[2]); rgb_speed = int(parts[3])
            elif mode == "BRIGHT" and len(parts) >= 2:
                rgb_bright = max(0, min(255, int(parts[1])))
    except Exception:
        pass

# ── Init ──────────────────────────────────────────────────────
time.sleep(0.5)
print(DEVICE_ID)
print("AXIONPAD:READY")

last_pressed = set()
poll_slow    = False
_cmd_buf     = ""

# ─────────────────────────────────────────────────────────────
while True:
    while supervisor.runtime.serial_bytes_available:
        ch = sys.stdin.read(1)
        if ch in ('\n', '\r'):
            cmd = _cmd_buf.strip()
            _cmd_buf = ""
            if cmd: _process_command(cmd)
        else:
            _cmd_buf += ch

    cur = set(keypad.pressed_keys)
    for k in cur - last_pressed:
        idx = k - 1
        if idx in KEY_MAP: kbd.press(*KEY_MAP[idx])
    for k in last_pressed - cur:
        idx = k - 1
        if idx in KEY_MAP: kbd.release(*KEY_MAP[idx])
    last_pressed = cur

    _update_rgb()

    time.sleep(2.0 if poll_slow else 0.01)
