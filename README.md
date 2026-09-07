<p align="center">
  <img src="assets/banner.png" alt="Yu-Gi-Oh! Master Duel Coach APP Banner" width="100%" />
</p>

<h1 align="center">👁️ [Yu-Gi-Oh] Master Duel Coach APP // Alpha version</h1>

<p align="center">
  <i>«¡No confíes solo en la suerte! El verdadero duelista forja su propio destino combinando el Corazón de las Cartas con la tecnología táctica más avanzada del Milenio.»</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/KAIBA_CORP-APPROVED-0052FF?style=for-the-badge" />
  <img src="https://img.shields.io/badge/MILLENNIUM_EYE-TACTICAL_AI-FFD700?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/LICENSE-MIT-green?style=for-the-badge" />
</p>

<p align="center">
  <b>🌐 Multilingual Engine:</b>
  <code>[ES] Español</code> • 
  <code>[EN] English</code> • 
  <code>[FR] Français</code> • 
  <code>[DE] Deutsch</code> • 
  <code>[IT] Italiano</code>
</p>

---

> ### 💬 *«¡ES HORA DEL DU-DU-DU-DUELO!»*
> **Duel Master Coach** es un HUD táctico inteligente en tiempo real que se proyecta sobre **Yu-Gi-Oh! Master Duel**. Inspirado en interfaces modernas de e-sports de élite (*Mobalytics / Blitz.gg*) y en los legendarios sistemas holográficos de KaibaCorp: analiza tu mano, calcula probabilidades (EV), traza rutas de invocación paso a paso y te alerta de las trampas e interrupciones del rival antes de que caigas en ellas.

---

## ⚡ CAPÍTULO I: EL OJO DEL MILENIO (Características Tácticas)

```
       ┌──────────────────────────────────────────────────────────┐
       │   KAIBACORP LIVE TACTICAL RADAR                          │
       │   [⭐ HERO PLAY] ───► [⚡ 4-STEP COMBO] ───► [🛡️ ALERT]   │
       │   [🃏 HAND SENSOR: MONSTER 4 | SPELL 1 | TRAP 0]        │
       └──────────────────────────────────────────────────────────┘
```

### 1. ⭐ Carta Heroica (Tu Jugada Ganadora)
- **Arte en Alta Definición:** Muestra la carta prioritaria con su ilustración oficial a gran tamaño.
- **Cálculo de EV% (Expected Value):** Mide el impacto ofensivo y la viabilidad de la jugada.
- **Veredicto del Coach:** Instrucciones precisas (*«Invoca de Modo Normal, activa su efecto para buscar tu iniciador»*).

### 2. ⚡ Ruta de Combo en Cadena (4 Pasos Holográficos)
- Sin diagramas confusos: **4 cartas secuenciales con miniaturas reales**.
- Al hacer clic en cualquier paso del combo, el HUD actualiza la vista previa y detalla el efecto para que nunca te pierdas en combos largos.

### 3. 🃏 Escáner de Mano en Tiempo Real (Visión por IA)
- Detección inmediata de tu mano con bordes y distintivos oficiales:
  - 🟠 **Monstruo de Efecto** | 🟢 **Mágica** | 🟣 **Trampa** | 🔵 **Ritual** | ⚪ **Sincronía** | ⚫ **Xyz** | 🔷 **Enlace**
- Etiquetas tácticas dinámicas: `👉 JUGAR AHORA`, `⚡ Extensión`, `🛡️ Guardar`.

### 4. 🛡️ Radar de Interrupciones Enemigas
- ¡Que no te sorprenda el Reino de las Sombras! Detecta ventanas de peligro enemigas (*Ash Blossom & Joyous Spring*, *Maxx "C"*, *Nibiru, the Primal Being*, *Infinite Impermanence*).

### 5. 📖 Grimorio de Estrategias Integrado
- Consulta la biblia de tu mazo (guía completa, prioridades, side decking) en una ventana flotante oscura sin tener que salir del juego ni abrir navegadores pesados.

---

## 🔮 CAPÍTULO II: RITUAL DE INVOCACIÓN (Instalación)

### 1. Requisitos del Duelista
- **Sistema Operativo:** Windows 10 u 11 (64-bit).
- **Python:** 3.10 o superior ([Descargar aquí](https://www.python.org/downloads/)).
- **Yu-Gi-Oh! Master Duel:** Configurado preferiblemente en *Ventana sin bordes* o *Modo Ventana*.

### 2. Invocación desde la Terminal
Clona el repositorio sagrado en tu máquina:
```bash
git clone git@github.com:Hyloozsgamer/yugioh-master-duel-coach.git
cd yugioh-master-duel-coach
```

Instala los componentes mágicos y tecnológicos:
```bash
pip install -r requirements.txt
```

### 3. Despertar el Núcleo de Gemini AI
1. Duplica la plantilla de entorno:
   ```bash
   cp .env.example .env
   ```
2. Abre `.env` e ingresa tu clave gratuita de Google Gemini (obtenible en [Google AI Studio](https://aistudio.google.com/)):
   ```env
   GEMINI_API_KEY=tu_clave_secreta_aqui
   ```

### 4. ¡A Jugar! (Lanzador Rápido)
Haz doble clic en el archivo ejecutable:
```bat
INICIAR_COACH_EN_VIVO.bat
```
*(O ejecútalo por consola con `python coach_live_overlay.py`)*

---

## 🏛️ CAPÍTULO III: MAPA ARQUITECTÓNICO

```text
📦 yugioh-master-duel-coach
 ┣ 📂 assets/                # Banners e ilustraciones estilo manga
 ┣ 📂 coach/                 # Núcleo neuronal del asistente
 ┃ ┣ 📜 live_brain.py        # Motor de visión multimodal y análisis de jugadas
 ┃ ┗ 📜 i18n.py              # Diccionario políglota (ES / EN / FR / DE / IT)
 ┣ 📂 decks_estrategias/     # Guías tácticas y rutas de combo por arquetipo
 ┣ 📂 master_duel/           # Base de datos SQLite y visión del juego
 ┃ ┗ 📂 database/ygo_cards.db# Registro de passcodes e ilustraciones de cartas
 ┣ 📜 coach_live_overlay.py  # HUD flotante interactivo (Mobalytics UI)
 ┣ 📜 INICIAR_COACH_EN_VIVO.bat # Lanzador en 1 clic para duelistas
 ┣ 📜 requirements.txt       # Dependencias necesarias
 ┗ 📜 README.md              # Este pergamino sagrado
```

---

## ⚖️ CAPÍTULO IV: DESCARGO SAGRADO (Disclaimer)

> *Yu-Gi-Oh!, Yu-Gi-Oh! Master Duel y todos sus elementos gráficos asociados son marcas registradas de **KONAMI Digital Entertainment**, **Kazuki Takahashi** y **Studio Dice / SHUEISHA, TV TOKYO**.*  
> 
> *Este proyecto es una herramienta de asistencia táctica creada por y para la comunidad con propósitos exclusivamente educativos, analíticos y de entretenimiento. No está afiliada ni respaldada oficialmente por Konami.*

---

<p align="center">
  <sub>Hecho con pasión por duelistas para duelistas. <b>¡Cree en tu mazo y que comience el duelo!</b></sub>
</p>
