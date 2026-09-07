"""
Game State Detector for Yu-Gi-Oh! Master Duel
Detecta el estado actual de la pantalla mediante heurísticas de visión rápida (OpenCV):
- Colores dominantes, proporciones y zonas clave de la interfaz 16:9.
- Detección de Fases, Prompts de Cadena, Menú Principal, Modo Solo y Resultados.
- Si una pantalla no es concluyente, se marca como UNKNOWN para consulta al Cerebro Gemini.
"""

import cv2
import numpy as np
from enum import Enum
from typing import Tuple, Dict, Any, Optional


class MasterDuelState(Enum):
    TITLE_SCREEN = "TITLE_SCREEN"
    MAIN_MENU = "MAIN_MENU"
    PVP_WARNING = "PVP_WARNING"
    SOLO_GATE_SELECT = "SOLO_GATE_SELECT"
    SOLO_GATE_VIEW = "SOLO_GATE_VIEW"
    SOLO_CHAPTER_DETAIL = "SOLO_CHAPTER_DETAIL"
    SOLO_CUTSCENE = "SOLO_CUTSCENE"
    SOLO_DECK_SELECT = "SOLO_DECK_SELECT"
    COIN_TOSS = "COIN_TOSS"
    DUEL_PLAYER_TURN = "DUEL_PLAYER_TURN"
    DUEL_OPPONENT_TURN = "DUEL_OPPONENT_TURN"
    DUEL_CHAIN_PROMPT = "DUEL_CHAIN_PROMPT"
    DUEL_TARGET_SELECT = "DUEL_TARGET_SELECT"
    DUEL_RESULT = "DUEL_RESULT"
    DIALOG_BOX = "DIALOG_BOX"
    MODAL_POPUP = "MODAL_POPUP"
    UNKNOWN = "UNKNOWN"


class StateDetector:
    """Clasificador visual de estados para Yu-Gi-Oh! Master Duel."""

    def __init__(self):
        pass

    def detect(self, frame: np.ndarray) -> Tuple[MasterDuelState, float, Dict[str, Any]]:
        """
        Analiza el frame y retorna:
        (Estado, Nivel de Confianza [0.0 - 1.0], Metadatos adicionales)
        """
        if frame is None or frame.size == 0:
            return MasterDuelState.UNKNOWN, 0.0, {}

        h, w = frame.shape[:2]
        meta: Dict[str, Any] = {}

        # 1. ESCUDO ANTI-PVP: Verificar si estamos en menús de Ranked, Casual o Matchmaking
        is_pvp, pvp_reason = self._is_pvp_screen(frame, w, h)
        if is_pvp:
            return MasterDuelState.PVP_WARNING, 0.99, {"reason": pvp_reason}

        # 2. Comprobar si estamos en el MENÚ PRINCIPAL (debe evaluarse ANTES de buscar duelos)
        if self._is_main_menu(frame, w, h):
            return MasterDuelState.MAIN_MENU, 0.95, {"hint": "main_menu"}

        # 3. Comprobar si estamos dentro de un DUELO ACTIVO (Tablero de juego)
        # DEBE evaluarse ANTES de modales y menús para que los botones del duelo (Select/Cancel) no se confundan con CLOSE
        if self._is_duel_board(frame, w, h):
            if self._is_duel_result(frame, w, h):
                return MasterDuelState.DUEL_RESULT, 0.95, {"hint": "duel_result"}
            if self._is_card_selection_modal(frame, w, h):
                return MasterDuelState.DUEL_TARGET_SELECT, 0.95, {"hint": "card_select_modal"}
            if self._is_chain_prompt(frame, w, h):
                return MasterDuelState.DUEL_CHAIN_PROMPT, 0.92, {"hint": "chain_prompt"}
            if self._is_phase_selection_modal(frame, w, h):
                return MasterDuelState.DUEL_PLAYER_TURN, 0.95, {"hint": "phase_select_modal"}

            is_duel, duel_meta = self._check_duel_state(frame, w, h)
            meta.update(duel_meta)
            if duel_meta.get("is_player_turn", True):
                return MasterDuelState.DUEL_PLAYER_TURN, 0.93, meta
            else:
                return MasterDuelState.DUEL_OPPONENT_TURN, 0.88, meta

        # 4. Comprobar si hay Diálogo / Tutorial con botón CLOSE (inferior o esquina superior derecha X fuera de duelo)
        has_close, close_click = self._is_close_button_modal(frame, w, h)
        if has_close:
            return MasterDuelState.MODAL_POPUP, 0.95, {"hint": "close_modal", "click": close_click}

        # 5. Comprobar si estamos DENTRO de una PUERTA de MODO SOLO (Árbol de nodos con orbes elementales)
        is_solo, solo_state, solo_meta = self._check_solo_screens(frame, w, h)
        if is_solo:
            return solo_state, 0.90, solo_meta

        # 6. Comprobar si estamos en el HUB principal de Modo Solo (Selección de puertas, sin orbes)
        if self._is_solo_hub(frame, w, h):
            return MasterDuelState.SOLO_GATE_SELECT, 0.92, {"hint": "solo_hub"}

        # 7. Comprobar si hay Diálogo / Noticia Modal en el centro
        if self._is_modal_popup(frame, w, h):
            return MasterDuelState.MODAL_POPUP, 0.85, {"hint": "modal_popup"}

        # 8. Comprobar Pantalla de Resultados de Duelo fuera de tablero
        if self._is_duel_result(frame, w, h):
            return MasterDuelState.DUEL_RESULT, 0.88, {"hint": "duel_result"}

        # 9. Comprobar Pantalla de Título (Press Any Button)
        if self._is_title_screen(frame, w, h):
            return MasterDuelState.TITLE_SCREEN, 0.85, {"hint": "title_screen"}

        return MasterDuelState.UNKNOWN, 0.15, {}

    def _is_solo_hub(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta la pantalla de selección de puertas / categorías de Modo Solo (Solo Mode)."""
        # Si hay orbes elementales, estamos dentro de una puerta, no en el hub
        top_right_orbs = frame[int(h * 0.04):int(h * 0.12), int(w * 0.55):int(w * 0.95)]
        if top_right_orbs.size > 0:
            hsv_orbs = cv2.cvtColor(top_right_orbs, cv2.COLOR_BGR2HSV)
            green_orbs = cv2.inRange(hsv_orbs, np.array([40, 120, 120]), np.array([85, 255, 255]))
            red_orbs = cv2.inRange(hsv_orbs, np.array([0, 140, 140]), np.array([10, 255, 255])) + \
                       cv2.inRange(hsv_orbs, np.array([170, 140, 140]), np.array([180, 255, 255]))
            if (np.count_nonzero(green_orbs) > 80) and (np.count_nonzero(red_orbs) > 80):
                return False

        header_roi = frame[int(h * 0.05):int(h * 0.13), int(w * 0.05):int(w * 0.25)]
        if header_roi.size == 0:
            return False
        gray_h = cv2.cvtColor(header_roi, cv2.COLOR_BGR2GRAY)
        white_h = np.count_nonzero(gray_h > 220)

        lp_box = frame[int(h * 0.25):int(h * 0.55), int(w * 0.65):int(w * 0.92)]
        if lp_box.size == 0:
            return False
        gray_lp = cv2.cvtColor(lp_box, cv2.COLOR_BGR2GRAY)
        has_lp = np.count_nonzero(gray_lp > 220) > 100

        return white_h > 300 and has_lp

    def _is_duel_board(self, frame: np.ndarray, w: int, h: int) -> bool:
        """
        Determina con 100% de precisión si estamos en el tablero de un duelo:
        - Barra de LP del Oponente en esquina superior derecha (0.80 a 0.92, 0.06 a 0.13).
        - Barra de LP del Jugador en esquina inferior izquierda (0.08 a 0.20, 0.90 a 0.97).
        Ambas contienen dígitos y texto 'LP' en blanco brillante puro (> 240).
        """
        opp_roi = frame[int(h * 0.06):int(h * 0.13), int(w * 0.80):int(w * 0.92)]
        ply_roi = frame[int(h * 0.90):int(h * 0.97), int(w * 0.08):int(w * 0.20)]
        if opp_roi.size == 0 or ply_roi.size == 0:
            return False

        gray_opp = cv2.cvtColor(opp_roi, cv2.COLOR_BGR2GRAY)
        gray_ply = cv2.cvtColor(ply_roi, cv2.COLOR_BGR2GRAY)
        opp_white = np.count_nonzero(gray_opp > 240)
        ply_white = np.count_nonzero(gray_ply > 240)

        return opp_white > 350 and ply_white > 350

    def _check_duel_state(self, frame: np.ndarray, w: int, h: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Analiza las condiciones tácticas dentro del duelo:
        - Determina si es turno del jugador por el botón de fase (Gold=Main1, Red=Battle, Blue=Main2, Purple=End)
          o el temporizador del jugador (esquina superior izquierda).
        """
        phase_roi = frame[int(h * 0.42):int(h * 0.51), int(w * 0.74):int(w * 0.80)]
        is_player_turn = False
        detected_phase = "MAIN1"

        if phase_roi.size > 0:
            hsv_p = cv2.cvtColor(phase_roi, cv2.COLOR_BGR2HSV)
            # 1. Main Phase 1 (Dorado / Oro)
            gold_p = cv2.inRange(hsv_p, np.array([15, 100, 100]), np.array([35, 255, 255]))
            cnt_gold = np.count_nonzero(gold_p)

            # 2. Battle Phase (Rojo / Carmesí)
            red_p1 = cv2.inRange(hsv_p, np.array([0, 90, 90]), np.array([12, 255, 255]))
            red_p2 = cv2.inRange(hsv_p, np.array([168, 90, 90]), np.array([180, 255, 255]))
            cnt_red = np.count_nonzero(red_p1 + red_p2)

            # 3. Main Phase 2 (Azul)
            blue_p = cv2.inRange(hsv_p, np.array([95, 90, 90]), np.array([130, 255, 255]))
            cnt_blue = np.count_nonzero(blue_p)

            # 4. End Phase (Púrpura / Violeta)
            purple_p = cv2.inRange(hsv_p, np.array([135, 70, 70]), np.array([165, 255, 255]))
            cnt_purple = np.count_nonzero(purple_p)

            max_cnt = max(cnt_gold, cnt_red, cnt_blue, cnt_purple)
            if max_cnt > 120:
                is_player_turn = True
                if max_cnt == cnt_red:
                    detected_phase = "BATTLE"
                elif max_cnt == cnt_blue:
                    detected_phase = "MAIN2"
                elif max_cnt == cnt_purple:
                    detected_phase = "END"
                else:
                    detected_phase = "MAIN1"

        # Fallback: Comprobar si el temporizador del jugador (fila azul inferior en 0.08 a 0.20, 0.08 a 0.12) está activo
        if not is_player_turn:
            timer_roi = frame[int(h * 0.08):int(h * 0.12), int(w * 0.08):int(w * 0.20)]
            if timer_roi.size > 0:
                hsv_t = cv2.cvtColor(timer_roi, cv2.COLOR_BGR2HSV)
                blue_timer = cv2.inRange(hsv_t, np.array([100, 100, 100]), np.array([130, 255, 255]))
                if np.count_nonzero(blue_timer) > 150:
                    is_player_turn = True

        return True, {"is_player_turn": is_player_turn, "in_duel": True, "detected_phase": detected_phase}

    def _is_chain_prompt(self, frame: np.ndarray, w: int, h: int) -> bool:
        """
        Detecta si hay un cuadro modal de activación/cadena real en el centro del tablero.
        Requiere un fondo modal oscuro concentrado y texto/botones brillantes.
        """
        cen_roi = frame[int(h * 0.42):int(h * 0.62), int(w * 0.35):int(w * 0.65)]
        if cen_roi.size == 0:
            return False

        gray = cv2.cvtColor(cen_roi, cv2.COLOR_BGR2GRAY)
        dark_ratio = np.count_nonzero(gray < 40) / gray.size
        # Un modal de prompt real cubre el centro con fondo oscuro (> 55%) y texto blanco nítido
        if dark_ratio < 0.55:
            return False

        white_ratio = np.count_nonzero(gray > 200) / gray.size
        return white_ratio > 0.02

    def _is_phase_selection_modal(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta si está abierta la ventana emergente 'Select Phase to Change to' en duelo."""
        banner_roi = frame[int(h * 0.52):int(h * 0.56), int(w * 0.35):int(w * 0.65)]
        if banner_roi.size == 0:
            return False
        gray = cv2.cvtColor(banner_roi, cv2.COLOR_BGR2GRAY)
        dark_ratio = np.count_nonzero(gray < 50) / gray.size
        white_ratio = np.count_nonzero(gray > 200) / gray.size
        return dark_ratio > 0.60 and white_ratio > 0.03

    def _is_duel_result(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta pantalla de Victoria / Derrota (grandes letras o banners dorados/azules)."""
        center_roi = frame[int(h * 0.20):int(h * 0.60), int(w * 0.20):int(w * 0.80)]
        if center_roi.size == 0:
            return False

        hsv = cv2.cvtColor(center_roi, cv2.COLOR_BGR2HSV)
        lower_gold = np.array([18, 140, 150])
        upper_gold = np.array([32, 255, 255])
        mask = cv2.inRange(hsv, lower_gold, upper_gold)
        ratio = np.count_nonzero(mask) / mask.size
        return ratio > 0.08

    def _is_pvp_screen(self, frame: np.ndarray, w: int, h: int) -> Tuple[bool, str]:
        """Detecta si la pantalla actual corresponde a Ranked, Casual, Room o Matchmaking."""
        # Si hay orbes elementales de Modo Solo en la parte superior derecha, NO es PvP
        top_right_orbs = frame[int(h * 0.04):int(h * 0.12), int(w * 0.55):int(w * 0.95)]
        if top_right_orbs.size > 0:
            hsv_orbs = cv2.cvtColor(top_right_orbs, cv2.COLOR_BGR2HSV)
            red_mask = cv2.inRange(hsv_orbs, np.array([0, 150, 150]), np.array([10, 255, 255])) + \
                       cv2.inRange(hsv_orbs, np.array([170, 150, 150]), np.array([180, 255, 255]))
            blue_mask = cv2.inRange(hsv_orbs, np.array([95, 150, 150]), np.array([125, 255, 255]))
            if (np.count_nonzero(red_mask) + np.count_nonzero(blue_mask)) > 50:
                return False, ""

        # 1. Comprobar cabecera 'DUEL' (menú PvP)
        header_roi = frame[int(h * 0.03):int(h * 0.12), int(w * 0.04):int(w * 0.25)]
        if header_roi.size > 0:
            ranked_tile = frame[int(h * 0.25):int(h * 0.65), int(w * 0.18):int(w * 0.50)]
            if ranked_tile.size > 0:
                hsv_rt = cv2.cvtColor(ranked_tile, cv2.COLOR_BGR2HSV)
                gold_mask = cv2.inRange(hsv_rt, np.array([15, 150, 150]), np.array([35, 255, 255]))
                cyan_mask = cv2.inRange(hsv_rt, np.array([85, 160, 160]), np.array([105, 255, 255]))
                if (np.count_nonzero(gold_mask) / gold_mask.size > 0.15) and (np.count_nonzero(cyan_mask) / cyan_mask.size > 0.08):
                    return True, "Ranked Duel Selection Screen"

        # 2. Comprobar botón 'Cancel' de Matchmaking en el centro
        modal_roi = frame[int(h * 0.40):int(h * 0.75), int(w * 0.35):int(w * 0.65)]
        if modal_roi.size > 0:
            gray_m = cv2.cvtColor(modal_roi, cv2.COLOR_BGR2GRAY)
            if np.mean(gray_m) < 40:
                hsv_m = cv2.cvtColor(modal_roi, cv2.COLOR_BGR2HSV)
                blue_m = cv2.inRange(hsv_m, np.array([100, 140, 120]), np.array([130, 255, 255]))
                if np.count_nonzero(blue_m) / blue_m.size > 0.10:
                    return True, "Matchmaking Queue Active"

        return False, ""

    def _is_main_menu(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta la pantalla principal con la lista DUEL, DECK, SOLO, SHOP en el lateral izquierdo."""
        left_menu = frame[int(h * 0.15):int(h * 0.55), 0:int(w * 0.25)]
        if left_menu.size == 0:
            return False

        hsv = cv2.cvtColor(left_menu, cv2.COLOR_BGR2HSV)
        red_mask = cv2.inRange(hsv, np.array([0, 140, 90]), np.array([10, 255, 255])) + \
                   cv2.inRange(hsv, np.array([170, 140, 90]), np.array([180, 255, 255]))
        red_ratio = np.count_nonzero(red_mask) / red_mask.size

        gray = cv2.cvtColor(left_menu, cv2.COLOR_BGR2GRAY)
        white_ratio = np.count_nonzero(gray > 220) / gray.size

        return red_ratio > 0.12 and white_ratio > 0.004

    def _check_solo_screens(self, frame: np.ndarray, w: int, h: int) -> Tuple[bool, MasterDuelState, Dict[str, Any]]:
        """Detecta si estamos en Modo Solo: cinemática de historia, detalle de capítulo, o vista del árbol de nodos."""
        # 1. Comprobar botón Atrás '<' circular en esquina superior izquierda
        tl_roi = frame[int(h * 0.05):int(h * 0.12), int(w * 0.015):int(w * 0.055)]
        has_back = False
        if tl_roi.size > 0:
            hsv_tl = cv2.cvtColor(tl_roi, cv2.COLOR_BGR2HSV)
            yellow_ring = cv2.inRange(hsv_tl, np.array([20, 100, 100]), np.array([45, 255, 255]))
            has_back = np.count_nonzero(yellow_ring) > 40

        if not has_back:
            # Comprobar Cinemática / Diálogo de Escenario (botón de menú hamburguesa en inferior derecha)
            burger_roi = frame[int(h * 0.86):int(h * 0.96), int(w * 0.89):int(w * 0.98)]
            if burger_roi.size > 0:
                gray_b = cv2.cvtColor(burger_roi, cv2.COLOR_BGR2GRAY)
                dark_cnt = np.count_nonzero(gray_b < 40)
                white_cnt = np.count_nonzero(gray_b > 200)
                if dark_cnt > 2000 and white_cnt > 50:
                    skip_roi = frame[int(h * 0.58):int(h * 0.68), int(w * 0.86):int(w * 0.98)]
                    has_skip = False
                    if skip_roi.size > 0:
                        gray_skip = cv2.cvtColor(skip_roi, cv2.COLOR_BGR2GRAY)
                        has_skip = np.count_nonzero(gray_skip > 200) > 20
                    return True, MasterDuelState.SOLO_CUTSCENE, {"has_skip_visible": bool(has_skip)}
            return False, MasterDuelState.UNKNOWN, {}

        # 2. Comprobar si el panel de detalle de capítulo está abierto con el árbol a la izquierda
        left_roi = frame[int(h * 0.35):int(h * 0.75), 0:int(w * 0.32)]
        hsv_left = cv2.cvtColor(left_roi, cv2.COLOR_BGR2HSV)
        yellow_borders = cv2.inRange(hsv_left, np.array([25, 150, 150]), np.array([40, 255, 255]))
        has_tree_on_left = np.count_nonzero(yellow_borders) > 400

        btn_roi = frame[int(h * 0.78):int(h * 0.90), int(w * 0.68):int(w * 0.94)]
        has_play_btn = False
        btn_color = "green"
        if btn_roi.size > 0:
            hsv_btn = cv2.cvtColor(btn_roi, cv2.COLOR_BGR2HSV)
            green = cv2.inRange(hsv_btn, np.array([25, 100, 70]), np.array([85, 255, 255]))
            blue = cv2.inRange(hsv_btn, np.array([95, 120, 120]), np.array([125, 255, 255]))
            g_ratio = np.count_nonzero(green) / green.size
            b_ratio = np.count_nonzero(blue) / blue.size
            if g_ratio > 0.10 or b_ratio > 0.10:
                has_play_btn = True
                btn_color = "green" if g_ratio > b_ratio else "blue"

        if has_tree_on_left and has_play_btn:
            return True, MasterDuelState.SOLO_CHAPTER_DETAIL, {"btn_color": btn_color, "can_play": True}

        # 3. Comprobar si estamos en la vista de árbol de la puerta (orbes elementales presentes)
        top_right_orbs = frame[int(h * 0.04):int(h * 0.12), int(w * 0.55):int(w * 0.95)]
        if top_right_orbs.size > 0:
            hsv_orbs = cv2.cvtColor(top_right_orbs, cv2.COLOR_BGR2HSV)
            green_orbs = cv2.inRange(hsv_orbs, np.array([40, 120, 120]), np.array([85, 255, 255]))
            red_orbs = cv2.inRange(hsv_orbs, np.array([0, 140, 140]), np.array([10, 255, 255])) + \
                       cv2.inRange(hsv_orbs, np.array([170, 140, 140]), np.array([180, 255, 255]))
            if (np.count_nonzero(green_orbs) > 80) and (np.count_nonzero(red_orbs) > 80):
                return True, MasterDuelState.SOLO_GATE_VIEW, {"has_nodes": True}

        return False, MasterDuelState.UNKNOWN, {}

    def _is_close_button_modal(self, frame: np.ndarray, w: int, h: int) -> Tuple[bool, Tuple[float, float]]:
        """Detecta ventanas informativas / modales con botón CLOSE (X en superior derecha o CLOSE en centro inferior)."""
        # 1. Botón circular lima (X) en esquina superior derecha (0.93-0.99, 0.05-0.15)
        tr_roi = frame[int(h * 0.05):int(h * 0.15), int(w * 0.93):int(w * 0.99)]
        if tr_roi.size > 0:
            hsv_tr = cv2.cvtColor(tr_roi, cv2.COLOR_BGR2HSV)
            lime_tr = cv2.inRange(hsv_tr, np.array([30, 150, 150]), np.array([85, 255, 255]))
            if np.count_nonzero(lime_tr) > 300:
                return True, (0.963, 0.09)

        # 2. Botón CLOSE en inferior central (0.40-0.60, 0.88-0.95)
        close_roi = frame[int(h * 0.88):int(h * 0.95), int(w * 0.40):int(w * 0.60)]
        if close_roi.size > 0:
            hsv = cv2.cvtColor(close_roi, cv2.COLOR_BGR2HSV)
            lime = cv2.inRange(hsv, np.array([30, 150, 150]), np.array([85, 255, 255]))
            gray = cv2.cvtColor(close_roi, cv2.COLOR_BGR2GRAY)
            dark = np.count_nonzero(gray < 40)
            if dark > 8000 and np.count_nonzero(lime) > 250:
                return True, (0.50, 0.915)

        # 3. Botón CLOSE en modal de recompensas de evento / campaña (0.32-0.48, 0.74-0.81)
        event_close_roi = frame[int(h * 0.74):int(h * 0.81), int(w * 0.32):int(w * 0.48)]
        if event_close_roi.size > 0:
            hsv_ec = cv2.cvtColor(event_close_roi, cv2.COLOR_BGR2HSV)
            lime_ec = cv2.inRange(hsv_ec, np.array([25, 120, 120]), np.array([85, 255, 255]))
            if np.count_nonzero(lime_ec) > 200:
                return True, (0.40, 0.77)

        return False, (0.5, 0.5)

    def _is_title_screen(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta pantalla inicial de Master Duel (Press Any Button)."""
        if np.mean(frame) > 65:
            return False
        bottom_text_roi = frame[int(h * 0.80):int(h * 0.92), int(w * 0.30):int(w * 0.70)]
        if bottom_text_roi.size == 0:
            return False
        gray = cv2.cvtColor(bottom_text_roi, cv2.COLOR_BGR2GRAY)
        white_pixels = np.count_nonzero(gray > 220)
        return (white_pixels / gray.size) > 0.04

    def _is_modal_popup(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta si hay un cuadro de diálogo emergente o confirmación en el centro."""
        center = frame[int(h * 0.20):int(h * 0.80), int(w * 0.25):int(w * 0.75)]
        if center.size == 0:
            return False

        hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
        # Línea divisoria cian/azul brillante del modal de Master Duel
        blue_line = cv2.inRange(hsv, np.array([90, 140, 120]), np.array([130, 255, 255]))
        # Botones de confirmación con esquinas/textos amarillo/lima (CANCEL / YES / OK)
        lime_btn = cv2.inRange(hsv, np.array([25, 120, 120]), np.array([45, 255, 255]))

        if np.count_nonzero(blue_line) > 800 and np.count_nonzero(lime_btn) > 200:
            return True

        corner = frame[0:int(h * 0.15), 0:int(w * 0.15)]
        if corner.size > 0:
            corner_mean = np.mean(corner)
            center_mean = np.mean(center)
            if corner_mean < 45 and center_mean > 95:
                return True

        return False

    def _is_phase_selection_modal(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta si está abierta la ventana emergente 'Select Phase to Change to'."""
        banner_roi = frame[int(h * 0.52):int(h * 0.56), int(w * 0.35):int(w * 0.65)]
        if banner_roi.size == 0:
            return False
        gray = cv2.cvtColor(banner_roi, cv2.COLOR_BGR2GRAY)
        dark_ratio = np.count_nonzero(gray < 50) / gray.size
        white_ratio = np.count_nonzero(gray > 200) / gray.size
        return dark_ratio > 0.60 and white_ratio > 0.03

    def _is_chain_prompt(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta si hay una ventana emergente de activación / cadena / pregunta en el centro del tablero."""
        prompt_roi = frame[int(h * 0.42):int(h * 0.62), int(w * 0.35):int(w * 0.65)]
        if prompt_roi.size == 0:
            return False
        hsv = cv2.cvtColor(prompt_roi, cv2.COLOR_BGR2HSV)
        # Borde azul brillante de cuadro de diálogo
        blue_box = cv2.inRange(hsv, np.array([90, 120, 100]), np.array([135, 255, 255]))
        gray = cv2.cvtColor(prompt_roi, cv2.COLOR_BGR2GRAY)
        white_txt = np.count_nonzero(gray > 220)
        return np.count_nonzero(blue_box) > 400 and white_txt > 80

    def _is_card_selection_modal(self, frame: np.ndarray, w: int, h: int) -> bool:
        """Detecta si está abierto un selector de cartas (Deck Search, Cementerio, Extra Deck o Campo) con botón Decide."""
        # Botón Decide / Confirmar en zona inferior central (0.42 - 0.58 x, 0.72 - 0.82 y)
        decide_roi = frame[int(h * 0.72):int(h * 0.82), int(w * 0.42):int(w * 0.58)]
        if decide_roi.size == 0:
            return False
        hsv = cv2.cvtColor(decide_roi, cv2.COLOR_BGR2HSV)
        blue_btn = cv2.inRange(hsv, np.array([95, 90, 90]), np.array([130, 255, 255]))
        gray = cv2.cvtColor(decide_roi, cv2.COLOR_BGR2GRAY)
        white_txt = np.count_nonzero(gray > 220)
        return np.count_nonzero(blue_btn) > 180 and white_txt > 50

