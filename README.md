# 🃏 [Yu-Gi-Oh] Master Duel Coach APP // Alpha version

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Interface: Mobalytics Style](https://img.shields.io/badge/UI-Blitz.gg%20%2F%20Mobalytics-purple.svg)]()
[![Languages](https://img.shields.io/badge/Languages-ES%20%7C%20EN%20%7C%20FR%20%7C%20DE%20%7C%20IT-green.svg)]()

> **Asistente táctico visual inteligente en tiempo real para Yu-Gi-Oh! Master Duel.**  
> Diseñado con una interfaz flotante moderna estilo Blitz.gg / Mobalytics: visualiza tus mejores jugadas, rutas de combo paso a paso con miniaturas de cartas y alertas de respuesta del oponente sin entorpecer tu pantalla.

---

## 🌟 Características Principales

- ⭐ **Hero Card (Jugada Recomendada):**
  - Muestra la mejor jugada prioritaria con ilustración de la carta a gran resolución, porcentaje de EV (Expected Value) y explicación táctica paso a paso.
- ⚡ **Ruta de Combo Interactiva:**
  - 4 tarjetas secuenciales con miniaturas reales de las cartas del combo. Al hacer clic en cualquier paso, previsualiza la carta y su efecto.
- 🃏 **Detección de Mano en Tiempo Real:**
  - Reconocimiento visual de las cartas en tu mano con distintivos de color oficiales (Monstruo, Magia, Trampa, Enlace, Xyz, Fusión, Sincronía) y etiquetas de acción táctica (*JUGAR AHORA*, *Extensión*, *Guardar*).
- 🛡️ **Radar Táctico y Alertas de Oponente:**
  - Avisos preventivos sobre posibles interrupciones enemigas (Ash Blossom, Nibiru, Infinite Impermanence).
- 🌐 **Soporte Multilingüe (5 Idiomas):**
  - Cambio instantáneo con un solo clic entre **Español (ES)**, **Inglés (EN)**, **Francés (FR)**, **Alemán (DE)** e **Italiano (IT)** en la interfaz y en el motor de visión.
- 📖 **Visor Integrado de Estrategias:**
  - Consulta planes de juego, side decking y guías completas del mazo en una ventana oscura dentro de la app sin abrir el navegador ni salir del duelo.

---

## 🚀 Instalación y Puesta en Marcha

### 1. Requisitos Previos
- **Windows 10 / 11**
- **Python 3.10 o superior** ([Descargar Python](https://www.python.org/downloads/))
- **Yu-Gi-Oh! Master Duel** (en ventana sin bordes o modo ventana para un funcionamiento óptimo del overlay)

### 2. Clonar el Repositorio
`ash
git clone git@github.com:Hyloozsgamer/yugioh-master-duel-coach.git
cd yugioh-master-duel-coach
`

### 3. Instalar Dependencias
`ash
pip install -r requirements.txt
`
*(o instalar las librerías principales: pip install google-genai pillow opencv-python pygetwindow pyautogui)*

### 4. Configurar tu API Key
1. Copia el archivo .env.example y renómbralo a .env:
   `ash
   cp .env.example .env
   `
2. Abre .env y pega tu clave gratuita de Google Gemini (puedes obtener una en [Google AI Studio](https://aistudio.google.com/)).

### 5. Iniciar el Coach
Haz doble clic en:
`at
INICIAR_COACH_EN_VIVO.bat
`
¡O ejecuta directamente desde la consola:
`ash
python coach_live_overlay.py
`

---

## 🖥️ Arquitectura del Proyecto

`	ext
├── coach/
│   ├── live_brain.py       # Motor táctico de visión y análisis de duelos
│   ├── i18n.py             # Sistema de traducción (ES, EN, FR, DE, IT)
│   └── ...
├── decks_estrategias/      # Guías tácticas y rutas de combo por mazo
├── master_duel/
│   ├── database/
│   │   └── ygo_cards.db    # Base de datos SQLite local de cartas Yu-Gi-Oh
│   └── vision/             # Módulos de captura y procesamiento de pantalla
├── coach_live_overlay.py   # HUD Overlay flotante principal (Mobalytics UI)
├── INICIAR_COACH_EN_VIVO.bat # Lanzador rápido para Windows
├── .env.example            # Plantilla para claves de entorno
└── README.md
`

---

## 📜 Licencia

Distribuido bajo la Licencia **MIT**. Consulta el archivo LICENSE para más información.

---

## ⚠️ Descargo de Responsabilidad (Disclaimer)

*Yu-Gi-Oh! y Master Duel son marcas registradas de **Konami Digital Entertainment** y **Studio Dice / SHUEISHA, TV TOKYO**. Este proyecto es una herramienta de coaching independiente creada por la comunidad con fines educativos y de entrenamiento. No está respaldada, afiliada ni asociada formalmente con Konami.*
