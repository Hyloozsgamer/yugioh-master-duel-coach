"""
Live Vision & Reasoning Engine for Master Duel Head Coach.
Incluye:
- Detección y análisis completo de Decks en Modo Solo / Confirmación de Baraja.
- Generación de Guía de Estrategia (.json y .md) guardada en decks_estrategias/.
- Inyección de baraja registrada en el análisis de duelo para CERO alucinaciones.
- Detección en vivo ultra-rápida (0.25s).
"""

import os
import sys
import time
import json
import base64
import urllib.request
import urllib.error
import cv2
import numpy as np
from typing import Optional, Dict, Any, List

class LiveVisionCoach:
    def __init__(self, db=None):
        self.db = db
        self.api_key = self._load_api_key()
        self.models_pool = [
            "gemini-flash-lite-latest",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite"
        ]
        self.current_model_idx = 0
        self._last_call_time = 0.0
        self._min_call_interval = 0.6
        self._last_frame_hash = None
        self._pending_frame_hash = None
        self._sct = None
        self.active_deck = self._load_latest_deck()  # Carga baraja previa escaneada si existe
        self._init_capture()

    def _load_api_key(self) -> str:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
        return os.environ.get("GEMINI_API_KEY", "")

    def _attach_to_desktop(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            DESKTOP_ALL = 0x01FF
            hdesk = user32.OpenDesktopW("default", 0, False, DESKTOP_ALL)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    def _init_capture(self):
        self._attach_to_desktop()
        try:
            import mss
            self._sct = mss.MSS()
        except Exception:
            self._sct = None

    def _find_masterduel_hwnd(self) -> Optional[int]:
        try:
            import ctypes
            import ctypes.wintypes
            import psutil

            user32 = ctypes.windll.user32
            found_hwnd = None

            def cb(hwnd, _):
                nonlocal found_hwnd
                if user32.IsWindowVisible(hwnd):
                    pid = ctypes.wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    try:
                        p = psutil.Process(pid.value)
                        if "masterduel" in p.name().lower():
                            found_hwnd = hwnd
                    except Exception:
                        pass
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(cb), 0)
            return found_hwnd
        except Exception:
            return None

    def bring_game_to_front(self):
        """Trae la ventana de Master Duel al frente para garantizar captura limpia."""
        hwnd = self._find_masterduel_hwnd()
        if hwnd:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                user32.keybd_event(0x12, 0, 0, 0)
                user32.SetForegroundWindow(hwnd)
                user32.keybd_event(0x12, 0, 2, 0)
                user32.ShowWindow(hwnd, 9)
                time.sleep(0.35)
            except Exception:
                pass

    def capture_game_screen(self) -> Optional[np.ndarray]:
        self._attach_to_desktop()
        if self._sct is None:
            try:
                import mss
                self._sct = mss.MSS()
            except Exception:
                return None

        hwnd = self._find_masterduel_hwnd()
        if hwnd:
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                if user32.IsIconic(hwnd):
                    return None
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w >= 400 and h >= 300:
                    mon = {"top": rect.top, "left": rect.left, "width": w, "height": h}
                    shot = self._sct.grab(mon)
                    img = np.array(shot, dtype=np.uint8)[:, :, :3]
                    if np.mean(img) > 2.0:
                        return img
            except Exception:
                pass

        try:
            mon = self._sct.monitors[0]
            shot = self._sct.grab(mon)
            img = np.array(shot, dtype=np.uint8)[:, :, :3]
            if np.mean(img) > 2.0:
                return img
        except Exception:
            pass

        return None

    def _has_frame_changed(self, frame: np.ndarray) -> bool:
        h, w = frame.shape[:2]
        roi_hand = frame[int(h * 0.70):int(h * 0.98), int(w * 0.18):int(w * 0.85)]
        roi_center = frame[int(h * 0.20):int(h * 0.75), int(w * 0.20):int(w * 0.80)]
        
        sample = np.concatenate([cv2.resize(roi_hand, (35, 18)), cv2.resize(roi_center, (35, 18))])
        frame_hash = hash(sample.tobytes())
        
        self._pending_frame_hash = frame_hash
        return self._last_frame_hash is None or frame_hash != self._last_frame_hash

    def commit_frame_hash(self):
        if self._pending_frame_hash is not None:
            self._last_frame_hash = self._pending_frame_hash

    def analyze_deck_screen(self, frame: np.ndarray, lang: str = 'ES') -> Optional[Dict[str, Any]]:
        """
        Escanea la pantalla de baraja o Puerta de Modo Solo en Master Duel,
        extrae cartas/arquetipo, genera la estrategia y la guarda en disco.
        """
        if not self.api_key or frame is None:
            return None

        h, w = frame.shape[:2]
        resized = cv2.resize(frame, (1024, int(h * 1024 / w)))
        _, buf = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64_img = base64.b64encode(buf).decode("utf-8")

        lang_names = {'ES': 'Español', 'EN': 'English', 'FR': 'Français', 'DE': 'Deutsch', 'IT': 'Italiano'}
        target_lang = lang_names.get(str(lang).upper(), 'Español')

        prompt = f"""Eres el Head Coach profesional y gran estratega de Yu-Gi-Oh! Master Duel.
El usuario ha configurado el asistente en: {target_lang}.
La imagen muestra la pantalla de Master Duel (Modo Solo: Puerta, selección de duelo o cuadrícula de cartas del Deck de Préstamo). El juego puede estar en cualquier idioma (Español, Inglés, Francés, Alemán, Italiano o Japonés).

REGLAS DE PRECISIÓN Y CERO ALUCINACIONES:
1. Lee los nombres EXACTOS de las cartas visibles y tradúcelos/preséntalos en {target_lang}.
2. Incluye para cada carta también su nombre canónico en inglés ('name_en') para vincular la base de datos de cartas.
2. NUNCA inventes nombres ni pongas textos genéricos como 'Monstruos Cantantes', 'Monstruos de Sincronía', 'Starter 1' o 'Busca-recursos'. Pon nombres reales y completos de cartas de Yu-Gi-Oh.
3. Extrae con precisión:
   - Starters reales con los que iniciar el Turno 1 (monstruos de Nivel bajo o buscadores).
   - Monstruos Cantantes (Tuners) y sus niveles (si es baraja de Sincronía), o extensores de Invocación Especial (si es Enlace/Xyz).
   - Monstruos Jefe del Extra Deck presentes en la baraja.
   - Magias y Trampas de soporte clave (ej: Agujero Oscuro, Tifón, trampas de interrupción).
4. Genera una GUÍA TÁCTICA INTUITIVA Y ACCIONABLE:
   - Fórmula matemática y combo exacto (ej: 'Nivel 2 (Buscador) + Cantante Nivel 3 (Defensor) = Sincronía Nivel 5 (Catastor)').
   - Cómo contrarrestar al deck del rival de este escenario (ej: efectos contra monstruos de LUZ, destrucción sin cálculo de daño, etc.).
5. Especifica los 4 NODOS EXACTOS de la secuencia Z con CARTAS REALES:

Devuelve SIEMPRE un JSON válido con este esquema:
{
  "is_deck_screen": true,
  "is_loaner": true,
  "screen_type": "SOLO_GATE / LOANER_DECK",
  "deck_name": "Nombre Real de la Baraja",
  "archetype": "Arquetipo Principal",
  "total_cards_estimated": 40,
  "loaner_tip": "Consejo táctico directo y concreto para ganar este duelo contra la IA",
  "key_starters": ["Nombre Exacto Carta 1", "Nombre Exacto Carta 2"],
  "tuners_or_extenders": ["Nombre Exacto Cantante/Extensor 1"],
  "extra_deck_cards": ["Nombre Exacto Jefe Extra 1", "Nombre Exacto Jefe Extra 2"],
  "support_spells_traps": ["Magia/Trampa Clave 1"],
  "z_nodes": [
    {"node": 1, "phase": "1. INICIO", "card": "Nombre Real Starter", "action": "Invocación Normal (Nivel/Efecto inicial)", "ev": 98},
    {"node": 2, "phase": "2. EXTENSIÓN", "card": "Nombre Real Cantante/Extensor", "action": "Invocación Especial o Cantante", "ev": 94},
    {"node": 3, "phase": "3. EXTRA DECK", "card": "Nombre Real Monstruo Extra", "action": "Invocación por Sincronía/Enlace/Xyz", "ev": 96},
    {"node": 4, "phase": "4. REMATE", "card": "Nombre Real Jefe o Trampa", "action": "Control de mesa / Victoria", "ev": 95}
  ],
  "strategy": {
    "win_condition": "Objetivo táctico principal para ganar la partida...",
    "combo_steps": [
      "1. [Paso 1 con nombres de cartas exactas y niveles/acciones]",
      "2. [Paso 2]",
      "3. [Paso 3]",
      "4. [Paso 4]"
    ],
    "end_board": "Campo final recomendado y recursos preparados...",
    "ideal_hand": ["Carta 1", "Carta 2"]
  }
}"""

        for attempt in range(len(self.models_pool)):
            idx = (self.current_model_idx + attempt) % len(self.models_pool)
            model_name = self.models_pool[idx]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}}
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1000}
            }

            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    if "```json" in text:
                        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
                    elif "```" in text:
                        text = text.split("```", 1)[1].split("```", 1)[0].strip()
                    parsed = json.loads(text)
                    self.current_model_idx = idx
                    
                    if parsed.get("is_deck_screen") or parsed.get("key_starters") or parsed.get("strategy"):
                        parsed["is_deck_screen"] = True
                        self.active_deck = parsed
                        self._save_deck_and_strategy(parsed)
                    return parsed
            except Exception:
                continue

        return None

    def _save_deck_and_strategy(self, deck_data: Dict[str, Any]):
        """Guarda la baraja y su estrategia en disco en decks_estrategias."""
        try:
            base_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "decks_estrategias")
            os.makedirs(base_folder, exist_ok=True)

            d_name = deck_data.get("deck_name", "Deck_Personalizado").replace(" ", "_").replace("★", "").replace("☆", "")
            d_name = "".join(c for c in d_name if c.isalnum() or c in "_-")
            if not d_name:
                d_name = "Deck_Estrategia"

            json_path = os.path.join(base_folder, f"{d_name}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(deck_data, f, ensure_ascii=False, indent=2)

            strat = deck_data.get("strategy", {})
            is_loaner = deck_data.get("is_loaner", True)
            loaner_badge = "🎮 Baraja de Préstamo (Modo Solo Konami)" if is_loaner else "🛡️ Baraja Personal"
            loaner_tip = deck_data.get("loaner_tip", "Sigue los combos pensados por Konami para este escenario.")

            tuners_str = ", ".join(deck_data.get("tuners_or_extenders", [])) or "Extensores temáticos del arquetipo"
            extra_str = ", ".join(deck_data.get("extra_deck_cards", [])) or "Jefes del Extra Deck"
            spells_str = ", ".join(deck_data.get("support_spells_traps", [])) or "Recursos de limpieza y protección"

            md_content = f"""# 🧠 Guía Táctica y Estratégica: {deck_data.get('deck_name', 'Baraja de Préstamo')}
**Modalidad:** {loaner_badge} | **Arquetipo:** {deck_data.get('archetype', 'General')}

---

## 🎯 Condición de Victoria (Win Condition)
{strat.get('win_condition', 'Construir presencia en mesa y agotar los recursos del rival.')}

---

## 🃏 Cartas Clave del Mazo
- **⚡ Starters (Apertura Turno 1):** {", ".join(deck_data.get('key_starters', []))}
- **🔄 Cantantes / Extensores:** {tuners_str}
- **👑 Jefes del Extra Deck:** {extra_str}
- **🛡️ Magias y Trampas de Soporte:** {spells_str}

---

## 🔄 Secuencia de Combo Óptima (Paso a Paso)
"""
            for step in strat.get("combo_steps", []):
                md_content += f"- {step}\n"

            md_content += f"""
---

## 🛡️ Campo Final Ideal (End Board)
{strat.get('end_board', 'Monstruos jefes y trampas preparadas para el turno rival.')}

---

## 💡 Consejo Táctico para Vencer a la IA de este Escenario
{loaner_tip}
"""

            md_path = os.path.join(base_folder, f"{d_name}_estrategia.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            deck_data["saved_json_path"] = json_path
            deck_data["saved_md_path"] = md_path
        except Exception:
            pass

    
    def _load_latest_deck(self) -> Optional[Dict[str, Any]]:
        """Carga la baraja mas reciente escaneada en decks_estrategias si existe."""
        try:
            base_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "decks_estrategias")
            if not os.path.exists(base_folder):
                return None
            json_files = [os.path.join(base_folder, f) for f in os.listdir(base_folder) if f.endswith(".json")]
            if not json_files:
                return None
            full_decks = []
            for jf in json_files:
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("main_deck_cards") or data.get("key_starters"):
                        full_decks.append((os.path.getmtime(jf), len(data.get("main_deck_cards", [])), data))
                except Exception:
                    pass
            if full_decks:
                # Priorizar decks completos (40+ cartas) y luego fecha
                full_decks.sort(key=lambda x: (x[1] >= 40, x[0]), reverse=True)
                return full_decks[0][2]
        except Exception:
            pass
        return None

    def analyze_live_duel(self, frame: np.ndarray, lang: str = 'ES') -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None

        now = time.time()
        if now - self._last_call_time < self._min_call_interval:
            return None

        self._last_call_time = now
        h, w = frame.shape[:2]

        full_resized = cv2.resize(frame, (720, int(h * 720 / w)))
        _, full_buf = cv2.imencode(".jpg", full_resized, [cv2.IMWRITE_JPEG_QUALITY, 68])
        b64_full = base64.b64encode(full_buf).decode("utf-8")

        hand_crop = frame[int(h * 0.68):int(h * 0.98), int(w * 0.18):int(w * 0.85)]
        hand_resized = cv2.resize(hand_crop, (540, int(hand_crop.shape[0] * 540 / hand_crop.shape[1])))
        _, hand_buf = cv2.imencode(".jpg", hand_resized, [cv2.IMWRITE_JPEG_QUALITY, 78])
        b64_hand = base64.b64encode(hand_buf).decode("utf-8")

        card_preview = frame[int(h * 0.12):int(h * 0.88), int(w * 0.01):int(w * 0.25)]
        prev_resized = cv2.resize(card_preview, (280, int(card_preview.shape[0] * 280 / card_preview.shape[1])))
        _, prev_buf = cv2.imencode(".jpg", prev_resized, [cv2.IMWRITE_JPEG_QUALITY, 78])
        b64_prev = base64.b64encode(prev_buf).decode("utf-8")

        # Inyectar baraja activa si existe para CERO alucinaciones
        deck_context = ""
        if self.active_deck:
            d_name = self.active_deck.get("deck_name", "Préstamo Modo Solo")
            starters = ", ".join(self.active_deck.get("key_starters", []))
            extra = ", ".join(self.active_deck.get("extra_deck_cards", []))
            is_loaner = self.active_deck.get("is_loaner", True)
            loaner_label = "BARAJA DE PRÉSTAMO DE KONAMI (MODO SOLO)" if is_loaner else "BARAJA DEL JUGADOR"
            deck_context = f"""
{loaner_label} ({d_name}):
- Starters incluidos en el préstamo: {starters}
- Extra Deck del préstamo: {extra}
REGLA CRUCIAL: Estás jugando con una BARAJA DE PRÉSTAMO. Recomienda ÚNICAMENTE jugadas posibles con las cartas que Konami entrega en este préstamo. No asumas staples competitivas de fuera."""

        lang_names = {'ES': 'Español', 'EN': 'English', 'FR': 'Français', 'DE': 'Deutsch', 'IT': 'Italiano'}
        target_lang = lang_names.get(str(lang).upper(), 'Español')

        system_prompt = f"""Eres el Head Coach profesional de Yu-Gi-Oh! Master Duel.
El usuario tiene configurado el Asistente en idioma: {target_lang}.
El juego en pantalla de Master Duel puede estar en cualquiera de los idiomas soportados (Español, Inglés, Francés, Alemán, Italiano, etc.).
{deck_context}

REGLAS ESTRICTAS DE FIDELIDAD (PROHIBIDO INVENTAR):
1. Redacta todas tus recomendaciones, nombres de jugada, advertencias y pasos del turno en {target_lang}.
1. Si la imagen NO muestra una partida real de Master Duel (ej: escritorio, YouTube o navegador), responde:
   {{"in_duel": false, "status_message": "Master Duel no esta visible en pantalla"}}
2. SOLO reporta cartas que veas FISICAMENTE en la mano o en el campo del jugador en espanol.
3. NUNCA INVENTES CARTAS QUE EL JUGADOR NO TIENE. Si ves 2 cartas en mano, 'hand_cards' debe tener exactamente esas 2 cartas.
4. Para la secuencia de 4 pasos en Z:
   - Nodo 1: Carta en mano a jugar primero y su accion.
   - Nodo 2: Siguiente paso legal (carta en mano o efecto derivado de la primera).
   - Nodo 3: Transicion o Extra Deck si esta disponible.
   - Nodo 4: Objetivo de fin de turno (ej: "Avanzar a Battle Phase", "Colocar Trampa Set" o "Pasar Turno").
   - Si no hay 4 cartas diferentes, usa acciones reales como "Avanzar a Battle Phase" o "Pasar Turno", PERO NUNCA INVENTES NOMBRES DE CARTAS QUE NO TIENE.

Devuelve SOLO JSON valido:
{{
  "in_duel": true,
  "active_modal": "Descripcion del modal si hay uno abierto o null",
  "hand_cards": [
    {{"slot": 1, "name": "Nombre Exacto en Espanol", "play_index": "1º", "is_optimal": true}}
  ],
  "opponent_board": {{
    "monsters_count": 0,
    "monsters_summary": "Descripcion del campo rival",
    "spells_traps_count": 0,
    "threat_level": "BAJO/MEDIO/ALTO"
  }},
  "neural_sequence": [
    {{"node": 1, "phase": "1. INICIO", "card": "Nombre Carta Real", "action": "Accion Inmediata", "ev": 96, "status": "ACTIVE"}},
    {{"node": 2, "phase": "2. EXTENSIÓN", "card": "Siguiente Paso", "action": "Efecto o Carta", "ev": 92, "status": "PENDING"}},
    {{"node": 3, "phase": "3. ENLACE", "card": "Extra Deck o Acción", "action": "Transición", "ev": 89, "status": "PENDING"}},
    {{"node": 4, "phase": "4. REMATE", "card": "Objetivo", "action": "Control o Pasar Turno", "ev": 95, "status": "PENDING"}}
  ],
  "recommended_play": {{
    "card_name": "Nombre de la Carta del Nodo 1",
    "action": "Accion exacta en cliente",
    "win_equity_pct": 96,
    "reason_why": ["Motivo 1", "Motivo 2"],
    "client_procedure": ["Paso 1", "Paso 2"]
  }}
}}"""

        for attempt in range(len(self.models_pool)):
            idx = (self.current_model_idx + attempt) % len(self.models_pool)
            model_name = self.models_pool[idx]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": system_prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": b64_full}},
                            {"inline_data": {"mime_type": "image/jpeg", "data": b64_hand}},
                            {"inline_data": {"mime_type": "image/jpeg", "data": b64_prev}}
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1200}
            }

            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    if "```json" in text:
                        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
                    elif "```" in text:
                        text = text.split("```", 1)[1].split("```", 1)[0].strip()
                    parsed = json.loads(text)
                    self.current_model_idx = idx
                    return parsed
            except Exception:
                continue

        return None
