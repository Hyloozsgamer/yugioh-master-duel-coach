# Yu-Gi-Oh! Master Duel Coach - Release v0.01

Primera versión oficial de **Yu-Gi-Oh! Master Duel Live Coach (HUD)**.
Un asistente táctico en tiempo real diseñado para guiarte en duelos y escenarios de Modo Solo con precisión de torneo, estética manga Cyber/KaibaCorp y cero latencia perceptible.

---

## Novedades Principales en la v0.01

### 1. Live HUD KaibaCorp (Manga Cyberpunk)
* Interfaz acoplada al lateral de Master Duel (340x768 px).
* Paleta futurista con modo oscuro profundo (`#040711`), acentos en cian neón (`#00F5FF`) y detalles dorados.
* Visualizador de fase de duelo, nivel de amenaza rival y medidor de Win Equity (% EV).

### 2. Captura Directa por HWND (PrintWindow)
* Captura de pantalla nativa de Windows directamente desde el identificador de ventana de `masterduel.exe`.
* Captura fiable y nítida incluso si la ventana del juego queda cubierta por navegadores u otras aplicaciones.

### 3. Motor de Visión Táctica con IA (Gemini Robotics Preview)
* Integración del modelo de alta disponibilidad y cuota activa `gemini-robotics-er-2-preview`.
* Escaneo dual simultáneo: analiza tanto el tablero completo como un recorte ampliado en alta definición de las cartas en mano.
* Sistema de protección de cuota inteligente: cooldown de 15 segundos en modo automático para evitar errores HTTP 429.
* Tecla rápida global **F5** y botón dedicado para escaneos manuales inmediatos.

### 4. Hero Card: Jugada Inmediata Fiable
* Identificación exacta de la carta en mano a jugar ahora mismo.
* Procedimiento detallado en cliente paso a paso (ej. *"1. Haz clic en 'Exormana Marta' en mano -> 2. Pulsa Activar -> 3. Invoca a Elis"*).
* Motivo táctico de la jugada y porcentaje de ventaja de victoria.
* Resaltado visual en la lista de mano con borde cian y distintivo `[JUGAR AHORA]`.

### 5. Línea de Combo en 4 Nodos Z
* Cronología vertical interactiva con 4 fases:
  1. **Inicio:** Starter y activación inicial.
  2. **Extensión:** Búsqueda o invocación especial secundaria.
  3. **Extra Deck:** Invocación de Xyz, Sincronía, Fusión o Enlace.
  4. **Remate:** Control de mesa, trampas o batalla.

### 6. Dossiers de Estrategia Nivel Torneo
* Generación y persistencia de guías completas en `decks_estrategias/`:
  - Condición de victoria (*Win Condition*).
  - Starters y combos legales de 1 carta.
  - Línea Turno 1 (Going 1st) y Turno 2 (Going 2nd / OTK).
  - Interrupciones en el turno rival.
  - Guía Anti-IA específica para escenarios de Modo Solo Konami.
* Visor enriquecido con títulos coloreados, pasos destacados y botón para copiar la guía completa al portapapeles.

### 7. Soporte Multilingüe Completo (i18n)
* Conmutador dinámico en tiempo real para 5 idiomas:
  - Español (`ES`)
  - English (`EN`)
  - Français (`FR`)
  - Deutsch (`DE`)
  - Italiano (`IT`)

---

## Instalación y Uso Rápido

1. Clona el repositorio:
   ```bash
   git clone git@github.com:Hyloozsgamer/yugioh-master-duel-coach.git
   cd yugioh-master-duel-coach
   ```
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura tu clave de Gemini en el archivo `.env`:
   ```env
   GEMINI_API_KEY=tu_clave_aqui
   ```
4. Inicia Master Duel y ejecuta el Coach:
   - Haz doble clic en `INICIAR_COACH_EN_VIVO.bat` o ejecuta:
     ```bash
     python coach_live_overlay.py
     ```
5. Pulsa **F5** dentro de Master Duel para escanear en cualquier momento.
