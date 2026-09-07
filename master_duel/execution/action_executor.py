"""
Action Executor for Yu-Gi-Oh! Master Duel AI.
Translates high-level tactical DuelActions into accurate, humanized Win32 mouse/keyboard actions.
Follows the OBSERVE -> ACT -> VERIFY contract.
"""
import time
import cv2
import numpy as np
from typing import Optional, Dict, Any, Tuple
from ..planning.legal_actions import DuelAction, ActionType
from ..input.input_controller import InputController
from ..vision.board_detector import BoardDetector, ZoneCoords
from ..vision.ui_recognizer import UIRecognizer
from ..vision.screen_capture import ScreenCapture

class ActionExecutor:
    def __init__(
        self,
        input_ctrl: InputController,
        board_detector: BoardDetector,
        ui_recognizer: UIRecognizer,
        screen_cap: ScreenCapture
    ):
        self.input_ctrl = input_ctrl
        self.board_detector = board_detector
        self.ui_recognizer = ui_recognizer
        self.screen_cap = screen_cap

    def execute_action(self, action: DuelAction) -> bool:
        """
        Executes a planned DuelAction using visual UI detection.
        Returns: True if physical interaction succeeded, False otherwise.
        """
        self.input_ctrl.bring_to_front()
        time.sleep(0.08)

        if action.action_type == ActionType.NORMAL_SUMMON:
            return self._execute_normal_summon(action)
        elif action.action_type == ActionType.SET_SPELL_TRAP:
            return self._execute_set_card(action)
        elif action.action_type in [ActionType.ACTIVATE_SPELL, ActionType.ACTIVATE_EFFECT]:
            return self._execute_activate(action)
        elif action.action_type == ActionType.ATTACK_MONSTER:
            return self._execute_attack_monster(action)
        elif action.action_type == ActionType.ATTACK_DIRECT:
            return self._execute_attack_direct(action)
        elif action.action_type == ActionType.ENTER_BATTLE:
            return self._execute_change_phase("battle")
        elif action.action_type == ActionType.ENTER_MAIN2:
            return self._execute_change_phase("main2")
        elif action.action_type == ActionType.END_TURN:
            return self._execute_change_phase("end")
        elif action.action_type == ActionType.CONFIRM_PROMPT:
            return self._execute_confirm_prompt()
        elif action.action_type == ActionType.PASS_PROMPT:
            return self._execute_pass_prompt()

        return False

    def _execute_normal_summon(self, action: DuelAction) -> bool:
        # 1. Click hand area or card
        hand_zone = self.board_detector.get_zone_rect("HAND")
        if hand_zone:
            # Click near center of hand
            self.input_ctrl.click_relative(hand_zone.center_x, hand_zone.center_y)
            time.sleep(0.35)

        # 2. Look for "Summon" action circle
        frame = self.screen_cap.capture()
        if frame is not None:
            action_buttons = self.ui_recognizer.find_action_circles(frame)
            if "summon" in action_buttons:
                btn = action_buttons["summon"]
                self.input_ctrl.click_screen(btn.x, btn.y)
                time.sleep(0.35)
            elif "normal_summon" in action_buttons:
                btn = action_buttons["normal_summon"]
                self.input_ctrl.click_screen(btn.x, btn.y)
                time.sleep(0.35)

        # 3. Check if game requires manual zone selection
        frame_after = self.screen_cap.capture()
        if frame_after is not None and self.ui_recognizer.is_zone_selection_prompt(frame_after):
            target_zone = action.target_zone or "M3"
            z_rect = self.board_detector.get_zone_rect(target_zone)
            if z_rect:
                self.input_ctrl.click_relative(z_rect.center_x, z_rect.center_y)
                time.sleep(0.3)

        return True

    def _execute_set_card(self, action: DuelAction) -> bool:
        hand_zone = self.board_detector.get_zone_rect("HAND")
        if hand_zone:
            self.input_ctrl.click_relative(hand_zone.center_x, hand_zone.center_y)
            time.sleep(0.35)

        frame = self.screen_cap.capture()
        if frame is not None:
            action_buttons = self.ui_recognizer.find_action_circles(frame)
            if "set" in action_buttons:
                btn = action_buttons["set"]
                self.input_ctrl.click_screen(btn.x, btn.y)
                time.sleep(0.35)

        # Check zone selection
        frame_after = self.screen_cap.capture()
        if frame_after is not None and self.ui_recognizer.is_zone_selection_prompt(frame_after):
            target_zone = action.target_zone or "ST3"
            z_rect = self.board_detector.get_zone_rect(target_zone)
            if z_rect:
                self.input_ctrl.click_relative(z_rect.center_x, z_rect.center_y)
                time.sleep(0.3)

        return True

    def _execute_activate(self, action: DuelAction) -> bool:
        # If source is hand
        if action.source_zone == "HAND" or not action.source_zone:
            hand_zone = self.board_detector.get_zone_rect("HAND")
            if hand_zone:
                self.input_ctrl.click_relative(hand_zone.center_x, hand_zone.center_y)
                time.sleep(0.35)
        else:
            # Click card on field
            z_rect = self.board_detector.get_zone_rect(action.source_zone)
            if z_rect:
                self.input_ctrl.click_relative(z_rect.center_x, z_rect.center_y)
                time.sleep(0.35)

        frame = self.screen_cap.capture()
        if frame is not None:
            action_buttons = self.ui_recognizer.find_action_circles(frame)
            if "activate" in action_buttons:
                btn = action_buttons["activate"]
                self.input_ctrl.click_screen(btn.x, btn.y)
                time.sleep(0.4)

        return True

    def _execute_attack_monster(self, action: DuelAction) -> bool:
        attacker_rect = self.board_detector.get_zone_rect(action.source_zone)
        defender_zone = action.target_zone or "OPP_M3"
        defender_rect = self.board_detector.get_zone_rect(defender_zone)

        # 1. Si el botón circular de Ataque (espada cian) ya está visible, pulsarlo directamente
        frame = self.screen_cap.capture()
        if frame is not None:
            atk_btn = self._find_action_button_on_board(frame)
            if atk_btn:
                self.input_ctrl.click_relative(atk_btn[0], atk_btn[1], delay=0.3)

        # 2. Pulsar monstruo atacante
        if attacker_rect:
            self.input_ctrl.click_relative(attacker_rect.center_x, attacker_rect.center_y, delay=0.3)
            # Pulsar inmediatamente el botón Attack que aparece sobre él
            self.input_ctrl.click_relative(attacker_rect.center_x, max(0.20, attacker_rect.center_y - 0.12), delay=0.3)

        # 3. Pulsar o arrastrar al objetivo defensor
        if defender_rect:
            self.input_ctrl.click_relative(defender_rect.center_x, defender_rect.center_y, delay=0.4)
            if attacker_rect:
                # Gesto de arrastre natural hacia el rival
                self.input_ctrl.drag(attacker_rect.center_x, attacker_rect.center_y, defender_rect.center_x, defender_rect.center_y)
            time.sleep(0.4)

        return True

    def _execute_attack_direct(self, action: DuelAction) -> bool:
        attacker_rect = self.board_detector.get_zone_rect(action.source_zone)

        # 1. Si el botón circular de Ataque ya está visible, pulsarlo
        frame = self.screen_cap.capture()
        if frame is not None:
            atk_btn = self._find_action_button_on_board(frame)
            if atk_btn:
                self.input_ctrl.click_relative(atk_btn[0], atk_btn[1], delay=0.3)

        # 2. Pulsar atacante
        if attacker_rect:
            self.input_ctrl.click_relative(attacker_rect.center_x, attacker_rect.center_y, delay=0.3)
            self.input_ctrl.click_relative(attacker_rect.center_x, max(0.20, attacker_rect.center_y - 0.12), delay=0.3)

        # 3. Pulsar LP rival (centro superior 0.50, 0.22)
        self.input_ctrl.click_relative(0.50, 0.22, delay=0.4)
        if attacker_rect:
            self.input_ctrl.drag(attacker_rect.center_x, attacker_rect.center_y, 0.50, 0.22)
        time.sleep(0.4)
        return True

    def _find_action_button_on_board(self, frame: np.ndarray) -> Optional[Tuple[float, float]]:
        """Busca botones circulares activos (espada de Ataque o Confirmación) en el centro del tablero."""
        if frame is None or frame.size == 0:
            return None
        h, w = frame.shape[:2]
        mid = frame[int(h * 0.25):int(h * 0.65), int(w * 0.25):int(w * 0.75)]
        hsv = cv2.cvtColor(mid, cv2.COLOR_BGR2HSV)
        # Espada de ataque o icono cian
        cyan = cv2.inRange(hsv, np.array([90, 100, 100]), np.array([115, 255, 255]))
        cnts, _ = cv2.findContours(cyan, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if 180 < cv2.contourArea(c) < 5000:
                bx, by, bw, bh = cv2.boundingRect(c)
                if 0.7 < bw / float(bh) < 1.4:
                    return ((int(w * 0.25) + bx + bw / 2) / w, (int(h * 0.25) + by + bh / 2) / h)
        return None

    def _execute_change_phase(self, phase_name: str) -> bool:
        # En Master Duel, el botón de fase está en (0.77, 0.46)
        # 1. Clic en el botón circular de fase para desplegar las opciones
        self.input_ctrl.click_relative(0.77, 0.46, delay=0.35)

        # 2. Clic en la fase objetivo dentro del menú desplegado
        menu_targets = {
            "battle": (0.74, 0.40),
            "main2": (0.74, 0.46),
            "end": (0.74, 0.53)
        }
        if phase_name in menu_targets:
            tx, ty = menu_targets[phase_name]
            self.input_ctrl.click_relative(tx, ty, delay=0.4)
            return True

        return True

    def _execute_confirm_prompt(self) -> bool:
        frame = self.screen_cap.capture()
        if frame is not None:
            # 1. Si hay cartas candidatas en el cuadro de selección (y=0.80), clicar la primera para seleccionarla
            # Esto evita bloqueos en prompts de 'Descartar', 'Enviar al Cementerio' o 'Desterrar'
            h, w = frame.shape[:2]
            prompt_header = frame[int(h * 0.60):int(h * 0.70), int(w * 0.30):int(w * 0.70)]
            if prompt_header.size > 0:
                # Clic en primera carta candidata
                self.input_ctrl.click_relative(0.46, 0.80, delay=0.3)
                self.input_ctrl.click_relative(0.37, 0.80, delay=0.2)
                time.sleep(0.2)

            # 2. Clic en botón de confirmar/activar en la parte inferior derecha del cuadro de diálogo
            self.input_ctrl.click_relative(0.58, 0.935, delay=0.3)
            self.input_ctrl.click_relative(0.50, 0.935, delay=0.3)
            # Fallback en caso de prompt centrado
            self.input_ctrl.click_relative(0.58, 0.60, delay=0.2)
            time.sleep(0.3)
            return True

        self.input_ctrl.click_relative(0.58, 0.935, delay=0.3)
        self.input_ctrl.click_relative(0.50, 0.935, delay=0.3)
        return True

    def _execute_pass_prompt(self) -> bool:
        # 1. Botón Cancelar en diálogo inferior
        self.input_ctrl.click_relative(0.42, 0.935, delay=0.3)
        # 2. Botón Cancelar circular en lateral
        self.input_ctrl.click_relative(0.68, 0.46, delay=0.3)
        # 3. Fallback central
        self.input_ctrl.click_relative(0.42, 0.60, delay=0.2)
        time.sleep(0.3)
        return True

    def execute_recovery(self):
        """
        Anti-block recovery: clicks empty board spot or presses ESC to dismiss hanging popups/animations.
        """
        # Click neutral board space (bottom left)
        self.input_ctrl.click_relative(0.15, 0.75)
        time.sleep(0.3)
        # Right click to cancel / dismiss popup
        self.input_ctrl.right_click()
        time.sleep(0.3)
