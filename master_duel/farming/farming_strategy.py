"""
Solo Farming Strategy Evaluator for Yu-Gi-Oh! Master Duel AI.
Calculates farming efficiency: (Reward / Minute) * Win_Probability * Reliability.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class DuelTarget:
    gate_name: str
    chapter_name: str
    estimated_time_min: float
    win_rate: float
    reward_score: float  # Gems, tickets, or legacy pack value
    deck_type: str = "MY_DECK"  # or "LOANER"
    completed: bool = False

    @property
    def efficiency_score(self) -> float:
        """
        Calculates efficiency metric: (Reward / Time) * WinRate
        """
        if self.estimated_time_min <= 0:
            return 0.0
        return (self.reward_score / self.estimated_time_min) * self.win_rate

class FarmingStrategy:
    def __init__(self):
        # Known fast farming gates in Solo Mode (e.g. Tutorial Duel Strategy, SP Deck Challenge, etc.)
        self.targets: List[DuelTarget] = [
            DuelTarget(
                gate_name="Duel Strategy",
                chapter_name="Practice 1",
                estimated_time_min=1.5,
                win_rate=0.99,
                reward_score=100.0,
                deck_type="LOANER"
            ),
            DuelTarget(
                gate_name="Duel Strategy 2",
                chapter_name="Summoning Mechanics",
                estimated_time_min=2.0,
                win_rate=0.98,
                reward_score=150.0,
                deck_type="LOANER"
            ),
            DuelTarget(
                gate_name="Gladiator Beasts",
                chapter_name="Chapter 1",
                estimated_time_min=2.5,
                win_rate=0.95,
                reward_score=120.0,
                deck_type="MY_DECK"
            )
        ]

    def select_best_target(self) -> DuelTarget:
        """
        Selects highest efficiency uncompleted or repeatable duel target.
        """
        active_targets = [t for t in self.targets if not t.completed]
        if not active_targets:
            # All completed, pick fastest repeatable target
            return max(self.targets, key=lambda t: t.efficiency_score)
        return max(active_targets, key=lambda t: t.efficiency_score)
