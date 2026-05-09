// ============================================================
//  AXION PAD MINI — QMK config
//  RP2040 · 6 touches (matrice 2×3) · USB HID + CDC Serial
//  Compatible AxionPad Configurator (protocole AxionPad Native)
// ============================================================
#pragma once

// ── Identité USB ─────────────────────────────────────────────
#define VENDOR_ID    0x2E8A   // Raspberry Pi / RP2040 — reconnu par l'auto-connect de l'app
#define PRODUCT_ID   0x0003
#define DEVICE_VER   0x0100
#define MANUFACTURER "AxionPad"
#define PRODUCT      "Axion Pad Mini"

// ── Matrice 2 lignes × 3 colonnes ────────────────────────────
// Brochage identique au firmware CircuitPython natif
// Lignes  : GP6, GP5
// Colonnes: GP7, GP8, GP9
#define MATRIX_ROWS 2
#define MATRIX_COLS 3

// Orientation diode COL2ROW (même que KMK)
#define DIODE_DIRECTION COL2ROW

// ── Timings ──────────────────────────────────────────────────
#define DEBOUNCE 5

// ── Console CDC (crée le port COM reconnu par le configurateur) ─
#define CONSOLE_ENABLE

// ── Désactiver les features inutiles pour réduire la taille ──
#undef LOCKING_SUPPORT_ENABLE
#undef LOCKING_RESYNC_ENABLE
