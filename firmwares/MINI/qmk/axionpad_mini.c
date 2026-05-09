// ============================================================
//  AXION PAD MINI — Code clavier QMK
//  Gère le protocole AxionPad Native via la console CDC
// ============================================================
#include "axionpad_mini.h"
#include <string.h>
#include <stdio.h>

#define DEVICE_ID "AXIONPAD:MINI"

// ── Greeting envoyé une fois au démarrage ────────────────────
// Le configurateur lit ce message pour identifier le modèle
void keyboard_post_init_user(void) {
    wait_ms(500);
    // Écriture directe sur le port console CDC
    printf(DEVICE_ID "\n");
    printf("AXIONPAD:READY\n");
}

// ── Réception de commandes série ─────────────────────────────
// Lecture non-bloquante de la console CDC.
// Pour le Mini (pas de potentiomètres, pas de RGB), seule la
// réponse à WHO_ARE_YOU est nécessaire.
static char _rx_buf[64];
static uint8_t _rx_pos = 0;

void housekeeping_task_user(void) {
    // Lecture caractère par caractère (non-bloquant)
    int16_t ch;
    while ((ch = virtser_recv()) != -1) {
        if (ch == '\n' || ch == '\r') {
            _rx_buf[_rx_pos] = '\0';
            if (_rx_pos > 0) {
                // Traitement de la commande
                if (strcmp(_rx_buf, "WHO_ARE_YOU") == 0) {
                    printf(DEVICE_ID "\n");
                }
                // POLL:LOW / POLL:HIGH — pas de potentiomètres sur Mini,
                // accepter silencieusement pour compatibilité
            }
            _rx_pos = 0;
        } else if (_rx_pos < sizeof(_rx_buf) - 1) {
            _rx_buf[_rx_pos++] = (char)ch;
        }
    }
}
