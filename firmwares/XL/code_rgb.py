# ============================================================
#   AXION PAD XL RGB — Firmware v2.1.0 (avec LEDs NeoPixel)
#   15 touches (matrice 5×3), 6 canaux ADC, OLED, RGB WS2812B
#   Utilisez code.py si vous n'avez PAS soudé les LEDs.
#
#   Brochage RP2040 :
#     OLED I2C  : SDA=GP0, SCL=GP1
#     Rangées   : GP5 (0), GP6 (1), GP7 (2)
#     Colonnes  : GP8, GP9, GP10, GP11, GP12
#     ADC réels : GP26–GP29  (canaux 0–3)
#     ADC stubs : fixés à 512 (canaux 4–5)
#     NeoPixel  : GP13 (16 LEDs)
# ============================================================
import time
import sys
import math
import board
import busio
import digitalio
import analogio
import adafruit_matrixkeypad
import usb_hid
import supervisor
import neopixel
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

DEVICE_ID    = "AXIONPAD:XL_RGB"
FIRMWARE_VER = "2.1.0"
NUM_KEYS     = 15
NUM_LEDS     = 16

# ── NeoPixel ──────────────────────────────────────────────────
pixels = neopixel.NeoPixel(board.GP13, NUM_LEDS, brightness=0.8, auto_write=False)

# ── OLED SSD1306 128×64 I2C (optionnel) ──────────────────────
try:
    import adafruit_ssd1306
    _i2c = busio.I2C(board.GP1, board.GP0)
    oled = adafruit_ssd1306.SSD1306_I2C(128, 64, _i2c)
    HAS_OLED = True
except (ImportError, ValueError, OSError, AttributeError):
    HAS_OLED = False

# ── RTC RP2040 ────────────────────────────────────────────────
try:
    import rtc as _rtc_module
    _rtc = _rtc_module.RTC()
    HAS_RTC = True
except (ImportError, AttributeError):
    HAS_RTC = False

# ── Matrice 5×3 ───────────────────────────────────────────────
rows = [digitalio.DigitalInOut(x) for x in (board.GP5, board.GP6, board.GP7)]
cols = [digitalio.DigitalInOut(x) for x in (board.GP8, board.GP9, board.GP10, board.GP11, board.GP12)]
key_matrix = [[1,2,3,4,5], [6,7,8,9,10], [11,12,13,14,15]]
keypad = adafruit_matrixkeypad.Matrix_Keypad(rows, cols, key_matrix)

# ── ADC (4 réels, 2 stubs) ────────────────────────────────────
real_sliders = [
    analogio.AnalogIn(board.GP26),
    analogio.AnalogIn(board.GP27),
    analogio.AnalogIn(board.GP28),
    analogio.AnalogIn(board.GP29),
]

kbd = Keyboard(usb_hid.devices)

KEY_MAP = {
    0:  [Keycode.F13], 1:  [Keycode.F14], 2:  [Keycode.F15], 3:  [Keycode.F16], 4:  [Keycode.F17],
    5:  [Keycode.F18], 6:  [Keycode.F19], 7:  [Keycode.F20], 8:  [Keycode.F21], 9:  [Keycode.F22],
    10: [Keycode.F23], 11: [Keycode.F24], 12: [Keycode.APPLICATION],
    13: [Keycode.PAUSE], 14: [Keycode.SCROLL_LOCK],
}

# ── État RGB ──────────────────────────────────────────────────
rgb_mode   = "OFF"
rgb_color1 = (124, 58, 237)
rgb_color2 = (0, 120, 255)
rgb_speed  = 80
rgb_bright = 200
rgb_phase  = 0.0

# ── État OLED ─────────────────────────────────────────────────
oled_mode  = "LOGO"
oled_cpu   = oled_ram = oled_hhmm = -1
oled_gpu   = oled_ctemp = oled_gtemp = -1
oled_date  = ""
oled_dirty = True
_oled_tick = 0

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

def _update_oled():
    global oled_dirty
    if not HAS_OLED or not oled_dirty: return
    oled_dirty = False
    try:
        oled.fill(0)
        if oled_mode == "LOGO":
            oled.text("  AxionPad XL", 0, 8, 1)
            oled.text("  v" + FIRMWARE_VER, 0, 26, 1)
            oled.text("    Ready", 0, 44, 1)
        elif oled_mode == "STATS":
            oled.text("CPU {}%  T:{}C".format(
                oled_cpu   if oled_cpu   >= 0 else "N/A",
                oled_ctemp if oled_ctemp >= 0 else "N/A"), 0, 0, 1)
            oled.text("GPU {}%  T:{}C".format(
                oled_gpu   if oled_gpu   >= 0 else "N/A",
                oled_gtemp if oled_gtemp >= 0 else "N/A"), 0, 14, 1)
            oled.text("RAM {}%".format(oled_ram if oled_ram >= 0 else "N/A"), 0, 28, 1)
            if oled_hhmm >= 0:
                oled.text("{:02d}:{:02d}".format(oled_hhmm // 100, oled_hhmm % 100), 44, 48, 1)
        elif oled_mode == "CLOCK":
            if oled_hhmm >= 0:
                oled.text("   {:02d}:{:02d}".format(oled_hhmm // 100, oled_hhmm % 100), 0, 18, 1)
            if oled_date:
                oled.text("  " + oled_date, 0, 40, 1)
        oled.show()
    except Exception:
        pass

def _process_command(cmd):
    global rgb_mode, rgb_color1, rgb_color2, rgb_speed, rgb_bright
    global poll_slow, oled_mode, oled_dirty
    global oled_cpu, oled_gpu, oled_ctemp, oled_gtemp, oled_ram, oled_hhmm, oled_date
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
        elif cmd.startswith("OLED:"):
            rest = cmd[5:]
            if rest.startswith("MODE:"):
                oled_mode = rest[5:]; oled_dirty = True
            else:
                parts = rest.split(":")
                for i in range(0, len(parts) - 1, 2):
                    key, val = parts[i], parts[i+1]
                    if   key == "CPU":   oled_cpu   = int(val)
                    elif key == "GPU":   oled_gpu   = int(val)
                    elif key == "CTEMP": oled_ctemp = int(val)
                    elif key == "GTEMP": oled_gtemp = int(val)
                    elif key == "RAM":   oled_ram   = int(val)
                    elif key == "HHMM":  oled_hhmm  = int(val)
                    elif key == "DATE":  oled_date  = val
                oled_dirty = True
        elif cmd.startswith("SYNC:"):
            if HAS_RTC:
                p = cmd[5:].split(":")
                _rtc.datetime = time.struct_time((
                    int(p[0]), int(p[1]), int(p[2]),
                    int(p[3]), int(p[4]), int(p[5]),
                    0, -1, -1))
    except Exception:
        pass

# ── Init ──────────────────────────────────────────────────────
time.sleep(0.5)
print(DEVICE_ID)
print("AXIONPAD:READY")
if HAS_OLED:
    _update_oled()

last_pressed = set()
poll_slow    = False
_cmd_buf     = ""
_adc_tick    = 0

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

    if not poll_slow or _adc_tick == 0:
        real = [str(int(s.value / 64)) for s in real_sliders]
        print("|".join(real + ["512", "512"]))
    _adc_tick = (_adc_tick + 1) % 200

    _update_rgb()

    if HAS_RTC and HAS_OLED and oled_mode == "CLOCK":
        try:
            now = _rtc.datetime
            oled_hhmm = now.tm_hour * 100 + now.tm_min
            oled_date = "{:02d}/{:02d}".format(now.tm_mday, now.tm_mon)
            oled_dirty = True
        except Exception:
            pass

    _oled_tick = (_oled_tick + 1) % 10
    if _oled_tick == 0:
        _update_oled()

    time.sleep(0.01)
