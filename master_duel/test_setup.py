"""
Test & Diagnostics for Master Duel Bot Setup
Valida la configuración de entorno, API de Gemini y detección de ventana.
"""

import os
import sys
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from master_duel.vision.screen_capture import ScreenCapture
from master_duel.brain.gemini_brain import MasterDuelBrain
from master_duel.vision.state_detector import StateDetector


def test_environment():
    print("=" * 60)
    print("  COMPROBACIÓN DE ENTORNO: BOT MASTER DUEL")
    print("=" * 60)

    # 1. Verificar OpenCV
    print(f"[OK] OpenCV Version: {cv2.__version__}")

    # 2. Verificar Gemini Brain
    brain = MasterDuelBrain()
    print(f"[*] Modelo configurado: {brain.model}")
    if brain.is_available():
        print(f"[OK] Gemini API Key detectada correctamente (longitud: {len(brain.api_key)})")
    else:
        print("[WARN] No se detectó GEMINI_API_KEY en .env")

    # 3. Verificar Detección de Ventana
    cap = ScreenCapture()
    gw = cap.find_game_window()
    if gw:
        print(f"[OK] Ventana de Master Duel detectada: {gw}")
        frame = cap.capture_frame()
        if frame is not None:
            print(f"[OK] Captura de pantalla exitosa: {frame.shape[1]}x{frame.shape[0]} px")
            detector = StateDetector()
            state, conf, meta = detector.detect(frame)
            print(f"[OK] Estado detectado: {state.value} (Confianza: {int(conf * 100)}%)")
        else:
            print("[WARN] No se pudo capturar el frame de la ventana.")
    else:
        print("[INFO] La ventana de Master Duel no está abierta actualmente.")
        print("       (El bot la detectará automáticamente en cuanto inicies el juego).")

    print("=" * 60)
    print("  DIAGNÓSTICO COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    test_environment()
