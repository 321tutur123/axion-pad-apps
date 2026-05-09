// ============================================================
//  AXION PAD MINI — Keymap par défaut
//  6 touches → F13–F18 (interceptés par AxionPad Configurator)
// ============================================================
#include QMK_KEYBOARD_H

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    //        Col 0    Col 1    Col 2
    [0] = LAYOUT(
        KC_F13,  KC_F14,  KC_F15,   // Rangée 0 (GP6)
        KC_F16,  KC_F17,  KC_F18    // Rangée 1 (GP5)
    ),
};
