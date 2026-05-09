# ============================================================
#   AXION PAD MINI — Firmware KMK v1.0.0
#   6 touches (matrice 2×3), 0 potentiomètre, pas de RGB
#   Protocole AxionPad Native — compatible AxionPad Configurator
#
#   Prérequis : copier le dossier /kmk/ (depuis kmkfw.io) dans /lib/
#
#   Brochage RP2040 (identique au firmware CircuitPython natif) :
#     Rangées  : GP6 (rang 0), GP5 (rang 1)
#     Colonnes : GP7, GP8, GP9
#   Note diode : COL2ROW par défaut — si les touches sont inversées,
#                changer en DiodeOrientation.ROW2COL
# ============================================================
import sys
import time
import board
import supervisor
import usb_hid

from kmk.kmk_keyboard  import KMKKeyboard
from kmk.keys          import KC
from kmk.scanners      import DiodeOrientation
from kmk.modules       import Module
from adafruit_hid.keyboard import Keyboard as _HIDKeyboard   # noqa — chargé par KMK

DEVICE_ID = "AXIONPAD:MINI"

# ── Clavier KMK ──────────────────────────────────────────────
keyboard = KMKKeyboard()
keyboard.col_pins = (board.GP7, board.GP8, board.GP9)
keyboard.row_pins = (board.GP6, board.GP5)
keyboard.diode_orientation = DiodeOrientation.COL2ROW

# Rangée 0 : F13 F14 F15 | Rangée 1 : F16 F17 F18
keyboard.keymap = [
    [KC.F13, KC.F14, KC.F15,
     KC.F16, KC.F17, KC.F18]
]

# ── Module AxionPad Native ────────────────────────────────────
class AxionNativeModule(Module):
    """Gère le protocole série AxionPad Native en parallèle de KMK."""

    def __init__(self):
        self._buf      = ""
        self._poll_slow = False
        self._greeted  = False

    # ── Cycle de vie KMK ─────────────────────────────────────
    def during_bootup(self, keyboard):
        time.sleep(0.5)
        print(DEVICE_ID)
        print("AXIONPAD:READY")
        self._greeted = True

    def before_matrix_scan(self, keyboard):
        self._read_serial()

    def after_matrix_scan(self, keyboard): pass
    def before_hid_send(self, keyboard):   pass
    def after_hid_send(self, keyboard):    pass
    def on_powersave_enable(self, keyboard):  pass
    def on_powersave_disable(self, keyboard): pass

    # ── Lecture série non-bloquante ──────────────────────────
    def _read_serial(self):
        while supervisor.runtime.serial_bytes_available:
            ch = sys.stdin.read(1)
            if ch in ('\n', '\r'):
                cmd = self._buf.strip()
                self._buf = ""
                if cmd:
                    self._handle(cmd)
            else:
                self._buf += ch

    def _handle(self, cmd):
        if cmd == "WHO_ARE_YOU":
            print(DEVICE_ID)
        elif cmd == "POLL:LOW":
            self._poll_slow = True
        elif cmd == "POLL:HIGH":
            self._poll_slow = False
        # Mini n'a pas de RGB ni d'OLED — commandes ignorées silencieusement

keyboard.modules.append(AxionNativeModule())

if __name__ == "__main__":
    keyboard.go()
