// ============================================================
//  AXION PAD MINI — Définition de la matrice
// ============================================================
#pragma once

#include "quantum.h"

// Mapping physique → position matrice
// Rangée 0 : K00 K01 K02
// Rangée 1 : K10 K11 K12
#define LAYOUT( \
    K00, K01, K02, \
    K10, K11, K12  \
) { \
    { K00, K01, K02 }, \
    { K10, K11, K12 }  \
}

// Pins lignes (GP6=0, GP5=1)
#define MATRIX_ROW_PINS { GP6, GP5 }

// Pins colonnes (GP7, GP8, GP9)
#define MATRIX_COL_PINS { GP7, GP8, GP9 }
