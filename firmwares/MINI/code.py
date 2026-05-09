# ============================================================
#   AXION PAD MINI — Firmware v2.0.0
#   6 touches (matrice 2×3), 0 potentiomètre, pas de RGB/OLED
#   Protocole : Device_ID au démarrage + touches HID F13–F18
#
#   Brochage RP2040 :
#     Rangées : GP6 (rang 0), GP5 (rang 1)
#     Colonnes : GP7, GP8, GP9
# ============================================================
import time
import sys
import board
import digitalio
import adafruit_matrixkeypad
import usb_hid
import supervisor
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

DEVICE_ID    = "AXIONPAD:MINI"
FIRMWARE_VER = "2.0.0"

# ── Matrice 2×3 ───────────────────────────────────────────────
rows = [digitalio.DigitalInOut(x) for x in (board.GP6, board.GP5)]
cols = [digitalio.DigitalInOut(x) for x in (board.GP7, board.GP8, board.GP9)]
key_matrix = [[1, 2, 3], [4, 5, 6]]
keypad = adafruit_matrixkeypad.Matrix_Keypad(rows, cols, key_matrix)

kbd = Keyboard(usb_hid.devices)

# Touches fixes F13–F18 — l'appli hôte intercepte et traduit
KEY_MAP = {
    0: [Keycode.F13], 1: [Keycode.F14], 2: [Keycode.F15],
    3: [Keycode.F16], 4: [Keycode.F17], 5: [Keycode.F18],
}

# ── Broadcast identité modèle (lu au démarrage par le configurateur) ──
time.sleep(0.5)
print(DEVICE_ID)
print("AXIONPAD:READY")

last_pressed = set()
poll_slow    = False
_cmd_buf     = ""

# ─────────────────────────────────────────────────────────────
while True:
    # ── Commandes série entrantes (non-bloquant) ─────────────
    while supervisor.runtime.serial_bytes_available:
        ch = sys.stdin.read(1)
        if ch in ('\n', '\r'):
            cmd = _cmd_buf.strip()
            _cmd_buf = ""
            if cmd == "WHO_ARE_YOU":
                print(DEVICE_ID)
            elif cmd == "POLL:LOW":
                poll_slow = True
            elif cmd == "POLL:HIGH":
                poll_slow = False
        else:
            _cmd_buf += ch

    # ── Matrice touches ──────────────────────────────────────
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

    time.sleep(2.0 if poll_slow else 0.01)
