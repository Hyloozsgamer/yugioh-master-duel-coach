"""
Dataset Collector para Yu-Gi-Oh! Master Duel
Captura frames automáticamente mientras juegas para construir el dataset de entrenamiento YOLO11.

Uso:
    python master_duel/vision/dataset_collector.py

Controles:
    ESPACIO   — captura manual inmediata
    A         — modo auto (captura cada N segundos)
    Q         — salir
"""

import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("[WARN] mss no disponible. Instala: pip install mss")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("[WARN] opencv no disponible. Instala: pip install opencv-python")

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("[WARN] keyboard no disponible. Instala: pip install keyboard")


# ─── Configuración ────────────────────────────────────────────────────────────
DATASET_DIR = Path(__file__).resolve().parents[2] / "yolo_dataset" / "raw"
AUTO_INTERVAL_SEC = 2.0    # Captura automática cada N segundos
RESOLUTION = (1920, 1080)  # Resolución esperada (borderless 1080p)
MONITOR_INDEX = 1          # Monitor principal (1 = primero)
# ─────────────────────────────────────────────────────────────────────────────


class DatasetCollector:
    """Captura frames del juego para el dataset de entrenamiento YOLO11."""

    def __init__(self):
        self.dataset_dir = DATASET_DIR
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.count = self._count_existing()
        self.auto_mode = False
        self._stop = False
        self._lock = threading.Lock()
        self._sct: Optional[object] = None

        print(f"[DatasetCollector] Directorio: {self.dataset_dir}")
        print(f"[DatasetCollector] Imágenes existentes: {self.count}")

    def _count_existing(self) -> int:
        if not DATASET_DIR.exists():
            return 0
        return len(list(DATASET_DIR.glob("*.png")))

    def _init_mss(self):
        if MSS_AVAILABLE and self._sct is None:
            self._sct = mss.mss()

    def capture_frame(self) -> Optional[np.ndarray]:
        """Captura un frame de la pantalla completa."""
        if not MSS_AVAILABLE:
            return None
        try:
            self._init_mss()
            monitor = self._sct.monitors[MONITOR_INDEX]
            shot = self._sct.grab(monitor)
            frame = np.array(shot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            # Resize si no es 1080p
            if frame.shape[:2] != (RESOLUTION[1], RESOLUTION[0]):
                frame = cv2.resize(frame, RESOLUTION)
            return frame
        except Exception as e:
            print(f"[ERROR] Fallo captura: {e}")
            return None

    def save_frame(self, frame: np.ndarray) -> str:
        """Guarda el frame con timestamp y número de secuencia."""
        with self._lock:
            self.count += 1
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"frame_{self.count:05d}_{ts}.png"
            filepath = self.dataset_dir / filename
            cv2.imwrite(str(filepath), frame)
            return str(filepath)

    def capture_and_save(self, label: str = "auto") -> bool:
        """Captura y guarda un frame. Devuelve True si tuvo éxito."""
        frame = self.capture_frame()
        if frame is None:
            print("[ERROR] No se pudo capturar la pantalla.")
            return False
        path = self.save_frame(frame)
        print(f"[{label.upper()}] Guardado #{self.count}: {Path(path).name}")
        return True

    def _auto_capture_loop(self):
        """Loop de captura automática mientras self.auto_mode es True."""
        print(f"[AUTO] Captura automática cada {AUTO_INTERVAL_SEC}s. Pulsa 'A' para detener.")
        while self.auto_mode and not self._stop:
            self.capture_and_save("auto")
            time.sleep(AUTO_INTERVAL_SEC)
        print("[AUTO] Captura automática detenida.")

    def run_interactive(self):
        """Modo interactivo con hotkeys de teclado."""
        if not CV2_AVAILABLE:
            print("[ERROR] OpenCV es necesario para el modo interactivo.")
            return
        if not KEYBOARD_AVAILABLE:
            self._run_simple()
            return

        print("\n" + "=" * 60)
        print("  DATASET COLLECTOR - Master Duel YOLO11")
        print("=" * 60)
        print(f"  ESPACIO → Captura manual")
        print(f"  A       → Activar/Desactivar captura automática ({AUTO_INTERVAL_SEC}s)")
        print(f"  Q / ESC → Salir")
        print("=" * 60)
        print(f"  Guardando en: {self.dataset_dir}")
        print("=" * 60 + "\n")

        keyboard.add_hotkey("space", lambda: self.capture_and_save("manual"))
        keyboard.add_hotkey("a", self._toggle_auto)
        keyboard.add_hotkey("q", self._quit)
        keyboard.add_hotkey("esc", self._quit)

        print("[OK] Hotkeys registrados. El bot está listo.")
        print("     Pon el juego en primer plano y juega normalmente.\n")

        try:
            keyboard.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self._stop = True
            self.auto_mode = False
            print(f"\n[FIN] Total de frames capturados: {self.count}")
            print(f"      Directorio: {self.dataset_dir}")

    def _toggle_auto(self):
        if self.auto_mode:
            self.auto_mode = False
        else:
            self.auto_mode = True
            t = threading.Thread(target=self._auto_capture_loop, daemon=True)
            t.start()

    def _quit(self):
        self._stop = True
        self.auto_mode = False
        keyboard.unhook_all()

    def _run_simple(self):
        """Modo simple sin keyboard: captura continua hasta Ctrl+C."""
        print("\n[SIMPLE] Captura automática continua. Ctrl+C para parar.")
        print(f"         Intervalo: {AUTO_INTERVAL_SEC}s")
        try:
            while True:
                self.capture_and_save("auto")
                time.sleep(AUTO_INTERVAL_SEC)
        except KeyboardInterrupt:
            print(f"\n[FIN] Frames capturados: {self.count}")


def main():
    if not MSS_AVAILABLE:
        print("[ERROR FATAL] mss no está instalado.")
        print("  Ejecuta: pip install mss")
        sys.exit(1)
    if not CV2_AVAILABLE:
        print("[ERROR FATAL] opencv-python no está instalado.")
        print("  Ejecuta: pip install opencv-python")
        sys.exit(1)

    collector = DatasetCollector()
    collector.run_interactive()


if __name__ == "__main__":
    main()
