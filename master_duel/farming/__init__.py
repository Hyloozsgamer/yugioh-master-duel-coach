"""
Farming package for Yu-Gi-Oh! Master Duel AI.
"""
from .farming_strategy import FarmingStrategy, DuelTarget
from .solo_farming_engine import SoloFarmingEngine

__all__ = ["FarmingStrategy", "DuelTarget", "SoloFarmingEngine"]
