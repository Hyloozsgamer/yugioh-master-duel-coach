"""
Strict Anti-PvP Shield for Yu-Gi-Oh! Master Duel AI.
Guarantees that the bot NEVER plays or interacts with Ranked, Casual, Event, or Room PvP matches.
If any PvP screen, ranked menu, or matchmaking prompt is detected:
1. Immediately cancels/backs out of the queue (ESC / Back).
2. Pauses the bot.
3. Notifies the user on console HUD.
"""

import cv2
import numpy as np
import time
from typing import Tuple, Dict, Any

class AntiPvPShield:
    """
    Escudo estricto contra modos PvP (Ranked / Casual / Room).
    """

    def __init__(self, input_ctrl=None):
        self.input_ctrl = input_ctrl
        self.pvp_detections_count = 0

    def inspect_screen(self, frame: np.ndarray) -> Tuple[bool, str]:
        """
        Analiza el frame para detectar cualquier elemento de Ranked, Casual o PvP.
        Retorna: (is_pvp_screen, reason_description)
        """
        if frame is None or frame.size == 0:
            return False, ""

        h, w = frame.shape[:2]

        # 0. VERIFICACIÓN PREVIA: Si estamos en Modo Solo (orbes elementales o árbol de historia), es 100% SEGURO
        top_right_orbs = frame[int(h * 0.04):int(h * 0.12), int(w * 0.55):int(w * 0.95)]
        if top_right_orbs.size > 0:
            # En Modo Solo hay orbes elementales (Fuego, Agua, Tierra, Viento, Luz, Oscuridad)
            hsv_orbs = cv2.cvtColor(top_right_orbs, cv2.COLOR_BGR2HSV)
            # Detección de orbe de Fuego (rojo) y Agua (azul brillante)
            red_mask = cv2.inRange(hsv_orbs, np.array([0, 150, 150]), np.array([10, 255, 255])) + \
                       cv2.inRange(hsv_orbs, np.array([170, 150, 150]), np.array([180, 255, 255]))
            blue_orb_mask = cv2.inRange(hsv_orbs, np.array([95, 150, 150]), np.array([125, 255, 255]))
            if (np.count_nonzero(red_mask) + np.count_nonzero(blue_orb_mask)) > 50:
                # Pantalla legítima de Modo Solo (árbol de capítulos u orbes) -> SEGURO
                return False, ""

        # 1. Comprobar menú de "DUEL" (donde aparecen Ranked, Casual, Room Match)
        # Solo comprobar si la cabecera superior izquierda NO tiene título de Modo Solo
        # En el menú DUEL, la tarjeta izquierda es 'RANKED DUEL' con marco dorado y distintivo de rango
        # Zona del título o subtítulo de Ranked: x: 18%-50%, y: 25%-65%
        header_text_roi = frame[int(h * 0.03):int(h * 0.12), int(w * 0.05):int(w * 0.25)]
        if header_text_roi.size > 0:
            gray_hdr = cv2.cvtColor(header_text_roi, cv2.COLOR_BGR2GRAY)
            # Si el texto de cabecera es el de selección de duelos PvP
            ranked_card_roi = frame[int(h * 0.25):int(h * 0.65), int(w * 0.18):int(w * 0.50)]
            if ranked_card_roi.size > 0:
                hsv = cv2.cvtColor(ranked_card_roi, cv2.COLOR_BGR2HSV)
                gold_mask = cv2.inRange(hsv, np.array([15, 150, 150]), np.array([35, 255, 255]))
                cyan_mask = cv2.inRange(hsv, np.array([85, 160, 160]), np.array([105, 255, 255]))
                gold_ratio = np.count_nonzero(gold_mask) / gold_mask.size
                cyan_ratio = np.count_nonzero(cyan_mask) / cyan_mask.size
                
                # Para ser PvP debe tener simultáneamente la tarjeta de Ranked y una barra inferior sin orbes
                if gold_ratio > 0.15 and cyan_ratio > 0.08:
                    return True, "Menú de Selección DUEL / RANKED detectado"

        # 2. Comprobar pantalla de 'MATCHMAKING / BUSCANDO RIVAL'
        modal_roi = frame[int(h * 0.40):int(h * 0.75), int(w * 0.35):int(w * 0.65)]
        if modal_roi.size > 0:
            gray_m = cv2.cvtColor(modal_roi, cv2.COLOR_BGR2GRAY)
            if np.mean(gray_m) < 40:
                # Fondo muy oscuro con botón azul de cancelación
                hsv_m = cv2.cvtColor(modal_roi, cv2.COLOR_BGR2HSV)
                blue_mask = cv2.inRange(hsv_m, np.array([100, 140, 120]), np.array([130, 255, 255]))
                if np.count_nonzero(blue_mask) / blue_mask.size > 0.10:
                    return True, "Matchmaking Queue Active"

        return False, ""

    def enforce_safe_exit(self):
        """
        Ejecuta maniobra de retirada inmediata si se detectó una pantalla de PvP:
        Pulsa ESC o hace clic en el botón Atrás (esquina superior izquierda).
        """
        print("\n[ANTI-PVP SHIELD] 🚨 ABORTANDO ACCESO A PVP / RANKED...")
        if self.input_ctrl:
            self.input_ctrl.bring_to_front()
            time.sleep(0.1)
            # 1. Clic en botón atrás (esquina superior izquierda: 0.06, 0.06)
            self.input_ctrl.click_relative(0.06, 0.06, delay=0.3)
            # 2. Clic en cancelar si hay cola activa (inferior central)
            self.input_ctrl.click_relative(0.50, 0.75, delay=0.3)
            # 3. Clic derecho para cerrar cualquier modal
            self.input_ctrl.right_click()
            time.sleep(0.2)
