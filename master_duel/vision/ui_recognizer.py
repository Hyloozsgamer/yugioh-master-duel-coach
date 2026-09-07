"""
UI Recognizer Module for Yu-Gi-Oh! Master Duel.
High-speed local OpenCV detection of buttons, phases, prompts, and dialogs.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any


@dataclass
class UIElement:
    element_type: str  # "BUTTON", "PHASE", "BANNER", "PROMPT", "RESULT"
    name: str          # "SUMMON", "SET", "ACTIVATE", "BATTLE", "END_PHASE", "OK", "CANCEL"
    center_x: float    # Normalizado 0.0 - 1.0
    center_y: float    # Normalizado 0.0 - 1.0
    confidence: float
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    x: int = 0
    y: int = 0


class UIRecognizer:
    """Reconocedor visual local de interfaz y elementos de control."""

    def __init__(self):
        pass

    def detect_all(self, frame: np.ndarray) -> List[UIElement]:
        """Escanea todos los elementos interactivos visibles en el frame."""
        elements: List[UIElement] = []
        if frame is None or frame.size == 0:
            return elements

        h, w = frame.shape[:2]

        # 1. Comprobar banner 'Select position for...'
        banner = self.detect_position_banner(frame, w, h)
        if banner:
            elements.append(banner)

        # 2. Comprobar círculos de acción (Summon / Set / Activate)
        action_circles = self.detect_action_circles(frame, w, h)
        elements.extend(action_circles)

        # 3. Comprobar botón de fase (Main 1 / Battle / Main 2 / End)
        phase_btn = self.detect_phase_button(frame, w, h)
        if phase_btn:
            elements.append(phase_btn)

        # 4. Comprobar modales con botón OK / Next / Close
        modal_btn = self.detect_modal_buttons(frame, w, h)
        if modal_btn:
            elements.append(modal_btn)

        return elements

    def detect_position_banner(self, frame: np.ndarray, w: int, h: int) -> Optional[UIElement]:
        """Detecta si está activa la barra azul de 'Select position for...'."""
        roi = frame[int(h * 0.22):int(h * 0.30), int(w * 0.25):int(w * 0.75)]
        if roi.size == 0:
            return None
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        white_count = np.count_nonzero(gray > 200)
        ratio = white_count / gray.size
        if ratio > 0.007:
            return UIElement(
                element_type="BANNER",
                name="SELECT_POSITION",
                center_x=0.50,
                center_y=0.26,
                confidence=0.95
            )
        return None

    def detect_action_circles(self, frame: np.ndarray, w: int, h: int) -> List[UIElement]:
        """Detecta los botones circulares cian/azules que aparecen sobre una carta seleccionada."""
        elements = []
        roi = frame[int(h * 0.65):int(h * 0.82), int(w * 0.20):int(w * 0.80)]
        if roi.size == 0:
            return elements

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower_cyan = np.array([85, 120, 120])
        upper_cyan = np.array([105, 255, 255])
        mask = cv2.inRange(hsv, lower_cyan, upper_cyan)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in cnts:
            area = cv2.contourArea(c)
            if area > 350:
                M = cv2.moments(c)
                if M['m00'] > 0:
                    cx = int(M['m10'] / M['m00']) + int(w * 0.20)
                    cy = int(M['m01'] / M['m00']) + int(h * 0.65)
                    candidates.append((cx / float(w), cy / float(h), area))

        if candidates:
            candidates.sort(key=lambda item: item[0])
            # Si hay 2 botones: el izquierdo es Summon / Activate, el derecho es Set
            if len(candidates) >= 2:
                elements.append(UIElement("BUTTON", "SUMMON", candidates[0][0], candidates[0][1], 0.92))
                elements.append(UIElement("BUTTON", "SET", candidates[1][0], candidates[1][1], 0.90))
            elif len(candidates) == 1:
                elements.append(UIElement("BUTTON", "ACTIVATE", candidates[0][0], candidates[0][1], 0.90))

        return elements

    def detect_phase_button(self, frame: np.ndarray, w: int, h: int) -> Optional[UIElement]:
        """Detecta la presencia del botón de cambio de fase en el lateral derecho."""
        # Zona 1: Circular media derecha (0.77, 0.46)
        roi_mid = frame[int(h * 0.40):int(h * 0.54), int(w * 0.72):int(w * 0.82)]
        if roi_mid.size > 0:
            hsv_mid = cv2.cvtColor(roi_mid, cv2.COLOR_BGR2HSV)
            # El botón de fase tiene borde dorado y centro azul brillante
            lower_gold = np.array([15, 120, 120])
            upper_gold = np.array([35, 255, 255])
            gold_mask = cv2.inRange(hsv_mid, lower_gold, upper_gold)
            if np.count_nonzero(gold_mask) / gold_mask.size > 0.02:
                return UIElement("PHASE", "PHASE_CHANGE_MID", 0.77, 0.46, 0.92)

        # Zona 2: Circular inferior derecha (0.91, 0.89)
        roi_corner = frame[int(h * 0.85):int(h * 0.96), int(w * 0.86):int(w * 0.96)]
        if roi_corner.size > 0:
            hsv_c = cv2.cvtColor(roi_corner, cv2.COLOR_BGR2HSV)
            lower_blue = np.array([100, 100, 100])
            upper_blue = np.array([130, 255, 255])
            blue_mask = cv2.inRange(hsv_c, lower_blue, upper_blue)
            if np.count_nonzero(blue_mask) / blue_mask.size > 0.03:
                return UIElement("PHASE", "PHASE_CHANGE_CORNER", 0.91, 0.89, 0.88)

        return None

    def detect_modal_buttons(self, frame: np.ndarray, w: int, h: int) -> Optional[UIElement]:
        """Detecta botones típicos 'OK' o 'NEXT' en modales centrados."""
        roi_ok = frame[int(h * 0.70):int(h * 0.85), int(w * 0.40):int(w * 0.60)]
        if roi_ok.size == 0:
            return None

        hsv = cv2.cvtColor(roi_ok, cv2.COLOR_BGR2HSV)
        # Botón verde / dorado de OK en Master Duel
        lower_green = np.array([35, 80, 80])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        if np.count_nonzero(mask) / mask.size > 0.04:
            return UIElement("BUTTON", "OK", 0.50, 0.76, 0.90)

        return None

    def detect_duel_result(self, frame: np.ndarray) -> Optional[str]:
        """
        Detects if duel finished with 'victory' or 'defeat'.
        """
        if frame is None or frame.size == 0:
            return None
        h, w = frame.shape[:2]
        center_roi = frame[int(h * 0.25):int(h * 0.55), int(w * 0.30):int(w * 0.70)]
        if center_roi.size == 0:
            return None

        hsv = cv2.cvtColor(center_roi, cv2.COLOR_BGR2HSV)
        # Victory: vibrant gold / cyan radiant banners
        lower_gold = np.array([15, 120, 150])
        upper_gold = np.array([32, 255, 255])
        gold_mask = cv2.inRange(hsv, lower_gold, upper_gold)
        gold_ratio = np.count_nonzero(gold_mask) / gold_mask.size
        if gold_ratio > 0.12:
            return "victory"

        # Defeat: dark red / purple tones
        lower_purple = np.array([130, 80, 80])
        upper_purple = np.array([170, 255, 255])
        purple_mask = cv2.inRange(hsv, lower_purple, upper_purple)
        purple_ratio = np.count_nonzero(purple_mask) / purple_mask.size
        if purple_ratio > 0.15:
            return "defeat"

        return None

    def detect_duel_context(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Extracts current turn phase, prompt presence, and active dialog status.
        """
        context = {
            "phase": "MAIN 1",
            "is_opponent_turn": False,
            "has_prompt": False,
            "prompt_type": None,
            "elements": []
        }
        if frame is None or frame.size == 0:
            return context

        h, w = frame.shape[:2]
        elements = self.detect_all(frame)
        context["elements"] = elements

        # Check phase button
        for el in elements:
            if el.element_type == "PHASE":
                context["phase"] = "MAIN 1"
            elif el.element_type == "BANNER" and el.name == "SELECT_POSITION":
                context["has_prompt"] = True
                context["prompt_type"] = "zone_selection"
            elif el.element_type == "BUTTON" and el.name in ["OK", "ACTIVATE"]:
                context["has_prompt"] = True
                context["prompt_type"] = "chain" if el.name == "ACTIVATE" else "confirmation"

        return context

    def find_action_circles(self, frame: np.ndarray) -> Dict[str, UIElement]:
        """
        Returns dictionary of currently visible action circles: 'summon', 'set', 'activate'.
        """
        res = {}
        if frame is None or frame.size == 0:
            return res
        h, w = frame.shape[:2]
        circles = self.detect_action_circles(frame, w, h)
        for c in circles:
            c.x = int(c.center_x * w)
            c.y = int(c.center_y * h)
            res[c.name.lower()] = c
        return res

    def is_zone_selection_prompt(self, frame: np.ndarray) -> bool:
        """Checks if game is prompting to choose a zone on the field."""
        if frame is None or frame.size == 0:
            return False
        h, w = frame.shape[:2]
        return self.detect_position_banner(frame, w, h) is not None

    def find_phase_buttons(self, frame: np.ndarray) -> Dict[str, UIElement]:
        """Returns dictionary of phase navigation buttons."""
        res = {}
        if frame is None or frame.size == 0:
            return res
        h, w = frame.shape[:2]
        p_btn = self.detect_phase_button(frame, w, h)
        if p_btn:
            p_btn.x = int(p_btn.center_x * w)
            p_btn.y = int(p_btn.center_y * h)
            res["battle"] = p_btn
            res["main2"] = p_btn
            res["end"] = p_btn
        return res

    def find_prompt_buttons(self, frame: np.ndarray) -> Dict[str, UIElement]:
        """Returns dictionary of modal prompt buttons (ok, cancel, yes, no)."""
        res = {}
        if frame is None or frame.size == 0:
            return res
        h, w = frame.shape[:2]
        m_btn = self.detect_modal_buttons(frame, w, h)
        if m_btn:
            m_btn.x = int(m_btn.center_x * w)
            m_btn.y = int(m_btn.center_y * h)
            res["ok"] = m_btn
            res["yes"] = m_btn
        return res
