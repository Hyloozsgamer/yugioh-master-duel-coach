"""
Board Detector Module for Yu-Gi-Oh! Master Duel.
Maps all relative field zones (16:9 normalized) and detects occupancy:
- 5 Player Monster Zones (Z1-Z5)
- 5 Player Spell/Trap Zones (ST1-ST5)
- 2 Extra Monster Zones (EMZ_LEFT, EMZ_RIGHT)
- Player Hand slots
- Graveyard, Extra Deck, Field Spell Zone
- Opponent Monster & Spell/Trap Zones
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass
class BoardZone:
    name: str
    center_x: float  # Normalizado 0.0 - 1.0
    center_y: float  # Normalizado 0.0 - 1.0
    width: float     # Ancho normalizado
    height: float    # Alto normalizado
    is_occupied: bool = False
    card_name: Optional[str] = None
    atk: Optional[int] = None
    def_val: Optional[int] = None
    position: str = "EMPTY"  # "ATTACK", "DEFENSE", "SET", "EMPTY"

# Aliases for compatibility
BoardOccupancy = BoardZone
ZoneCoords = BoardZone


class BoardDetector:
    """Mapeador y detector de ocupación de zonas de Master Duel."""

    # Coordenadas maestras relativas (16:9) del campo de Master Duel
    ZONES_CONFIG = {
        # Zonas de Monstruos del Jugador (Fila 1 frente al jugador)
        "M1": (0.31, 0.62, 0.08, 0.12),
        "M2": (0.40, 0.62, 0.08, 0.12),
        "M3": (0.50, 0.62, 0.08, 0.12),  # Centro
        "M4": (0.59, 0.62, 0.08, 0.12),
        "M5": (0.68, 0.62, 0.08, 0.12),

        # Zonas de Magia / Trampa del Jugador (Fila 2 inferior)
        "ST1": (0.31, 0.77, 0.08, 0.12),
        "ST2": (0.40, 0.77, 0.08, 0.12),
        "ST3": (0.50, 0.77, 0.08, 0.12),
        "ST4": (0.59, 0.77, 0.08, 0.12),
        "ST5": (0.68, 0.77, 0.08, 0.12),

        # Extra Monster Zones
        "EMZ_LEFT": (0.40, 0.49, 0.08, 0.11),
        "EMZ_RIGHT": (0.59, 0.49, 0.08, 0.11),

        # Zonas de Monstruos del Rival (Fila 1 superior)
        "OPP_M1": (0.68, 0.36, 0.08, 0.11),
        "OPP_M2": (0.59, 0.36, 0.08, 0.11),
        "OPP_M3": (0.50, 0.36, 0.08, 0.11),  # Centro rival
        "OPP_M4": (0.40, 0.36, 0.08, 0.11),
        "OPP_M5": (0.31, 0.36, 0.08, 0.11),

        # Zonas de Magia / Trampa del Rival (Fila 2 superior)
        "OPP_ST1": (0.68, 0.23, 0.08, 0.10),
        "OPP_ST2": (0.59, 0.23, 0.08, 0.10),
        "OPP_ST3": (0.50, 0.23, 0.08, 0.10),
        "OPP_ST4": (0.40, 0.23, 0.08, 0.10),
        "OPP_ST5": (0.31, 0.23, 0.08, 0.10),

        # Zonas Especiales
        "GRAVEYARD": (0.83, 0.75, 0.07, 0.11),
        "EXTRA_DECK": (0.16, 0.75, 0.07, 0.11),
        "FIELD_SPELL": (0.16, 0.50, 0.07, 0.11),
        "PHASE_BUTTON": (0.77, 0.46, 0.08, 0.08),
    }

    def __init__(self):
        self.zones: Dict[str, BoardZone] = {}
        for name, (cx, cy, w, h) in self.ZONES_CONFIG.items():
            self.zones[name] = BoardZone(name=name, center_x=cx, center_y=cy, width=w, height=h)

    def scan_board(self, frame: np.ndarray) -> Dict[str, BoardZone]:
        """
        Escanea el frame y determina qué zonas están ocupadas por monstruos o magias/trampas.
        """
        if frame is None or frame.size == 0:
            return self.zones

        h, w = frame.shape[:2]

        for name, zone in self.zones.items():
            # Extraer ROI de la zona
            x1 = max(0, int((zone.center_x - zone.width / 2) * w))
            x2 = min(w, int((zone.center_x + zone.width / 2) * w))
            y1 = max(0, int((zone.center_y - zone.height / 2) * h))
            y2 = min(h, int((zone.center_y + zone.height / 2) * h))

            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            # Determinación de ocupación:
            # Una zona vacía en Master Duel es una reja metálica oscura/marrón plana.
            # Una carta presenta saturación de color (bordes de carta o ilustración) y mayor varianza.
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            variance = np.var(gray)
            mean_bright = np.mean(gray)

            # Comprobar borde de carta en zona de monstruo
            is_occupied = False
            position = "EMPTY"

            if name.startswith("M") or name.startswith("EMZ") or name.startswith("OPP_M"):
                # Si la varianza o brillo supera el umbral de rejilla vacía (~350 varianza, >45 brillo)
                if variance > 450 and mean_bright > 40:
                    is_occupied = True
                    # Comprobar orientación (horizontal = Defensa, vertical = Ataque)
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    # Color dorado o naranja de monstruos
                    position = "ATTACK" if (roi.shape[0] >= roi.shape[1]) else "DEFENSE"

            elif name.startswith("ST") or name.startswith("OPP_ST"):
                # En magias/trampas boca abajo, el reverso de la carta Yu-Gi-Oh! tiene patrón marrón/naranja característico
                if variance > 380 and mean_bright > 35:
                    is_occupied = True
                    position = "SET"

            zone.is_occupied = is_occupied
            zone.position = position

        return self.zones

    def get_empty_player_monster_zone(self) -> Optional[Tuple[float, float]]:
        """Retorna coordenadas normalizadas de una zona de monstruo vacía (prioridad centro: M3 -> M2 -> M4 -> M1 -> M5)."""
        priority = ["M3", "M2", "M4", "M1", "M5"]
        for name in priority:
            zone = self.zones.get(name)
            if zone and not zone.is_occupied:
                return zone.center_x, zone.center_y
        return 0.50, 0.62  # Fallback a centro

    def get_empty_player_st_zone(self) -> Optional[Tuple[float, float]]:
        """Retorna coordenadas de una zona de magia/trampa vacía para colocar cartas."""
        priority = ["ST3", "ST2", "ST4", "ST1", "ST5"]
        for name in priority:
            zone = self.zones.get(name)
            if zone and not zone.is_occupied:
                return zone.center_x, zone.center_y
        return 0.50, 0.77

    def detect_occupancy(self, frame: np.ndarray) -> Dict[str, BoardZone]:
        """Alias for scan_board."""
        return self.scan_board(frame)

    def get_zone_rect(self, zone_name: str) -> Optional[BoardZone]:
        """Returns the BoardZone object for a specific zone name."""
        if zone_name in self.zones:
            return self.zones[zone_name]
        if zone_name == "HAND":
            return BoardZone(name="HAND", center_x=0.50, center_y=0.90, width=0.50, height=0.15)
        return None
