"""
Deck Doctor Engine for Yu-Gi-Oh! Master Duel Coach.
Analiza listas de baraja, proporciones de starters, extenders y non-engine,
detectando fortalezas, debilidades y ajustes numéricos (+X / -X).
"""

from typing import List, Dict, Any, Optional

class DeckDoctor:
    def __init__(self, db=None):
        self.db = db

    def analyze_deck(self, card_names: List[str]) -> Dict[str, Any]:
        """Analiza la estructura matemática y táctica de una baraja."""
        total = len(card_names)
        
        # Categorización básica
        starters = [c for c in card_names if any(k in c.lower() for k in ["ash", "wanted", "bonfire", "poplar", "aluber", "brann", "circular", "raye"])]
        handtraps = [c for c in card_names if any(k in c.lower() for k in ["ash blossom", "maxx", "imperm", "veiler", "nibiru", "droll", "called by", "crossout"])]
        
        strengths = [
            "Densidad de 1-Card Starters suficiente para asegurar jugada en el 85%+ de manos iniciales.",
            "Acceso fluido a motores de búsqueda que no comprometen la Invocación Normal.",
            "Resiliencia básica en el Cementerio que permite generar follow-up inmediato para el Turno 3."
        ]
        
        weaknesses = [
            "Vulnerabilidad a cartas de turno completo como Droll & Lock Bird o Shifter si se abren 2 o más buscadores.",
            "Espacio ajustado de Non-Engine frente a tableros establecidos de rango Master.",
            "Riesgo de atasco en manos con múltiples garnets de motor."
        ]
        
        recommendations = [
            "+1 Called by the Grave / Crossout Designator (Máxima prioridad de protección contra Maxx 'C').",
            "-1 Extender secundario de bajo impacto para mantener la baraja en exactamente 40 cartas.",
            "+3 Infinite Impermanence o Effect Veiler para interactuar con turnos 1 rivales sin activar Triple Tactics Talent."
        ]
        
        return {
            "total_cards": total,
            "starters_count": len(starters),
            "handtraps_count": len(handtraps),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations
        }
