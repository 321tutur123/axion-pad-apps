# ============================================================
#   AXION PAD MINI RGB — Firmware KMK v1.0.0 (avec NeoPixel)
#   6 touches (matrice 2×3), RGB WS2812B sur GP4
#   Utilisez code_kmk.py si vous n'avez PAS soudé les LEDs.
#
#   Prérequis : copier /kmk/ dans /lib/ sur le volume CIRCUITPY
# ============================================================
import sys
import time
import math
import board
import supervisor
import usb_hid
import neopixel

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys         import KC
from kmk.scanners     import DiodeOrientation
from kmk.modules      import Module

DEVICE_ID = "AXIONPAD:MINI_RGB"
NUM_LEDS  = 6

pixels = neopixel.NeoPixel(board.GP4, NUM_LEDS, brightness=0.8, auto_write=False)

keyboard = KMKKeyboard()
keyboard.col_pins = (board.GP7, board.GP8, board.GP9)
keyboard.row_pins = (board.GP6, board.GP5)
keyboard.diode_orientation = DiodeOrientation.COL2ROW

keyboard.keymap = [
    [KC.F13, KC.F14, KC.F15,
     KC.F16, KC.F17, KC.F18]
]

class AxionNativeModule(Module):
    def __init__(self):
        self._buf        = ""
        self._poll_slow  = False
        self._rgb_mode   = "OFF"
        self._rgb_color1 = (124, 58, 237)
        self._rgb_color2 = (0, 120, 255)
        self._rgb_speed  = 80
        self._rgb_bright = 200
        self._rgb_phase  = 0.0

    def during_bootup(self, keyboard):
        time.sleep(0.5)
        print(DEVICE_ID)
        print("AXIONPAD:READY")

    def before_matrix_scan(self, keyboard):
        self._read_serial()

    def after_matrix_scan(self, keyboard): pass

    def before_hid_send(self, keyboard):
        self._tick_rgb()

    def after_hid_send(self, keyboard):    pass
    def on_powersave_enable(self, keyboard):  pass
    def on_powersave_disable(self, keyboard): pass

    def _read_serial(self):
        while supervisor.runtime.serial_bytes_available:
            ch = sys.stdin.read(1)
            if ch in ('\n', '\r'):
                cmd = self._buf.strip()
                self._buf = ""
                if cmd: self._handle(cmd)
            else:
                self._buf += ch

    def _handle(self, cmd):
        if cmd == "WHO_ARE_YOU":
            print(DEVICE_ID)
        elif cmd == "POLL:LOW":
            self._poll_slow = True
        elif cmd == "POLL:HIGH":
            self._poll_slow = False
        elif cmd.startswith("RGB:"):
            self._handle_rgb(cmd[4:])

    def _handle_rgb(self, cmd):
        parts = cmd.split(":")
        mode  = parts[0]
        if mode == "OFF":
            self._rgb_mode = "OFF"
        elif mode == "STATIC" and len(parts) >= 2:
            self._rgb_mode = "STATIC"; self._rgb_color1 = self._pc(parts[1])
        elif mode == "BREATHING" and len(parts) >= 3:
            self._rgb_mode = "BREATHING"; self._rgb_color1 = self._pc(parts[1]); self._rgb_speed = int(parts[2])
        elif mode == "WAVE" and len(parts) >= 4:
            self._rgb_mode = "WAVE"; self._rgb_color1 = self._pc(parts[1]); self._rgb_color2 = self._pc(parts[2]); self._rgb_speed = int(parts[3])
        elif mode == "BRIGHT" and len(parts) >= 2:
            self._rgb_bright = max(0, min(255, int(parts[1])))

    @staticmethod
    def _pc(s):
        p = s.split(","); return (int(p[0]), int(p[1]), int(p[2]))

    @staticmethod
    def _sc(color, f):
        return tuple(max(0, min(255, int(c * f))) for c in color)

    def _tick_rgb(self):
        f = self._rgb_bright / 255.0
        if self._rgb_mode == "OFF":
            pixels.fill((0, 0, 0)); pixels.show()
        elif self._rgb_mode == "STATIC":
            pixels.fill(self._sc(self._rgb_color1, f)); pixels.show()
        elif self._rgb_mode == "BREATHING":
            bv = (math.sin(self._rgb_phase) + 1.0) / 2.0
            pixels.fill(self._sc(self._rgb_color1, f * bv)); pixels.show()
            self._rgb_phase += (self._rgb_speed / 255.0) * 0.05
            if self._rgb_phase > 2 * math.pi: self._rgb_phase -= 2 * math.pi
        elif self._rgb_mode == "WAVE":
            step = (2 * math.pi) / NUM_LEDS
            for i in range(NUM_LEDS):
                t = (math.sin(self._rgb_phase + i * step) + 1.0) / 2.0
                r = int(self._rgb_color1[0] * (1-t) + self._rgb_color2[0] * t)
                g = int(self._rgb_color1[1] * (1-t) + self._rgb_color2[1] * t)
                b = int(self._rgb_color1[2] * (1-t) + self._rgb_color2[2] * t)
                pixels[i] = self._sc((r, g, b), f)
            pixels.show()
            self._rgb_phase += (self._rgb_speed / 255.0) * 0.03
            if self._rgb_phase > 2 * math.pi: self._rgb_phase -= 2 * math.pi

keyboard.modules.append(AxionNativeModule())

if __name__ == "__main__":
    keyboard.go()
