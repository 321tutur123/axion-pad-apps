# ============================================================
#   AXION PAD STANDARD (Elite) — Firmware v2.1.0
#   12 touches (matrice 3×4), 4 potentiomètres
#   Brochage RP2040 :
#     Rangées  : GP7 (0), GP6 (1), GP5 (2)
#     Colonnes : GP8, GP9, GP10, GP11
#     ADC      : GP26–GP29
# ============================================================
import time
import sys
import board
import digitalio
import analogio
import adafruit_matrixkeypad
import usb_hid
import supervisor
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

DEVICE_ID    = "AXIONPAD:STANDARD"
FIRMWARE_VER = "2.1.0"
NUM_KEYS     = 12
NUM_SLIDERS  = 4

# ── Matrice 3×4 ───────────────────────────────────────────────
cols = [digitalio.DigitalInOut(x) for x in (board.GP8, board.GP9, board.GP10, board.GP11)]
rows = [digitalio.DigitalInOut(x) for x in (board.GP7, board.GP6, board.GP5)]
key_matrix = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
keypad = adafruit_matrixkeypad.Matrix_Keypad(rows, cols, key_matrix)

# ── ADC ───────────────────────────────────────────────────────
sliders = [
    analogio.AnalogIn(board.GP26),
    analogio.AnalogIn(board.GP27),
    analogio.AnalogIn(board.GP28),
    analogio.AnalogIn(board.GP29),
]

kbd = Keyboard(usb_hid.devices)

KEY_MAP = {
    0: [Keycode.F13], 1: [Keycode.F14], 2:  [Keycode.F15], 3:  [Keycode.F16],
    4: [Keycode.F17], 5: [Keycode.F18], 6:  [Keycode.F19], 7:  [Keycode.F20],
    8: [Keycode.F21], 9: [Keycode.F22], 10: [Keycode.F23], 11: [Keycode.F24],
}

def _process_command(cmd):
    global poll_slow
    try:
        if cmd == "WHO_ARE_YOU":
            print(DEVICE_ID)
        elif cmd == "POLL:LOW":
            poll_slow = True
        elif cmd == "POLL:HIGH":
            poll_slow = False
    except (ValueError, IndexError):
        pass

# ── Init ──────────────────────────────────────────────────────
time.sleep(0.5)
print(DEVICE_ID)
print("AXIONPAD:READY")

last_pressed = set()
poll_slow    = False
_cmd_buf     = ""
_adc_tick    = 0

while True:
    # ── Commandes série entrantes ────────────────────────────
    while supervisor.runtime.serial_bytes_available:
        ch = sys.stdin.read(1)
        if ch in ('\n', '\r'):
            cmd = _cmd_buf.strip()
            _cmd_buf = ""
            if cmd:
                _process_command(cmd)
        else:
            _cmd_buf += ch

    # ── Touches ─────────────────────────────────────────────
    cur = set(keypad.pressed_keys)
    for k in cur - last_pressed:
        idx = k - 1
        if idx in KEY_MAP:
            kbd.press(*KEY_MAP[idx])
    for k in last_pressed - cur:
        idx = k - 1
        if idx in KEY_MAP:
            kbd.release(*KEY_MAP[idx])
    last_pressed = cur

    # ── ADC → sortie AxionPad Native ────────────────────────
    if not poll_slow or _adc_tick == 0:
        vals = [str(int(s.value / 64)) for s in sliders]
        print("|".join(vals))
    _adc_tick = (_adc_tick + 1) % 200

    time.sleep(0.01)
