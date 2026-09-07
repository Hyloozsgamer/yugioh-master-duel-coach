"""
Game Vision — Capa unificada de visión para Master Duel.
Combina ScreenCapture + YOLODetector en una API única.

Uso:
    vision = GameVision()
    vision.start()

    frame_info = vision.get_latest()
    if frame_info.has_dialog():
        btn = frame_info.best_button()
        ...

    vision.stop()
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable
import numpy as np

from master_duel.vision.screen_capture import ScreenCapture
from master_duel.vision.yolo_detector import YOLODetector, YOLOFrame


# ─── Configuración ────────────────────────────────────────────────────────────
TARGET_FPS       = 10       # Inferencias por segundo (10fps es suficiente para duelos)
CAPTURE_INTERVAL = 1.0 / TARGET_FPS
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class VisionStats:
    """Estadísticas en tiempo real del sistema de visión."""
    frames_captured: int = 0
    frames_processed: int = 0
    avg_inference_ms: float = 0.0
    last_update: float = 0.0
    game_window_found: bool = False
    yolo_ready: bool = False
    running: bool = False


class GameVision:
    """
    Sistema de visión unificado para Master Duel.

    Captura la pantalla continuamente y ejecuta YOLO11
    en tiempo real, manteniendo siempre el último frame analizado.

    Arquitectura:
        Thread captura → queue → Thread YOLO → YOLOFrame latest
    """

    def __init__(
        self,
        yolo_model_path: Optional[str] = None,
        confidence: float = 0.45,
        fps: int = TARGET_FPS,
        on_frame: Optional[Callable[[YOLOFrame], None]] = None,
    ):
        self._capture = ScreenCapture()
        self._detector = YOLODetector(
            model_path=yolo_model_path,
            confidence=confidence,
        )
        self._fps = fps
        self._interval = 1.0 / fps
        self._on_frame = on_frame  # Callback opcional por cada frame

        self._latest_frame: Optional[YOLOFrame] = None
        self._latest_raw: Optional[np.ndarray] = None
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stats = VisionStats()

        self._stats.yolo_ready = self._detector.is_ready

    # ─── API Pública ──────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Inicia el loop de captura+detección en un thread de fondo."""
        if self._running:
            return True

        # Intentar encontrar ventana del juego
        window = self._capture.find_game_window()
        if window is None:
            print("[GameVision] AVISO: Ventana de Master Duel no encontrada.")
            print("             El bot iniciará cuando el juego esté abierto.")

        self._stats.game_window_found = window is not None
        self._running = True
        self._stats.running = True
        self._thread = threading.Thread(
            target=self._vision_loop,
            name="GameVisionLoop",
            daemon=True,
        )
        self._thread.start()
        print(f"[GameVision] ✓ Iniciado a {self._fps} FPS")
        return True

    def stop(self):
        """Detiene el loop de visión."""
        self._running = False
        self._stats.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        print("[GameVision] Detenido.")

    def get_latest(self) -> Optional[YOLOFrame]:
        """Devuelve el último YOLOFrame procesado (thread-safe)."""
        with self._lock:
            return self._latest_frame

    def get_raw_frame(self) -> Optional[np.ndarray]:
        """Devuelve la última captura de pantalla sin procesar."""
        with self._lock:
            return self._latest_raw.copy() if self._latest_raw is not None else None

    def capture_once(self) -> Optional[YOLOFrame]:
        """Captura y detecta un único frame de forma síncrona."""
        raw = self._capture_screen()
        if raw is None:
            return None
        result = self._detector.detect(raw)
        with self._lock:
            self._latest_frame = result
            self._latest_raw = raw
        return result

    def wait_for_condition(
        self,
        condition: Callable[[YOLOFrame], bool],
        timeout: float = 10.0,
        poll_interval: float = 0.2,
    ) -> Optional[YOLOFrame]:
        """
        Espera hasta que una condición se cumpla sobre el último frame.
        Útil para esperar a que aparezca un botón o desaparezca un diálogo.

        Ejemplo:
            frame = vision.wait_for_condition(lambda f: f.has_button("btn_ok"), timeout=5)
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            frame = self.get_latest()
            if frame and condition(frame):
                return frame
            time.sleep(poll_interval)
        return None  # Timeout

    @property
    def stats(self) -> VisionStats:
        return self._stats

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def yolo_ready(self) -> bool:
        return self._detector.is_ready

    # ─── Loop Interno ─────────────────────────────────────────────────────────

    def _vision_loop(self):
        """Thread principal de captura y detección YOLO."""
        inference_times = []
        last_window_check = 0.0

        while self._running:
            t_start = time.perf_counter()

            # Re-intentar encontrar ventana del juego cada 5s si no está
            if not self._stats.game_window_found and (time.time() - last_window_check) > 5.0:
                window = self._capture.find_game_window()
                self._stats.game_window_found = window is not None
                last_window_check = time.time()

            # Capturar pantalla
            raw = self._capture_screen()
            if raw is None:
                time.sleep(0.5)
                continue

            self._stats.frames_captured += 1

            # Inferencia YOLO
            if self._detector.is_ready:
                result = self._detector.detect(raw)
                inference_times.append(result.inference_ms)
                if len(inference_times) > 30:
                    inference_times.pop(0)
                self._stats.avg_inference_ms = sum(inference_times) / len(inference_times)
                self._stats.frames_processed += 1
            else:
                # Sin modelo YOLO: frame vacío
                result = YOLOFrame()

            self._stats.last_update = time.time()

            # Actualizar estado compartido
            with self._lock:
                self._latest_frame = result
                self._latest_raw = raw

            # Callback externo
            if self._on_frame:
                try:
                    self._on_frame(result)
                except Exception as e:
                    print(f"[GameVision] Error en callback: {e}")

            # Mantener el FPS objetivo
            elapsed = time.perf_counter() - t_start
            sleep_time = self._interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _capture_screen(self) -> Optional[np.ndarray]:
        """Captura la pantalla usando mss."""
        try:
            import mss
            import cv2
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Monitor principal
                shot = sct.grab(monitor)
                frame = np.array(shot)
                return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            return None

    # ─── Helpers para el bot ──────────────────────────────────────────────────

    def is_dialog_open(self) -> bool:
        """True si hay algún popup o botón de confirmación en pantalla."""
        frame = self.get_latest()
        if frame is None:
            return False
        return frame.has_dialog() or len(frame.buttons()) > 0

    def get_best_action_button(self):
        """Devuelve el mejor botón para clicar ahora (por prioridad)."""
        frame = self.get_latest()
        if frame is None:
            return None
        # Prioridad: efecto > ok > skip > end_phase > attack
        priority = ["btn_effect", "btn_ok", "btn_skip", "btn_end_phase", "btn_attack"]
        for btn_name in priority:
            if frame.has_button(btn_name):
                hits = frame.by_class(btn_name)
                if hits:
                    return max(hits, key=lambda d: d.confidence)
        return None

    def print_status(self):
        """Imprime estado actual del sistema de visión."""
        s = self._stats
        frame = self.get_latest()
        print(f"\n[GameVision Status]")
        print(f"  Running:       {s.running}")
        print(f"  YOLO Ready:    {s.yolo_ready}")
        print(f"  Game Window:   {s.game_window_found}")
        print(f"  Frames cap:    {s.frames_captured}")
        print(f"  Frames proc:   {s.frames_processed}")
        print(f"  Avg YOLO ms:   {s.avg_inference_ms:.1f}ms")
        if frame:
            print(f"  Last frame:    {frame.summary()}")
