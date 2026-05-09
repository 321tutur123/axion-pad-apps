# ── Build QMK pour RP2040 ────────────────────────────────────
MCU = RP2040
BOOTLOADER = rp2040

# Features essentielles
KEYBOARD_SHARED_EP = yes
CONSOLE_ENABLE     = yes   # crée le port COM CDC reconnu par le configurateur
NKRO_ENABLE        = yes   # N-key rollover

# Features désactivées (Mini = simplicité maximale)
MOUSEKEY_ENABLE    = no
EXTRAKEY_ENABLE    = no
AUDIO_ENABLE       = no
RGBLIGHT_ENABLE    = no
BACKLIGHT_ENABLE   = no
ENCODER_ENABLE     = no

# Output : .uf2 pour flash RP2040 via BOOTSEL
