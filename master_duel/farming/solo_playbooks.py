"""
Solo Playbooks Module for Yu-Gi-Oh! Master Duel AI.
Contiene scripts deterministas paso a paso para superar puertas, escenarios,
tutoriales y duelos del Modo Solo con precisión milimétrica (cero bucles).
Incluye un Vigilante Anti-Bucle (Watchdog) que detecta estancamiento y solicita
asistencia a la IA Gemini Vision.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

log = logging.getLogger("MD_Playbooks")


@dataclass
class PlaybookStep:
    name: str
    action_type: str  # "CLICK", "KEY", "WAIT", "DRAG", "PROMPT"
    target_x: float = 0.50
    target_y: float = 0.50
    key_code: Optional[str] = None
    delay_after: float = 0.5
    description: str = ""


class SoloPlaybookEngine:
    """
    Ejecuta guiones deterministas paso a paso para el Modo Solo.
    Si una pantalla o estado no avanza tras repetidos intentos, activa la alarma de estancamiento.
    """

    def __init__(self, input_ctrl=None):
        self.input_ctrl = input_ctrl
        self.current_playbook: Optional[str] = None
        self.step_index: int = 0
        
        # Vigilante Anti-Bucle
        self._last_state_hash: Optional[int] = None
        self._consecutive_same_state: int = 0
        self.MAX_STALL_TICKS: int = 25  # Tras 25 ticks idénticos sin cambios (~7s) se declara bucle

    def register_state(self, state_str: str, frame_mean: float) -> bool:
        """
        Registra el estado actual. Retorna True si detecta que el bot está atrapado en un bucle.
        """
        current_hash = hash((state_str, round(frame_mean, 1)))
        if self._last_state_hash == current_hash:
            self._consecutive_same_state += 1
        else:
            self._consecutive_same_state = 0
            self._last_state_hash = current_hash

        if self._consecutive_same_state >= self.MAX_STALL_TICKS:
            log.warning(f"🚨 [BUCLE DETECTADO] Estado '{state_str}' repetido {self._consecutive_same_state} veces sin cambios.")
            return True
        return False

    def reset_stall_counter(self):
        self._consecutive_same_state = 0

    def get_standard_loaner_duel_steps(self) -> List[PlaybookStep]:
        """
        Secuencia estándar para iniciar cualquier Duelo con Baraja de Préstamo (Loaner):
        1. Clic en 'Loaner Deck' (Pestaña izquierda) -> (0.35, 0.48)
        2. Clic en botón 'Duel' (Botón azul inferior derecho) -> (0.75, 0.85)
        3. Esperar carga inicial.
        """
        return [
            PlaybookStep(
                name="SELECT_LOANER",
                action_type="CLICK",
                target_x=0.35,
                target_y=0.48,
                delay_after=0.8,
                description="Seleccionar Baraja de Préstamo (Loaner Deck)"
            ),
            PlaybookStep(
                name="CLICK_START_DUEL",
                action_type="CLICK",
                target_x=0.75,
                target_y=0.85,
                delay_after=2.0,
                description="Iniciar Duelo con Baraja de Préstamo"
            )
        ]

    def get_skip_dialog_steps(self) -> List[PlaybookStep]:
        """
        Secuencia para saltar cinemáticas y diálogos del Modo Solo:
        1. Clic en pantalla / Enter para avanzar diálogo.
        2. Clic en botón Menú / Saltar (Esquina superior derecha 0.95, 0.05).
        3. Clic en Confirmar Salto (0.58, 0.60).
        """
        return [
            PlaybookStep(
                name="OPEN_SKIP_MENU",
                action_type="CLICK",
                target_x=0.95,
                target_y=0.05,
                delay_after=0.5,
                description="Abrir menú de salto"
            ),
            PlaybookStep(
                name="CONFIRM_SKIP",
                action_type="CLICK",
                target_x=0.58,
                target_y=0.60,
                delay_after=1.0,
                description="Confirmar salto de diálogo"
            )
        ]
