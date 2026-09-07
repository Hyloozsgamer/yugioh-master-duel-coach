"""
Card Recognizer Engine for Yu-Gi-Oh! Master Duel.
Identifies cards from hand, board, and inspector preview:
- Local database lookup by name / features.
- Confidence scoring.
- Protocol UNKNOWN_CARD if confidence is below safety threshold.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


@dataclass
class RecognizedCard:
    name: str
    card_id: Optional[str]
    card_type: str  # "MONSTER", "SPELL", "TRAP", "EXTRA"
    confidence: float
    atk: Optional[int] = None
    def_val: Optional[int] = None
    level_rank: Optional[int] = None
    is_known: bool = True
    screen_rect: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    @property
    def card_name(self) -> str:
        return self.name


class CardRecognizer:
    """Motor de reconocimiento visual y clasificación de cartas."""

    UNKNOWN_CARD = "UNKNOWN_CARD"

    def __init__(self, card_database=None):
        self.db = card_database

    def identify_card_from_crop(self, crop: np.ndarray, hint_name: Optional[str] = None) -> RecognizedCard:
        """
        Identifica una carta a partir de su recorte visual o pista de nombre.
        Si la confianza es baja, la etiqueta como UNKNOWN_CARD.
        """
        if crop is None or crop.size == 0:
            return RecognizedCard(self.UNKNOWN_CARD, None, "UNKNOWN", 0.0, is_known=False)

        # 1. Si tenemos una pista de nombre o texto detectado
        if hint_name and self.db:
            card_info = self.db.get_card(hint_name)
            if card_info:
                return RecognizedCard(
                    name=card_info.name,
                    card_id=card_info.card_id,
                    card_type=card_info.card_type,
                    confidence=0.96,
                    atk=card_info.atk,
                    def_val=card_info.def_val,
                    level_rank=card_info.level_rank,
                    is_known=True
                )

        # 2. Heurística visual por color de marco (Frame Type)
        # Naranja/Marrón = Monstruo Efecto
        # Amarillo = Monstruo Normal
        # Verde = Magia
        # Magenta/Rosa = Trampa
        # Azul = Enlace/Ritual
        # Blanco = Sincronía
        # Negro = XYZ
        card_type = self._detect_frame_color(crop)

        # Si no encontramos correspondencia segura
        return RecognizedCard(
            name=hint_name or self.UNKNOWN_CARD,
            card_id=None,
            card_type=card_type,
            confidence=0.70 if hint_name else 0.40,
            is_known=bool(hint_name)
        )

    def _detect_frame_color(self, crop: np.ndarray) -> str:
        """Detecta el tipo de carta según el tono y saturación del marco."""
        if crop is None or crop.size == 0:
            return "UNKNOWN"

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        h = hsv[:, :, 0]
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]
        total_pixels = float(h.size)

        # 1. Verde (Magia): Hue 35-85, saturación media/alta
        green_mask = (h >= 35) & (h <= 85) & (s >= 50) & (v >= 50)
        if np.count_nonzero(green_mask) / total_pixels > 0.15:
            return "SPELL"

        # 2. Rosa / Magenta (Trampa): Hue 140-175, saturación media/alta
        pink_mask = (h >= 140) & (h <= 175) & (s >= 45) & (v >= 50)
        if np.count_nonzero(pink_mask) / total_pixels > 0.12:
            return "TRAP"

        # 3. Morado / Violeta (Monstruo Fusión): Hue 125-142
        purple_mask = (h >= 125) & (h <= 142) & (s >= 40) & (v >= 50)
        if np.count_nonzero(purple_mask) / total_pixels > 0.12:
            return "MONSTER_FUSION"

        # 4. Azul Oscuro / Hexagonal (Monstruo Enlace / Ritual): Hue 95-125
        blue_mask = (h >= 95) & (h <= 125) & (s >= 60) & (v >= 50)
        if np.count_nonzero(blue_mask) / total_pixels > 0.12:
            return "MONSTER_LINK"

        # 5. Negro / Carbón (Monstruo XYZ): Muy bajo brillo
        black_mask = (v < 55)
        if np.count_nonzero(black_mask) / total_pixels > 0.35:
            return "MONSTER_XYZ"

        # 6. Blanco / Plateado (Monstruo Sincronía): Muy baja saturación, alto brillo
        white_mask = (s < 40) & (v > 175)
        if np.count_nonzero(white_mask) / total_pixels > 0.25:
            return "MONSTER_SYNCHRO"

        # 7. Amarillo / Dorado (Monstruo Normal): Hue 20-35, saturación alta
        yellow_mask = (h >= 20) & (h <= 35) & (s >= 70) & (v >= 70)
        if np.count_nonzero(yellow_mask) / total_pixels > 0.15:
            return "MONSTER_NORMAL"

        # 8. Marrón / Naranja (Monstruo Efecto): Hue 8-22, saturación media/alta
        orange_mask = (h >= 8) & (h <= 22) & (s >= 60) & (v >= 60)
        if np.count_nonzero(orange_mask) / total_pixels > 0.15:
            return "MONSTER_EFFECT"

        # Fallback general de monstruo
        if np.count_nonzero((h >= 8) & (h <= 35)) / total_pixels > 0.12:
            return "MONSTER"

        return "UNKNOWN"

    @staticmethod
    def is_monster(card_type: str) -> bool:
        """Determina si un tipo clasificado corresponde a un monstruo."""
        ct = card_type.upper()
        return "MONSTER" in ct or ct in ("MONSTER_NORMAL", "MONSTER_EFFECT", "MONSTER_FUSION", "MONSTER_SYNCHRO", "MONSTER_XYZ", "MONSTER_LINK")

    @staticmethod
    def is_spell(card_type: str) -> bool:
        """Determina si un tipo clasificado corresponde a una magia."""
        return "SPELL" in card_type.upper()

    @staticmethod
    def is_trap(card_type: str) -> bool:
        """Determina si un tipo clasificado corresponde a una trampa."""
        return "TRAP" in card_type.upper()

    def classify_card(self, crop: np.ndarray, hint_name: Optional[str] = None) -> RecognizedCard:
        """Alias for identify_card_from_crop."""
        return self.identify_card_from_crop(crop, hint_name=hint_name)

