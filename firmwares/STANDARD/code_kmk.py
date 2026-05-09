# ============================================================
#   AXION PAD ELITE (STANDARD) — Firmware KMK v1.0.0
#   12 touches (matrice 3×4), 4 potentiomètres
#   Protocole AxionPad Native — compatible AxionPad Configurator
#
#   Prérequis : copier le dossier /kmk/ (depuis kmkfw.io) dans /lib/
#
#   Brochage RP2040 (identique au firmware CircuitPython natif) :
#     Rangées  : GP7 (rang 0), GP6 (rang 1), GP5 (rang 2)
#     Colonnes : GP8, GP9, GP10, GP11
#     ADC      : GP26–GP29
#   Note diode : COL2ROW par défaut
# ============================================================
import sys
import time
import board
import supervisor
import analogio
import usb_hid

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys         import KC
from kmk.scanners     import DiodeOrientation
from kmk.modules      import Module

DEVICE_ID    = "AXIONPAD:STANDARD"
POLL_FAST_MS = 10    # intervalle envoi ADC en mode normal  (ms)
POLL_SLOW_MS = 200   # intervalle envoi ADC en mode POLL:LOW (ms)

# ── ADC ───────────────────────────────────────────────────────
sliders = [
    analogio.AnalogIn(board.GP26),
    analogio.AnalogIn(board.GP27),
    analogio.AnalogIn(board.GP28),
    analogio.AnalogIn(board.GP29),
]

# ── Clavier KMK ──────────────────────────────────────────────
keyboard = KMKKeyboard()
keyboard.col_pins = (board.GP8, board.GP9, board.GP10, board.GP11)
keyboard.row_pins = (board.GP7, board.GP6, board.GP5)
keyboard.diode_orientation = DiodeOrientation.COL2ROW

#            R0                R1                R2
keyboard.keymap = [
    [KC.F13, KC.F14, KC.F15, KC.F16,    # rang 0
     KC.F17, KC.F18, KC.F19, KC.F20,    # rang 1
     KC.F21, KC.F22, KC.F23, KC.F24]    # rang 2
]

# ── Module AxionPad Native ────────────────────────────────────
class AxionNativeModule(Module):
    """Gère le protocole série AxionPad Native en parallèle de KMK."""

    def __init__(self):
        self._buf       = ""
        self._poll_slow = False
        self._last_adc  = -POLL_FAST_MS   # force envoi immédiat
        self._adc_tick  = 0

    def _now_ms(self):
        return supervisor.ticks_ms()

    def during_bootup(self, keyboard):
        time.sleep(0.5)
        print(DEVICE_ID)
        print("AXIONPAD:READY")

    def before_matrix_scan(self, keyboard):
        self._read_serial()
        self._send_adc()

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
        # RGB non câblé sur Elite actuel — commande ignorée silencieusement

    # ── Envoi ADC (même format que firmware CircuitPython natif) ──
    def _send_adc(self):
        interval = POLL_SLOW_MS if self._poll_slow else POLL_FAST_MS
        now = self._now_ms()
        if (now - self._last_adc) >= interval:
            vals = [str(int(s.value / 64)) for s in sliders]
            print("|".join(vals))
            self._last_adc = now

keyboard.modules.append(AxionNativeModule())

if __name__ == "__main__":
    keyboard.go()
