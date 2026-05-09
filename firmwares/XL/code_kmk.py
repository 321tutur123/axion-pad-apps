# ============================================================
#   AXION PAD XL — Firmware KMK v1.0.0
#   15 touches (matrice 5×3), 6 potentiomètres
#   NeoPixel RGB + OLED SSD1306 128×64
#   Protocole AxionPad Native — compatible AxionPad Configurator
#
#   Prérequis : copier le dossier /kmk/ (depuis kmkfw.io) dans /lib/
#
#   Brochage RP2040 :
#     OLED I2C  : SDA=GP0, SCL=GP1
#     Rangées   : GP5 (rang 0), GP6 (rang 1), GP7 (rang 2)
#     Colonnes  : GP8, GP9, GP10, GP11, GP12
#     ADC réels : GP26–GP29 (canaux 0–3)
#     ADC stubs : fixés à 512 (canaux 4–5 — futur MCP3208)
#     NeoPixel  : GP13 (16 LEDs)
#   Note diode : COL2ROW par défaut
# ============================================================
import sys
import time
import math
import board
import supervisor
import analogio
import usb_hid

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys         import KC
from kmk.scanners     import DiodeOrientation
from kmk.modules      import Module

FIRMWARE_VER = "1.0.0"
NUM_LEDS     = 16
POLL_FAST_MS = 10
POLL_SLOW_MS = 200

# ── NeoPixel — détecte automatiquement si les LEDs sont soudées ──
# L'ID annoncé au configurateur dépend du résultat de cette détection.
try:
    import neopixel
    pixels   = neopixel.NeoPixel(board.GP13, NUM_LEDS, brightness=0.8, auto_write=False)
    HAS_RGB  = True
    DEVICE_ID = "AXIONPAD:XL_RGB"
except (ImportError, ValueError, AttributeError):
    HAS_RGB   = False
    DEVICE_ID = "AXIONPAD:XL"

# ── OLED SSD1306 128×64 I2C (optionnel) ──────────────────────
try:
    import busio
    import adafruit_ssd1306
    _i2c  = busio.I2C(board.GP1, board.GP0)
    oled  = adafruit_ssd1306.SSD1306_I2C(128, 64, _i2c)
    HAS_OLED = True
except (ImportError, ValueError, OSError, AttributeError):
    HAS_OLED = False

# ── RTC RP2040 ────────────────────────────────────────────────
try:
    import rtc as _rtc_module
    _rtc    = _rtc_module.RTC()
    HAS_RTC = True
except (ImportError, AttributeError):
    HAS_RTC = False

# ── ADC (4 réels, 2 stubs) ────────────────────────────────────
real_sliders = [
    analogio.AnalogIn(board.GP26),
    analogio.AnalogIn(board.GP27),
    analogio.AnalogIn(board.GP28),
    analogio.AnalogIn(board.GP29),
]

# ── Clavier KMK (5×3 = 15 touches) ───────────────────────────
keyboard = KMKKeyboard()
keyboard.col_pins = (board.GP8, board.GP9, board.GP10, board.GP11, board.GP12)
keyboard.row_pins = (board.GP5, board.GP6, board.GP7)
keyboard.diode_orientation = DiodeOrientation.COL2ROW

#            R0                         R1                         R2
keyboard.keymap = [
    [KC.F13, KC.F14, KC.F15, KC.F16, KC.F17,    # rang 0
     KC.F18, KC.F19, KC.F20, KC.F21, KC.F22,    # rang 1
     KC.F23, KC.F24, KC.APPLICATION, KC.PAUSE, KC.SCROLL_LOCK]  # rang 2
]

# ── Module AxionPad Native ────────────────────────────────────
class AxionNativeModule(Module):
    """Protocole AxionPad Native + RGB + OLED en parallèle de KMK."""

    def __init__(self):
        self._buf        = ""
        self._poll_slow  = False
        self._last_adc   = -POLL_FAST_MS
        # RGB
        self._rgb_mode   = "OFF"
        self._rgb_color1 = (124, 58, 237)
        self._rgb_color2 = (0, 120, 255)
        self._rgb_speed  = 80
        self._rgb_bright = 200
        self._rgb_phase  = 0.0
        # OLED
        self._oled_mode  = "LOGO"
        self._oled_cpu   = -1
        self._oled_gpu   = -1
        self._oled_ctemp = -1
        self._oled_gtemp = -1
        self._oled_ram   = -1
        self._oled_hhmm  = -1
        self._oled_date  = ""
        self._oled_dirty = True
        self._oled_tick  = 0

    # ── Cycle de vie KMK ─────────────────────────────────────
    def during_bootup(self, keyboard):
        time.sleep(0.5)
        print(DEVICE_ID)
        print("AXIONPAD:READY")
        if HAS_OLED:
            self._draw_oled()

    def before_matrix_scan(self, keyboard):
        self._read_serial()
        self._send_adc()

    def after_matrix_scan(self, keyboard): pass

    def before_hid_send(self, keyboard):
        self._tick_rgb()
        self._tick_oled()

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
        elif cmd.startswith("RGB:"):
            self._handle_rgb(cmd[4:])
        elif cmd.startswith("OLED:"):
            self._handle_oled(cmd[5:])
        elif cmd.startswith("SYNC:"):
            self._handle_sync(cmd[5:])

    # ── ADC ──────────────────────────────────────────────────
    def _send_adc(self):
        interval = POLL_SLOW_MS if self._poll_slow else POLL_FAST_MS
        now = supervisor.ticks_ms()
        if (now - self._last_adc) >= interval:
            real = [str(int(s.value / 64)) for s in real_sliders]
            print("|".join(real + ["512", "512"]))
            self._last_adc = now

    # ── RGB ──────────────────────────────────────────────────
    @staticmethod
    def _parse_color(s):
        p = s.split(",")
        return (int(p[0]), int(p[1]), int(p[2]))

    @staticmethod
    def _scale(color, f):
        return tuple(max(0, min(255, int(c * f))) for c in color)

    def _handle_rgb(self, cmd):
        parts = cmd.split(":")
        mode  = parts[0]
        if mode == "OFF":
            self._rgb_mode = "OFF"
        elif mode == "STATIC" and len(parts) >= 2:
            self._rgb_mode   = "STATIC"
            self._rgb_color1 = self._parse_color(parts[1])
        elif mode == "BREATHING" and len(parts) >= 3:
            self._rgb_mode   = "BREATHING"
            self._rgb_color1 = self._parse_color(parts[1])
            self._rgb_speed  = int(parts[2])
        elif mode == "WAVE" and len(parts) >= 4:
            self._rgb_mode   = "WAVE"
            self._rgb_color1 = self._parse_color(parts[1])
            self._rgb_color2 = self._parse_color(parts[2])
            self._rgb_speed  = int(parts[3])
        elif mode == "BRIGHT" and len(parts) >= 2:
            self._rgb_bright = max(0, min(255, int(parts[1])))

    def _tick_rgb(self):
        if not HAS_RGB:
            return
        f = self._rgb_bright / 255.0
        if self._rgb_mode == "OFF":
            pixels.fill((0, 0, 0))
            pixels.show()
        elif self._rgb_mode == "STATIC":
            pixels.fill(self._scale(self._rgb_color1, f))
            pixels.show()
        elif self._rgb_mode == "BREATHING":
            bv = (math.sin(self._rgb_phase) + 1.0) / 2.0
            pixels.fill(self._scale(self._rgb_color1, f * bv))
            pixels.show()
            self._rgb_phase += (self._rgb_speed / 255.0) * 0.05
            if self._rgb_phase > 2 * math.pi:
                self._rgb_phase -= 2 * math.pi
        elif self._rgb_mode == "WAVE":
            step = (2 * math.pi) / NUM_LEDS
            for i in range(NUM_LEDS):
                t = (math.sin(self._rgb_phase + i * step) + 1.0) / 2.0
                r = int(self._rgb_color1[0] * (1 - t) + self._rgb_color2[0] * t)
                g = int(self._rgb_color1[1] * (1 - t) + self._rgb_color2[1] * t)
                b = int(self._rgb_color1[2] * (1 - t) + self._rgb_color2[2] * t)
                pixels[i] = self._scale((r, g, b), f)
            pixels.show()
            self._rgb_phase += (self._rgb_speed / 255.0) * 0.03
            if self._rgb_phase > 2 * math.pi:
                self._rgb_phase -= 2 * math.pi

    # ── OLED ─────────────────────────────────────────────────
    def _handle_oled(self, rest):
        if rest.startswith("MODE:"):
            self._oled_mode  = rest[5:]
            self._oled_dirty = True
        else:
            parts = rest.split(":")
            for i in range(0, len(parts) - 1, 2):
                key, val = parts[i], parts[i + 1]
                if   key == "CPU":   self._oled_cpu   = int(val)
                elif key == "GPU":   self._oled_gpu   = int(val)
                elif key == "CTEMP": self._oled_ctemp = int(val)
                elif key == "GTEMP": self._oled_gtemp = int(val)
                elif key == "RAM":   self._oled_ram   = int(val)
                elif key == "HHMM":  self._oled_hhmm  = int(val)
                elif key == "DATE":  self._oled_date  = val
            self._oled_dirty = True

    def _tick_oled(self):
        if not HAS_OLED:
            return
        # Sync RTC en mode CLOCK
        if HAS_RTC and self._oled_mode == "CLOCK":
            try:
                now = _rtc.datetime
                self._oled_hhmm  = now.tm_hour * 100 + now.tm_min
                self._oled_date  = "{:02d}/{:02d}".format(now.tm_mday, now.tm_mon)
                self._oled_dirty = True
            except Exception:
                pass
        self._oled_tick = (self._oled_tick + 1) % 10
        if self._oled_tick == 0 and self._oled_dirty:
            self._draw_oled()

    def _draw_oled(self):
        if not HAS_OLED:
            return
        self._oled_dirty = False
        try:
            oled.fill(0)
            if self._oled_mode == "LOGO":
                oled.text("  AxionPad XL", 0, 8,  1)
                oled.text("  v" + FIRMWARE_VER,  0, 26, 1)
                oled.text("    Ready",      0, 44, 1)
            elif self._oled_mode == "STATS":
                cpu_s   = "{}%".format(self._oled_cpu)   if self._oled_cpu   >= 0 else "N/A"
                gpu_s   = "{}%".format(self._oled_gpu)   if self._oled_gpu   >= 0 else "N/A"
                ctemp_s = "{}C".format(self._oled_ctemp) if self._oled_ctemp >= 0 else "N/A"
                gtemp_s = "{}C".format(self._oled_gtemp) if self._oled_gtemp >= 0 else "N/A"
                ram_s   = "{}%".format(self._oled_ram)   if self._oled_ram   >= 0 else "N/A"
                oled.text("CPU {} T:{}".format(cpu_s, ctemp_s), 0, 0,  1)
                oled.text("GPU {} T:{}".format(gpu_s, gtemp_s), 0, 14, 1)
                oled.text("RAM {}".format(ram_s),               0, 28, 1)
                if self._oled_hhmm >= 0:
                    h = self._oled_hhmm // 100
                    m = self._oled_hhmm % 100
                    oled.text("{:02d}:{:02d}".format(h, m), 44, 48, 1)
            elif self._oled_mode == "CLOCK":
                if self._oled_hhmm >= 0:
                    h = self._oled_hhmm // 100
                    m = self._oled_hhmm % 100
                    oled.text("   {:02d}:{:02d}".format(h, m), 0, 18, 1)
                if self._oled_date:
                    oled.text("  " + self._oled_date,          0, 40, 1)
            oled.show()
        except Exception:
            pass  # OLED non câblé — ignorer

    # ── RTC SYNC ─────────────────────────────────────────────
    def _handle_sync(self, rest):
        if not HAS_RTC:
            return
        try:
            p = rest.split(":")
            _rtc.datetime = time.struct_time((
                int(p[0]), int(p[1]), int(p[2]),
                int(p[3]), int(p[4]), int(p[5]),
                0, -1, -1))
        except Exception:
            pass

keyboard.modules.append(AxionNativeModule())

if __name__ == "__main__":
    keyboard.go()
