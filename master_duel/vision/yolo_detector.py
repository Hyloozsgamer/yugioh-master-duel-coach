"""
YOLO11 Detector para Yu-Gi-Oh! Master Duel.
Wrapper de inferencia en tiempo real sobre el modelo entrenado.

Detecta: cartas, botones, zonas, fases, diálogos.
Resolución objetivo: 1920x1080 (borderless windowed).
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import numpy as np

# ─── Clases del modelo (deben coincidir con dataset.yaml) ─────────────────────
CLASS_NAMES = {
    0:  "card_hand",          # Carta en mano del jugador
    1:  "card_field_player",  # Carta del jugador en campo
    2:  "card_field_opp",     # Carta rival en campo
    3:  "zone_monster_free",  # Zona de monstruo vacía
    4:  "zone_spell_free",    # Zona de magia/trampa vacía
    5:  "btn_ok",             # Botón OK / Confirmar
    6:  "btn_effect",         # Botón Activar Efecto
    7:  "btn_skip",           # Botón Cancelar / Saltar
    8:  "btn_attack",         # Botón Atacar
    9:  "btn_end_phase",      # Botón Terminar Fase
    10: "dialog_popup",       # Ventana emergente genérica
    11: "phase_main",         # Indicador Main Phase
    12: "phase_battle",       # Indicador Battle Phase
    13: "phase_end",          # Indicador End Phase
    14: "lp_player",          # Puntos de vida del jugador
    15: "lp_opponent",        # Puntos de vida del rival
}

# Grupos de clases por tipo
BUTTON_CLASSES    = {"btn_ok", "btn_effect", "btn_skip", "btn_attack", "btn_end_phase"}
CARD_CLASSES      = {"card_hand", "card_field_player", "card_field_opp"}
ZONE_CLASSES      = {"zone_monster_free", "zone_spell_free"}
PHASE_CLASSES     = {"phase_main", "phase_battle", "phase_end"}
DIALOG_CLASSES    = {"dialog_popup"}
LP_CLASSES        = {"lp_player", "lp_opponent"}

# Modelo por defecto (se entrena en FASE 3)
DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "yolo_runs" / "masterduel_v1" / "weights" / "best.pt"
PRETRAINED_NANO   = "yolo11n.pt"  # Fallback pre-entrenado (sin clases de MD)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Detection:
    """Una detección individual de YOLO11."""
    class_id: int
    class_name: str
    confidence: float
    x1: int  # píxeles absolutos
    y1: int
    x2: int
    y2: int

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def center_norm(self) -> Tuple[float, float]:
        """Centro normalizado 0.0–1.0 para 1920x1080."""
        cx, cy = self.center
        return (cx / 1920.0, cy / 1080.0)

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height

    def is_type(self, class_name: str) -> bool:
        return self.class_name == class_name

    def is_button(self) -> bool:
        return self.class_name in BUTTON_CLASSES

    def is_card(self) -> bool:
        return self.class_name in CARD_CLASSES

    def __repr__(self):
        cx, cy = self.center
        return f"Detection({self.class_name} {self.confidence:.2f} @ ({cx},{cy}))"


@dataclass
class YOLOFrame:
    """Resultado de una inferencia YOLO sobre un frame completo."""
    detections: List[Detection] = field(default_factory=list)
    inference_ms: float = 0.0
    frame_shape: Tuple[int, int] = (1080, 1920)
    timestamp: float = field(default_factory=time.time)

    # ─── Filtros de conveniencia ──────────────────────────────────────────────

    def by_class(self, class_name: str) -> List[Detection]:
        return [d for d in self.detections if d.class_name == class_name]

    def buttons(self) -> List[Detection]:
        return [d for d in self.detections if d.is_button()]

    def cards_in_hand(self) -> List[Detection]:
        return self.by_class("card_hand")

    def cards_player_field(self) -> List[Detection]:
        return self.by_class("card_field_player")

    def cards_opp_field(self) -> List[Detection]:
        return self.by_class("card_field_opp")

    def free_monster_zones(self) -> List[Detection]:
        return self.by_class("zone_monster_free")

    def free_spell_zones(self) -> List[Detection]:
        return self.by_class("zone_spell_free")

    def dialogs(self) -> List[Detection]:
        return self.by_class("dialog_popup")

    def has_dialog(self) -> bool:
        return len(self.dialogs()) > 0

    def has_button(self, btn: str) -> bool:
        return any(d.class_name == btn for d in self.detections)

    def best_button(self) -> Optional[Detection]:
        """Devuelve el botón con mayor confianza."""
        btns = self.buttons()
        if not btns:
            return None
        return max(btns, key=lambda d: d.confidence)

    def current_phase(self) -> Optional[str]:
        """Devuelve la fase actual detectada."""
        for cls in ["phase_main", "phase_battle", "phase_end"]:
            hits = self.by_class(cls)
            if hits:
                return cls
        return None

    def summary(self) -> str:
        phase = self.current_phase() or "unknown"
        dialogs = len(self.dialogs())
        btns = [d.class_name for d in self.buttons()]
        hand = len(self.cards_in_hand())
        field = len(self.cards_player_field())
        return (
            f"Phase={phase} | Dialogs={dialogs} | Buttons={btns} | "
            f"Hand={hand} | Field={field} | {self.inference_ms:.1f}ms"
        )


class YOLODetector:
    """
    Detector YOLO11 en tiempo real para Master Duel.

    Uso:
        detector = YOLODetector()
        frame_np = capture_screen()  # numpy array BGR
        result = detector.detect(frame_np)
        for det in result.buttons():
            print(f"Botón: {det.class_name} @ {det.center}")
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence: float = 0.45,
        iou: float = 0.4,
        device: str = "auto",
    ):
        self.confidence = confidence
        self.iou = iou
        self.model = None
        self.model_path = None
        self._loaded = False
        self._inference_count = 0

        # Selección de device
        if device == "auto":
            try:
                import torch
                self.device = "0" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device

        # Selección de modelo
        if model_path:
            self.model_path = Path(model_path)
        elif DEFAULT_MODEL_PATH.exists():
            self.model_path = DEFAULT_MODEL_PATH
            print(f"[YOLODetector] Modelo entrenado encontrado: {self.model_path}")
        else:
            # Usar modelo nano pre-entrenado (sólo detección genérica hasta entrenar)
            self.model_path = PRETRAINED_NANO
            print(f"[YOLODetector] AVISO: No hay modelo entrenado.")
            print(f"               Usando {PRETRAINED_NANO} (pre-entrenado COCO, sin clases de MD).")
            print(f"               Ejecuta ENTRENAR_YOLO.bat para entrenar el modelo personalizado.")

        self._load_model()

    def _load_model(self):
        """Carga el modelo YOLO11."""
        try:
            from ultralytics import YOLO
            print(f"[YOLODetector] Cargando modelo: {self.model_path} en {self.device}...")
            t0 = time.time()
            self.model = YOLO(str(self.model_path))
            elapsed = (time.time() - t0) * 1000
            self._loaded = True
            print(f"[YOLODetector] ✓ Modelo cargado en {elapsed:.0f}ms")
        except ImportError:
            print("[YOLODetector] ERROR: ultralytics no instalado.")
            print("               Ejecuta: pip install ultralytics")
        except Exception as e:
            print(f"[YOLODetector] ERROR al cargar modelo: {e}")

    @property
    def is_ready(self) -> bool:
        return self._loaded and self.model is not None

    def detect(self, frame: np.ndarray) -> YOLOFrame:
        """
        Ejecuta inferencia YOLO11 sobre un frame.

        Args:
            frame: numpy array BGR (1920x1080 recomendado)

        Returns:
            YOLOFrame con todas las detecciones
        """
        if not self.is_ready:
            return YOLOFrame()

        t0 = time.perf_counter()
        try:
            results = self.model.predict(
                source=frame,
                conf=self.confidence,
                iou=self.iou,
                device=self.device,
                verbose=False,
                stream=False,
            )
        except Exception as e:
            print(f"[YOLODetector] Error en inferencia: {e}")
            return YOLOFrame()

        elapsed_ms = (time.perf_counter() - t0) * 1000
        self._inference_count += 1

        detections: List[Detection] = []
        for r in results:
            if r.boxes is None:
                continue
            boxes = r.boxes
            for i in range(len(boxes)):
                cls_id  = int(boxes.cls[i].item())
                conf    = float(boxes.conf[i].item())
                xyxy    = boxes.xyxy[i].tolist()
                x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])

                # Mapear class_id al nombre de nuestras clases
                class_name = CLASS_NAMES.get(cls_id, f"unknown_{cls_id}")

                detections.append(Detection(
                    class_id=cls_id,
                    class_name=class_name,
                    confidence=conf,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                ))

        h, w = frame.shape[:2]
        return YOLOFrame(
            detections=detections,
            inference_ms=elapsed_ms,
            frame_shape=(h, w),
        )

    def detect_realtime(self, frame: np.ndarray, min_conf: float = 0.5) -> YOLOFrame:
        """Inferencia optimizada para tiempo real (filtra baja confianza)."""
        old_conf = self.confidence
        self.confidence = min_conf
        result = self.detect(frame)
        self.confidence = old_conf
        return result

    def stats(self) -> Dict:
        return {
            "model": str(self.model_path),
            "device": self.device,
            "loaded": self._loaded,
            "inferences": self._inference_count,
            "confidence": self.confidence,
        }
