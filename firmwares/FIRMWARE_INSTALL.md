# Installation des firmwares alternatifs

## CircuitPython natif (par défaut)

Aucune installation supplémentaire. Le configurateur exporte `code.py` directement sur le volume `CIRCUITPY`.

---

## KMK Firmware

Compatible avec tous les modèles (Mini, Elite, XL).

### Prérequis sur le pad

1. CircuitPython 8.x ou 9.x déjà installé
2. Bibliothèques Adafruit (normalement déjà présentes dans `/lib/`) :
   - `adafruit_hid`
   - `adafruit_matrixkeypad`
   - `adafruit_ssd1306` (XL uniquement)
3. Bibliothèque KMK — à télécharger depuis [kmkfw.io](https://kmkfw.io) :
   - Télécharger le `.zip` et copier le dossier `kmk/` dans `/lib/` sur le volume `CIRCUITPY`

### Flash

1. Brancher le pad (volume `CIRCUITPY` visible)
2. Copier le fichier `code_kmk.py` correspondant à ton modèle sur le volume
3. **Renommer-le en `code.py`** (remplace l'ancien)
4. Le pad redémarre automatiquement avec KMK

### Différences vs CircuitPython natif

| Fonctionnalité | CircuitPython natif | KMK |
|---|---|---|
| Touches HID | ✓ | ✓ |
| Potentiomètres (sliders) | ✓ | ✓ |
| Protocole AxionPad Native | ✓ | ✓ |
| RGB (XL) | ✓ | ✓ |
| OLED (XL) | ✓ | ✓ |
| Layers KMK avancés | — | ✓ |
| Tap-Dance, Combos | — | ✓ |
| Rotation d'encodeur | — | ✓ (avec module) |

### Retour au firmware CircuitPython natif

Copier le `code.py` original depuis ce dépôt (`firmwares/MODELE/code.py`) sur le volume `CIRCUITPY`.

---

## QMK Firmware (Mini uniquement)

### Prérequis

- [QMK CLI](https://docs.qmk.fm/newbs_getting_started) installé (`qmk setup`)
- Python 3.9+ et ARM toolchain (installés automatiquement par `qmk setup`)

### Installation

```bash
# 1. Cloner QMK
qmk setup

# 2. Copier les sources dans QMK
cp -r firmwares/MINI/qmk ~/.local/share/qmk/firmware/keyboards/axionpad/mini

# 3. Compiler
qmk compile -kb axionpad/mini -km default

# 4. Flasher
#    Maintenir BOOTSEL enfoncé en branchant le Mini → volume RPI-RP2 visible
#    Copier le fichier .uf2 généré sur le volume
cp ~/.local/share/qmk/firmware/axionpad_mini_default.uf2 /media/$USER/RPI-RP2/
```

### Protocole AxionPad Native en QMK

Le firmware QMK expose un port CDC Serial (COM) que le configurateur reconnaît :
- Envoie `AXIONPAD:MINI` + `AXIONPAD:READY` au démarrage
- Répond `AXIONPAD:MINI` à `WHO_ARE_YOU`
- Pas de valeurs ADC (Mini n'a pas de potentiomètres)
- Pas de RGB ni d'OLED sur le Mini

### Retour au firmware CircuitPython

1. Maintenir BOOTSEL en branchant
2. Copier le `.uf2` CircuitPython 8.x depuis [circuitpython.org/downloads](https://circuitpython.org/downloads)
3. Le volume `CIRCUITPY` réapparaît
4. Copier `firmwares/MINI/code.py` dessus

---

## Compatibilité configurateur

Tous les firmwares envoient le même message d'identification (`AXIONPAD:MINI`, `AXIONPAD:STANDARD`, `AXIONPAD:XL`) sur le port série. Le configurateur les détecte automatiquement.
