"""
Duel Engine Module for Yu-Gi-Oh! Master Duel
Manejo híbrido ultrarrápido:
- Acciones mecánicas rutinarias en local (OpenCV en < 5ms):
  * Detección instantánea de botones 'Summon' / 'Set' / 'Activate' y 'Confirm' sobre cartas en mano y campo.
  * Detección instantánea de selección de posición en tablero ('Select position for...').
  * Descarte de prompts y selección de Fase inteligente (BATTLE PHASE vs END PHASE).
  * Rutina de ataque automático en Battle Phase (declaración de ataque y daño directo).
  * Registro paso a paso de cada jugada en ReplayRecorder para aprendizaje continuo.
- Cerebro Gemini para decisiones macro-tácticas enriquecidas con heurísticas aprendidas.
"""

import time
import cv2
import logging
import numpy as np
from typing import Optional, Tuple, Dict, Any, List
from master_duel.vision.state_detector import MasterDuelState
from master_duel.input.input_controller import InputController
from master_duel.brain.gemini_brain import MasterDuelBrain
from master_duel.vision.board_detector import BoardDetector
from master_duel.database.card_database import CardDatabase
from master_duel.vision.card_recognizer import CardRecognizer
from master_duel.decision.utility_evaluator import UtilityEvaluator, ActionCandidate

log = logging.getLogger("MD_DuelEngine")


class MasterDuelEngine:
    """Motor táctico híbrido de alta precisión (OpenCV local ultrarrápido + Base de Conocimiento + Utility AI)."""

    def __init__(
        self,
        input_ctrl: InputController,
        brain: MasterDuelBrain,
        learning_system: Optional[Any] = None,
        replay_recorder: Optional[Any] = None
    ):
        self.input = input_ctrl
        self.brain = brain
        self.learning_system = learning_system
        self.replay_recorder = replay_recorder
        
        # Inteligencia de Tablero y Base de Datos de 14.600+ cartas
        self.board_detector = BoardDetector()
        self.card_database = CardDatabase()
        self.card_recognizer = CardRecognizer(self.card_database)
        self.utility_evaluator = UtilityEvaluator(self.card_database)

        self.last_action_time = 0.0
        self.action_cooldown = 1.0
        self.last_macro_call_time = 0.0
        self.macro_cooldown = 3.0  # Máximo 1 consulta a Gemini cada 3s

        # Estado táctico de fases y combate
        self.turn_number = 1
        self.has_attacked_this_turn = False
        self.has_normal_summoned_this_turn = False
        self.has_set_traps_this_turn = False
        self.hand_probe_index = 0
        self.set_probe_index = 0
        self.glowing_click_history: Dict[Tuple[int, int], int] = {}
        self.current_phase = "MAIN1"
        self.battle_phase_entered_time = 0.0

    def handle_duel_step(self, frame: np.ndarray, state: MasterDuelState, meta: Dict[str, Any]) -> bool:
        now = time.time()
        if now - self.last_action_time < self.action_cooldown:
            return False

        h, w = frame.shape[:2]

        # Actualizar fase visualmente detectada
        detected_phase = meta.get("detected_phase", self.current_phase)
        if detected_phase in ("MAIN1", "BATTLE", "MAIN2", "END"):
            if self.current_phase != detected_phase:
                log.info(f"🔄 Fase detectada por visión: {self.current_phase} -> {detected_phase}")
                self.current_phase = detected_phase
                if detected_phase == "BATTLE":
                    self.has_attacked_this_turn = False

        # ── 1. RUTINAS LOCALES ULTRA-RÁPIDAS (< 5ms, CERO LATENCIA) ───────────

        # A. Si el juego pide colocar el monstruo ("Select position for...")
        if self._is_position_selection(frame, w, h):
            empty_pos = self.board_detector.get_empty_player_monster_zone() or (0.50, 0.62)
            log.info(f"⚡ [INSTANTÁNEO] 'Select position for...' detectado. Invocando monstruo en zona óptima ({empty_pos[0]:.2f}, {empty_pos[1]:.2f})...")
            self.input.click(empty_pos[0], empty_pos[1], normalized=True, delay=0.4)
            self.has_normal_summoned_this_turn = True  # Invocación normal / especial confirmada en tablero
            if self.replay_recorder:
                self.replay_recorder.record_action("POSITION_SELECT", phase="MAIN1", turn=self.turn_number, details={"monsters": [1]})
            self.last_action_time = time.time()
            return True

        # B. Si hay botones circulares 'Summon' / 'Activate' / 'Confirm' abiertos sobre una carta
        summon_pos = self._find_action_circle(frame, w, h)
        if summon_pos:
            log.info(f"⚡ [INSTANTÁNEO] Botón de acción detectado en ({summon_pos[0]:.2f}, {summon_pos[1]:.2f}). Pulsando...")
            self.input.click(summon_pos[0], summon_pos[1], normalized=True, delay=0.4)
            act_type = "CARD_ACTION"
            if self.replay_recorder:
                self.replay_recorder.record_action(
                    act_type,
                    card_name="Card Action",
                    details={"x": summon_pos[0], "y": summon_pos[1], "monsters": [1]},
                    phase=self.current_phase,
                    turn=self.turn_number
                )
            self.last_action_time = time.time()
            return True

        # B.2. Si hay selector de cartas activo (Búsqueda en Mazo / Cementerio / Objetivo)
        if state == MasterDuelState.DUEL_TARGET_SELECT or self._is_card_selection_modal(frame, w, h):
            return self._handle_card_selection_modal(frame)

        # C. Si hay prompt de activación / cadena emergente en el centro
        if state == MasterDuelState.DUEL_CHAIN_PROMPT:
            return self._handle_chain_prompt(frame)

        # D. Si es turno del oponente, esperar pacíficamente y reiniciar banderas de turno
        if state == MasterDuelState.DUEL_OPPONENT_TURN:
            log.info("⏳ Turno del oponente...")
            if self.current_phase != "OPPONENT":
                self.turn_number += 1
                self.has_normal_summoned_this_turn = False
                self.has_attacked_this_turn = False
                self.has_set_traps_this_turn = False
                self.hand_probe_index = 0
                self.set_probe_index = 0
                self.glowing_click_history.clear()
                self.utility_evaluator.reset_turn()
            self.current_phase = "OPPONENT"
            time.sleep(1.0)
            return True

        # E. Si está abierta la ventana de selección de fase ('Select Phase to Change to')
        if self._is_phase_selection_modal(frame, w, h):
            if self.turn_number == 1:
                log.info("🛡️ [TURNO 1] No se puede atacar en Turno 1 -> END PHASE (0.78, 0.72)...")
                self.input.click(0.78, 0.72, normalized=True, delay=0.6)
                self.current_phase = "END"
            elif not self.has_attacked_this_turn:
                log.info("⚔️ [TACTICA] 'Select Phase' detectado -> BATTLE PHASE (0.78, 0.58) para atacar...")
                self.input.click(0.78, 0.58, normalized=True, delay=0.6)
                self.current_phase = "BATTLE"
                self.battle_phase_entered_time = time.time()
            else:
                log.info("🛡️ [TACTICA] Ataque concluido -> END PHASE (0.78, 0.72)...")
                self.input.click(0.78, 0.72, normalized=True, delay=0.6)
                self.current_phase = "END"
            if self.replay_recorder:
                self.replay_recorder.record_action("PHASE_SELECT", phase=self.current_phase, turn=self.turn_number, details={"monsters": [1]})
            self.last_action_time = time.time()
            return True

        # F. Rutina de Combate Activo si estamos en Battle Phase
        if self.current_phase == "BATTLE" and not self.has_attacked_this_turn:
            if self._execute_battle_attack(frame, w, h):
                return True

        # ── 2. DECISIÓN MACRO CON GEMINI (Solo cuando se requiere pensar) ──────
        if state == MasterDuelState.DUEL_PLAYER_TURN:
            return self._handle_player_turn(frame, meta)

        return False

    def _is_phase_selection_modal(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta si está abierta la ventana emergente 'Select Phase to Change to'."""
        tl_roi = frame[int(h * 0.05):int(h * 0.12), int(w * 0.015):int(w * 0.055)]
        if tl_roi.size > 0:
            hsv_tl = cv2.cvtColor(tl_roi, cv2.COLOR_BGR2HSV)
            yellow_ring = cv2.inRange(hsv_tl, np.array([20, 100, 100]), np.array([45, 255, 255]))
            if np.count_nonzero(yellow_ring) > 40:
                return False

        banner_roi = frame[int(h * 0.52):int(h * 0.56), int(w * 0.35):int(w * 0.65)]
        if banner_roi.size == 0:
            return False
        gray = cv2.cvtColor(banner_roi, cv2.COLOR_BGR2GRAY)
        dark_ratio = np.count_nonzero(gray < 50) / gray.size
        white_ratio = np.count_nonzero(gray > 200) / gray.size
        return dark_ratio > 0.60 and white_ratio > 0.03

    def _is_card_selection_modal(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta si está abierto un selector de cartas (Deck Search, Cementerio, Extra Deck o Campo) con botón Decide."""
        decide_roi = frame[int(h * 0.72):int(h * 0.82), int(w * 0.42):int(w * 0.58)]
        if decide_roi.size == 0:
            return False
        hsv = cv2.cvtColor(decide_roi, cv2.COLOR_BGR2HSV)
        blue_btn = cv2.inRange(hsv, np.array([95, 90, 90]), np.array([130, 255, 255]))
        gray = cv2.cvtColor(decide_roi, cv2.COLOR_BGR2GRAY)
        white_txt = np.count_nonzero(gray > 220)
        return np.count_nonzero(blue_btn) > 180 and white_txt > 50

    def _handle_card_selection_modal(self, frame: np.ndarray) -> bool:
        """
        Resuelve selecciones de cartas de la Baraja (Deck Search), Cementerio o Campo:
        1. Clic en la primera carta de la cuadrícula de búsqueda (0.40, 0.45).
        2. Clic en el botón Decide / Confirmar (0.50, 0.76).
        """
        log.info("🎯 [SELECTOR DE CARTAS] Menú de búsqueda en Mazo/Cementerio activo -> Seleccionando carta y confirmando...")
        self.input.click(0.40, 0.45, normalized=True, delay=0.35)
        time.sleep(0.3)
        self.input.click(0.50, 0.76, normalized=True, delay=0.4)
        if self.replay_recorder:
            self.replay_recorder.record_action("CARD_SELECT_CONFIRM", phase=self.current_phase, turn=self.turn_number, details={"monsters": [1]})
        self.last_action_time = time.time()
        return True

    def _is_position_selection(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta si está visible la barra azul 'Select position for...'."""
        roi_banner = frame[int(h * 0.22):int(h * 0.30), int(w * 0.25):int(w * 0.75)]
        if roi_banner.size == 0:
            return False
        gray = cv2.cvtColor(roi_banner, cv2.COLOR_BGR2GRAY)
        dark_ratio = np.count_nonzero(gray < 60) / gray.size
        white_count = np.count_nonzero(gray > 200)
        return dark_ratio > 0.50 and (white_count / gray.size) > 0.007

    def _execute_battle_attack(self, frame: np.ndarray, w: int, h: int) -> bool:
        """
        Ejecuta la declaración de ataque en Battle Phase asistido por BoardDetector y UtilityEvaluator:
        1. Evalúa el estado del campo mediante Utility AI.
        2. Si no hay monstruos rivales -> Lanza ofensiva de Ataque Directo a los LP.
        3. Si hay monstruos rivales -> Ataca sus monstruos para limpiar el campo.
        4. Pasa a End Phase al terminar todos los ataques.
        """
        board = self.board_detector.scan_board(frame)
        opp_monsters = [z for name, z in board.items() if name.startswith("OPP_M") and z.is_occupied]
        
        # Coordenadas de las zonas de monstruos aliadas (Zonas 1-5 y Extra Monster Zones)
        ally_zones = [
            (0.50, 0.62),  # Centro Zona 3
            (0.42, 0.62),  # Zona 2
            (0.58, 0.62),  # Zona 4
            (0.34, 0.62),  # Zona 1
            (0.68, 0.62),  # Zona 5
            (0.41, 0.46),  # EMZ Izquierda
            (0.59, 0.46),  # EMZ Derecha
        ]

        battle_candidates = self.utility_evaluator.evaluate_battle_actions(
            ally_monsters=ally_zones,
            opp_monsters_count=len(opp_monsters),
            turn_number=self.turn_number
        )

        is_direct = (len(opp_monsters) == 0)
        best_battle = self.utility_evaluator.select_best_action(battle_candidates)
        if best_battle:
            log.info(f"⚔️ [BATTLE PHASE] {best_battle.description} (Score: {best_battle.score:.1f})")

        attacks_declared = 0
        for ax, ay in ally_zones:
            # 1. Clic en nuestro monstruo
            self.input.click(ax, ay, normalized=True, delay=0.35)
            time.sleep(0.2)

            # 2. Clic en objetivo según estado del campo rival
            if is_direct:
                # Daño directo al centro y a los LP
                self.input.click(0.50, 0.36, normalized=True, delay=0.3)
                self.input.click(0.50, 0.22, normalized=True, delay=0.3)
            else:
                target_x = opp_monsters[0].center_x if opp_monsters else 0.50
                target_y = opp_monsters[0].center_y if opp_monsters else 0.36
                self.input.click(target_x, target_y, normalized=True, delay=0.35)

            # 3. Confirmar objetivo si aparece confirmación
            self.input.click(0.50, 0.55, normalized=True, delay=0.25)
            attacks_declared += 1
            time.sleep(0.8)  # Pausa calibrada para permitir la animación de batalla y cálculo de daño

        self.has_attacked_this_turn = True
        self.last_action_time = time.time()

        if self.replay_recorder:
            self.replay_recorder.record_action(
                "ATTACK",
                card_name="Ally Monsters",
                phase="BATTLE",
                turn=self.turn_number,
                details={"attacks_count": attacks_declared, "is_direct": is_direct, "monsters": [1]}
            )

        time.sleep(0.8)
        log.info("⏭️ [BATTLE PHASE] Ataques ejecutados. Pasando turno de forma segura...")
        self._safe_phase_advance()
        return True

    def _find_action_circle(self, frame: np.ndarray, w: int, h: int) -> Optional[Tuple[float, float]]:
        """
        Encuentra círculos cian/azules de acción ('Summon', 'Set', 'Activate', 'Confirm').
        Prioriza cartas en mano para invocación e ignora auto-sacrificios no deseados en campo.
        """
        roi = frame[int(h * 0.38):int(h * 0.85), int(w * 0.15):int(w * 0.85)]
        if roi.size == 0:
            return None

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([80, 100, 100]), np.array([135, 255, 255]))

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in cnts:
            area = cv2.contourArea(c)
            if 350 < area < 5000:
                peri = cv2.arcLength(c, True)
                if peri > 0:
                    circ = 4 * np.pi * area / (peri * peri)
                    if circ > 0.65:
                        M = cv2.moments(c)
                        if M['m00'] > 0:
                            cx = int(M['m10'] / M['m00']) + int(w * 0.15)
                            cy = int(M['m01'] / M['m00']) + int(h * 0.38)
                            norm_x = cx / float(w)
                            norm_y = cy / float(h)
                            candidates.append((norm_x, norm_y, area))

        if candidates:
            # Priorizar cartas en la mano (y > 0.70) para invocar monstruos y jugar magias limpiamente
            hand_candidates = [c for c in candidates if c[1] > 0.70]
            if hand_candidates:
                hand_candidates.sort(key=lambda item: item[0])
                return hand_candidates[0][0], hand_candidates[0][1]

            # Botones de confirmación sobre el campo
            candidates.sort(key=lambda item: item[0])
            return candidates[0][0], candidates[0][1]

        return None

    def _find_glowing_hand_cards(self, frame: np.ndarray, w: int, h: int) -> List[Tuple[float, float]]:
        """Detecta visualmente cartas jugables que brillan con aura dorada/cian en la mano."""
        hand_roi = frame[int(h * 0.82):int(h * 0.97), int(w * 0.30):int(w * 0.72)]
        if hand_roi.size == 0:
            return []

        hsv = cv2.cvtColor(hand_roi, cv2.COLOR_BGR2HSV)
        gold_glow = cv2.inRange(hsv, np.array([18, 120, 140]), np.array([35, 255, 255]))
        cyan_glow = cv2.inRange(hsv, np.array([85, 120, 140]), np.array([105, 255, 255]))
        glow_mask = gold_glow + cyan_glow

        cnts, _ = cv2.findContours(glow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        glowing_cards = []
        for c in cnts:
            if cv2.contourArea(c) > 200:
                M = cv2.moments(c)
                if M['m00'] > 0:
                    cx = int(M['m10'] / M['m00']) + int(w * 0.30)
                    cy = int(M['m01'] / M['m00']) + int(h * 0.82)
                    glowing_cards.append((cx / float(w), cy / float(h)))

        glowing_cards.sort(key=lambda item: item[0])
        return glowing_cards

    def _handle_player_turn(self, frame: np.ndarray, meta: Dict[str, Any]) -> bool:
        """
        Maneja el turno del jugador utilizando el motor de evaluación por puntuación táctica (Utility AI):
        1. Genera todas las acciones candidatas viables (brillantes, invocaciones, extra deck, set).
        2. Evalúa el score matemático de cada una según fase, turno e impacto en mesa.
        3. Despacha la acción de mayor EV. Si no quedan acciones de valor, avanza de fase.
        """
        h, w = frame.shape[:2]

        # 1. Comprobar si el Extra Deck está habilitado para un Boss Monster
        if self._check_and_summon_extra_deck(frame, w, h):
            return True

        # 2. Obtener candidatos de mano
        glowing = self._find_glowing_hand_cards(frame, w, h)
        hand_slots = [
            (0.44, 0.88),  # Slot 2 (central)
            (0.50, 0.88),  # Slot 3
            (0.38, 0.88),  # Slot 1
            (0.56, 0.88),  # Slot 4
            (0.62, 0.88),  # Slot 5
            (0.32, 0.88),  # Slot 0
        ]

        candidates = self.utility_evaluator.evaluate_hand_actions(
            glowing_cards=glowing,
            hand_slots=hand_slots,
            has_normal_summoned=self.has_normal_summoned_this_turn,
            current_phase=self.current_phase,
            turn_number=self.turn_number
        )

        # 3. Evaluar avance de fase como opción concurrente
        phase_candidate = self.utility_evaluator.evaluate_phase_advance(
            current_phase=self.current_phase,
            turn_number=self.turn_number,
            has_attacked=self.has_attacked_this_turn,
            has_normal_summoned=self.has_normal_summoned_this_turn,
            remaining_hand_actions=len(glowing)
        )
        candidates.append(phase_candidate)

        # 4. Seleccionar la acción con mayor puntuación
        best_action = self.utility_evaluator.select_best_action(candidates)
        if not best_action:
            self._safe_phase_advance()
            return True

        # 5. Ejecutar la acción seleccionada
        if best_action.action_type == "PHASE_CHANGE":
            log.info(f"⏭️ [DECISIÓN AI] {best_action.description}")
            self._safe_phase_advance()
            return True

        log.info(f"⚡ [DECISIÓN AI] Ejecutando: {best_action.description}")
        tx, ty = best_action.target_coords
        self.input.click(tx, ty, normalized=True, delay=0.4)
        self.last_action_time = time.time()
        return True

    def _check_and_summon_extra_deck(self, frame: np.ndarray, w: int, h: int) -> bool:
        """
        Detecta si el Extra Deck (esquina inferior izquierda) está brillando
        para invocar un Monstruo Jefe (Link, Synchro, Xyz, Fusion).
        """
        ed_roi = frame[int(h * 0.70):int(h * 0.82), int(w * 0.12):int(w * 0.20)]
        if ed_roi.size == 0:
            return False

        hsv = cv2.cvtColor(ed_roi, cv2.COLOR_BGR2HSV)
        glow_ed = cv2.inRange(hsv, np.array([85, 100, 120]), np.array([135, 255, 255])) + \
                  cv2.inRange(hsv, np.array([18, 120, 120]), np.array([35, 255, 255]))

        if np.count_nonzero(glow_ed) > 180:
            log.info("🌟 [EXTRA DECK] ¡Extra Deck brillando! Abriendo para invocar Monstruo Jefe...")
            self.input.click(0.16, 0.75, normalized=True, delay=0.5)
            time.sleep(0.4)
            # Clic en el primer monstruo disponible en el menú del Extra Deck (0.40, 0.50)
            self.input.click(0.40, 0.50, normalized=True, delay=0.4)
            self.last_action_time = time.time()
            return True
        return False

    def _handle_chain_prompt(self, frame: np.ndarray) -> bool:
        """
        Cancela o rechaza prompts de activación/cadena no deseados con Clic Derecho
        para prevenir auto-destrucción y tributos perjudiciales.
        """
        log.info("🛡️ [PROMPT] Cuadro de activación detectado -> Clic Derecho para cancelar/rechazar limpiamente...")
        self.input.right_click(0.50, 0.50, normalized=True, delay=0.3)
        if self.replay_recorder:
            self.replay_recorder.record_action("CHAIN_DISMISS", phase=self.current_phase, turn=self.turn_number, details={"monsters": [1]})
        self.last_action_time = time.time()
        return True

    def _execute_decision(self, decision: Dict[str, Any]) -> bool:
        action = decision.get("action", "").upper()
        summary = decision.get("summary", "")
        log.info(f"💡 Táctica: {summary}")

        if action == "CLICK":
            x = float(decision.get("x", 0.5))
            y = float(decision.get("y", 0.5))
            if x > 1.0: x /= 1920.0
            if y > 1.0: y /= 1080.0
            x = max(0.06, min(0.94, x))
            y = max(0.06, min(0.94, y))
            self.input.click(x, y, normalized=True, delay=0.3)
            self.last_action_time = time.time()
            return True

        elif action == "DRAG":
            fx = float(decision.get("from_x", 0.5))
            fy = float(decision.get("from_y", 0.85))
            tx = float(decision.get("to_x", 0.5))
            ty = float(decision.get("to_y", 0.60))
            if fx > 1.0: fx /= 1920.0
            if fy > 1.0: fy /= 1080.0
            if tx > 1.0: tx /= 1920.0
            if ty > 1.0: ty /= 1080.0
            self.input.drag(fx, fy, tx, ty, normalized=True)
            self.last_action_time = time.time()
            return True

        return False

    def _safe_phase_advance(self):
        """Pasa de fase de forma segura abriendo el menú de fase y seleccionando la fase adecuada."""
        log.info("⏭️ Avanzando fase (Battle / End Phase)...")
        # 1. Clic en la moneda de fase (0.77, 0.46) para abrir selector
        self.input.click(0.77, 0.46, normalized=True, delay=0.35)
        time.sleep(0.35)

        # 2. Seleccionar la fase correspondiente:
        if self.turn_number == 1:
            log.info("🛡️ [TURNO 1] Regla Yu-Gi-Oh!: No hay Battle Phase en Turno 1 -> END PHASE (0.78, 0.72)...")
            self.input.click(0.78, 0.72, normalized=True, delay=0.5)
            self.current_phase = "END"
        elif not self.has_attacked_this_turn and self.current_phase == "MAIN1":
            log.info("⚔️ [TURNO 2+] Seleccionando BATTLE PHASE (0.78, 0.58)...")
            self.input.click(0.78, 0.58, normalized=True, delay=0.5)
            self.current_phase = "BATTLE"
            self.battle_phase_entered_time = time.time()
        else:
            log.info("🛡️ Ataque concluido -> Seleccionando END PHASE (0.78, 0.72)...")
            self.input.click(0.78, 0.72, normalized=True, delay=0.5)
            self.current_phase = "END"

        if self.replay_recorder:
            self.replay_recorder.record_action(
                "PHASE_CHANGE",
                details={"to_phase": self.current_phase, "monsters": [1]},
                phase=self.current_phase,
                turn=self.turn_number
            )
        self.last_action_time = time.time()
