"""
Utility Evaluator & Action Scoring Engine for Yu-Gi-Oh! Master Duel AI.
Reemplaza la lógica rígida de if/else por un sistema de evaluación heurística por puntuación (Utility AI):
1. Genera las acciones candidatas disponibles en el estado actual.
2. Asigna un valor de utilidad (Score) basado en el impacto táctico, fase y roles de carta.
3. Selecciona y despacha la acción con mayor EV (Expected Value).
"""

import time
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

log = logging.getLogger("MD_UtilityAI")


@dataclass
class ActionCandidate:
    action_type: str        # "CLICK_CARD", "NORMAL_SUMMON", "ACTIVATE_SPELL", "SET_TRAP", "EXTRA_DECK", "ATTACK", "PHASE_CHANGE", "DECIDE"
    target_coords: Tuple[float, float]
    score: float
    description: str
    card_name: Optional[str] = None
    priority: int = 1


class UtilityEvaluator:
    """Motor de evaluación de acciones por puntuación táctica."""

    def __init__(self, card_database=None):
        self.db = card_database
        self.action_history: Dict[Tuple[int, int], int] = {}

    def reset_turn(self):
        """Reinicia el historial de acciones al inicio de un nuevo turno."""
        self.action_history.clear()

    def evaluate_hand_actions(
        self,
        glowing_cards: List[Tuple[float, float]],
        hand_slots: List[Tuple[float, float]],
        has_normal_summoned: bool,
        current_phase: str,
        turn_number: int
    ) -> List[ActionCandidate]:
        """Evalúa y puntúa las acciones viables desde la mano."""
        candidates: List[ActionCandidate] = []

        # 1. Cartas brillantes (Magias, Efectos rápidos, Invocaciones legales activas)
        for gx, gy in glowing_cards:
            coord_key = (int(gx * 100), int(gy * 100))
            repeat_count = self.action_history.get(coord_key, 0)
            
            # Puntuación base alta por ser legal según el cliente
            base_score = 150.0 - (repeat_count * 50.0)
            
            candidates.append(ActionCandidate(
                action_type="ACTIVATE_GLOWING",
                target_coords=(gx, gy),
                score=base_score,
                description=f"Activar carta brillante en ({gx:.2f}, {gy:.2f}) [Repeticiones: {repeat_count}]",
                priority=10
            ))

        # 2. Invocación Normal (si no se ha usado en el turno)
        if not has_normal_summoned and current_phase == "MAIN1":
            for idx, (hx, hy) in enumerate(hand_slots):
                # Priorizar cartas centrales (monstruos típicos en mano inicial)
                slot_bonus = 30.0 if idx in (0, 1, 2) else 10.0
                candidates.append(ActionCandidate(
                    action_type="PROBE_SUMMON",
                    target_coords=(hx, hy),
                    score=110.0 + slot_bonus,
                    description=f"Sondear slot de mano {idx + 1} para Invocación Normal en ({hx:.2f}, {hy:.2f})",
                    priority=8
                ))

        # 3. Colocación defensiva de Trampas / Magias de juego rápido (SET)
        if has_normal_summoned and current_phase in ("MAIN1", "MAIN2"):
            for idx, (sx, sy) in enumerate(hand_slots[2:]):
                candidates.append(ActionCandidate(
                    action_type="PROBE_SET",
                    target_coords=(sx, sy),
                    score=85.0 - (idx * 5.0),
                    description=f"Sondear carta en ({sx:.2f}, {sy:.2f}) para colocación defensiva (SET)",
                    priority=5
                ))

        return candidates

    def evaluate_battle_actions(
        self,
        ally_monsters: List[Tuple[float, float]],
        opp_monsters_count: int,
        turn_number: int
    ) -> List[ActionCandidate]:
        """Evalúa las acciones disponibles en Battle Phase."""
        candidates: List[ActionCandidate] = []

        if turn_number <= 1:
            # En Turno 1 oficial está prohibido el combate
            return candidates

        if opp_monsters_count == 0:
            # Campo libre: Ataque Directo prioritario
            candidates.append(ActionCandidate(
                action_type="DIRECT_ATTACK_SEQUENCE",
                target_coords=(0.50, 0.22),
                score=300.0,
                description="Ejecutar ofensiva total de Ataque Directo a los LP rivales",
                priority=20
            ))
        else:
            # Limpieza de campo rival
            candidates.append(ActionCandidate(
                action_type="FIELD_CLEAR_ATTACK",
                target_coords=(0.50, 0.36),
                score=220.0,
                description=f"Declarar ataques a los {opp_monsters_count} monstruos del oponente",
                priority=18
            ))

        return candidates

    def evaluate_phase_advance(
        self,
        current_phase: str,
        turn_number: int,
        has_attacked: bool,
        has_normal_summoned: bool,
        remaining_hand_actions: int
    ) -> ActionCandidate:
        """Puntúa el momento óptimo para el cambio de fase."""
        if current_phase == "MAIN1":
            if turn_number == 1:
                target_phase = "END"
                target_coords = (0.78, 0.72)
                score = 100.0 if (has_normal_summoned and remaining_hand_actions == 0) else 40.0
            else:
                target_phase = "BATTLE"
                target_coords = (0.78, 0.58)
                score = 130.0 if (has_normal_summoned and remaining_hand_actions == 0) else 50.0

            return ActionCandidate(
                action_type="PHASE_CHANGE",
                target_coords=target_coords,
                score=score,
                description=f"Avanzar de {current_phase} a {target_phase}",
                priority=4
            )

        elif current_phase == "BATTLE":
            return ActionCandidate(
                action_type="PHASE_CHANGE",
                target_coords=(0.78, 0.72),
                score=250.0 if has_attacked else 20.0,
                description="Concluir Battle Phase y pasar a End Phase",
                priority=15
            )

        return ActionCandidate(
            action_type="PHASE_CHANGE",
            target_coords=(0.78, 0.72),
            score=90.0,
            description="Pasar a End Phase",
            priority=2
        )

    def select_best_action(self, candidates: List[ActionCandidate]) -> Optional[ActionCandidate]:
        """Selecciona la acción con mayor puntuación matemática de utilidad."""
        if not candidates:
            return None

        # Ordenar por puntuación descendente
        candidates.sort(key=lambda c: c.score, reverse=True)
        best = candidates[0]

        # Registrar la acción en el historial para evitar bucles
        coord_key = (int(best.target_coords[0] * 100), int(best.target_coords[1] * 100))
        self.action_history[coord_key] = self.action_history.get(coord_key, 0) + 1

        log.info(f"🏆 Mejor jugada evaluada: {best.description} (Score: {best.score:.1f})")
        return best
