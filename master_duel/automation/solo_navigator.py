"""
Solo Mode Navigator for Yu-Gi-Oh! Master Duel
Navega automáticamente por el Modo Solo (PvE):
- Acceso a Puertas de Historia y Prácticas.
- Progreso continuo de capítulos y farmeo de gemas.
- Selección de Baraja Prestada / Propia y arranque de duelos.
- Salto de cinemáticas y recolección de recompensas de fin de duelo.
"""

import time
import logging
import numpy as np
from typing import Optional, Dict, Any
from master_duel.vision.state_detector import MasterDuelState
from master_duel.input.input_controller import InputController
from master_duel.brain.gemini_brain import MasterDuelBrain

log = logging.getLogger("MD_SoloNavigator")


class SoloNavigator:
    """Automatizador del flujo PvE / Modo Solo de Master Duel."""

    def __init__(self, input_ctrl: InputController, brain: MasterDuelBrain):
        self.input = input_ctrl
        self.brain = brain
        self._last_progress_time = time.time()

    def handle_navigation(self, frame: np.ndarray, state: MasterDuelState, meta: Dict[str, Any]) -> bool:
        """Determina y ejecuta el siguiente paso de navegación fuera de duelo."""
        
        # 1. Pantalla de Título (Press Any Button)
        if state == MasterDuelState.TITLE_SCREEN:
            log.info("🎮 Pantalla de título: Entrando al juego...")
            self.input.click(0.50, 0.50, normalized=True, delay=1.5)
            self._last_progress_time = time.time()
            return True

        # 2. Menú Principal -> Modo Solo
        if state == MasterDuelState.MAIN_MENU:
            log.info("🏠 Menú Principal: Navegando hacia Modo Solo...")
            return self._navigate_to_solo(frame)

        # 3. Pantalla de Resultados de Duelo (Victoria/Derrota y Recompensas)
        if state == MasterDuelState.DUEL_RESULT:
            log.info("🏆 Pantalla de Resultados: Recogiendo recompensas y gemas...")
            self.input.click(0.50, 0.85, normalized=True, delay=0.8)
            self._last_progress_time = time.time()
            return True

        # 4. Diálogos emergentes o Avisos
        if state == MasterDuelState.MODAL_POPUP:
            log.info("💬 Cerrando ventana emergente / diálogo modal...")
            self.input.click(0.50, 0.65, normalized=True, delay=0.5)
            self._last_progress_time = time.time()
            return True

        # 5. Puertas o Capítulos del Modo Solo
        if state in (MasterDuelState.SOLO_GATE_SELECT, MasterDuelState.SOLO_CHAPTER_DETAIL):
            log.info("🗺️ Modo Solo: Seleccionando capítulo o iniciando duelo...")
            return self._consult_and_navigate(frame, state.value)

        # Para cualquier otra pantalla no clasificada
        return self._consult_and_navigate(frame, state.value)

    def _navigate_to_solo(self, frame: np.ndarray) -> bool:
        decision = self.brain.consult(
            frame,
            current_state="MAIN_MENU",
            extra_context="Locate the 'SOLO' button in the main menu and click it."
        )
        if decision and decision.get("action") == "CLICK":
            x = float(decision.get("x", 0.35))
            y = float(decision.get("y", 0.55))
            self.input.click(x, y, normalized=True, delay=1.0)
            self._last_progress_time = time.time()
            return True
        else:
            # Fallback en posición típica del botón SOLO en Master Duel
            self.input.click(0.35, 0.55, normalized=True, delay=1.0)
            return True

    def _consult_and_navigate(self, frame: np.ndarray, state_name: str) -> bool:
        decision = self.brain.consult(
            frame,
            current_state=state_name,
            extra_context="In Solo Mode. Select the next uncompleted chapter, select loaner deck, skip cutscene, or start duel."
        )

        if not decision:
            # Si no hay respuesta, un click seguro en el centro para avanzar diálogos
            self.input.safe_dismiss_click()
            return False

        action = decision.get("action", "").upper()
        summary = decision.get("summary", "")
        log.info(f"🧭 Navegación: {action} - {summary}")

        if action == "CLICK":
            x = float(decision.get("x", 0.5))
            y = float(decision.get("y", 0.5))
            x = max(0.05, min(0.95, x))
            y = max(0.05, min(0.95, y))
            self.input.click(x, y, normalized=True, delay=0.5)
            self._last_progress_time = time.time()
            return True

        elif action == "WAIT":
            time.sleep(1.0)
            return True

        return False

    def check_stuck_recovery(self):
        """Si la navegación lleva más de 30 segundos sin cambios, intenta un clic de recuperación."""
        if time.time() - self._last_progress_time > 30.0:
            log.warning("⚠️ Sin cambios durante 30s. Ejecutando clic de rescate seguro...")
            self.input.safe_dismiss_click()
            time.sleep(0.5)
            self.input.right_click(0.5, 0.5, normalized=True)
            self._last_progress_time = time.time()
