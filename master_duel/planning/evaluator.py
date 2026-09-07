"""
State Evaluator for Yu-Gi-Oh! Master Duel AI.
Computes comprehensive tactical scores based on board presence, card advantage, LP delta, and threats.
"""
from typing import Dict, Any
from ..state.game_state import GameState, CardPosition
from ..database.card_database import CardDatabase

class StateEvaluator:
    def __init__(self, card_db: CardDatabase):
        self.card_db = card_db

    def evaluate(self, state: GameState) -> float:
        """
        Calculates holistic heuristic score for a GameState. Higher is better for Player.
        """
        # 1. Terminal / Win Conditions
        if state.opponent_lp <= 0:
            return 100000.0  # Immediate Victory
        if state.player_lp <= 0:
            return -100000.0  # Loss

        score = 0.0

        # 2. Life Points Differential (scaled)
        lp_diff = (state.player_lp - state.opponent_lp) / 100.0
        score += lp_diff * 0.5

        # 3. Card Advantage (Hand + Field)
        player_monsters = state.get_player_monsters()
        opp_monsters = state.get_opponent_monsters()
        player_st = [s for s in state.spell_trap_zones.values() if s is not None]
        opp_st = [s for s in state.opp_spell_trap_zones.values() if s is not None]

        player_total_cards = len(state.hand) + len(player_monsters) + len(player_st)
        opp_total_cards = state.opp_hand_count + len(opp_monsters) + len(opp_st)
        
        card_advantage = player_total_cards - opp_total_cards
        score += card_advantage * 150.0

        # 4. Board Presence & ATK Superiority
        player_total_atk = sum(m.atk for m in player_monsters if m.position == CardPosition.FACEUP_ATTACK)
        opp_total_atk = sum(m.atk for m in opp_monsters if m.position == CardPosition.FACEUP_ATTACK)

        score += (player_total_atk - opp_total_atk) * 0.2

        # 5. Monster Control Differential
        monster_diff = len(player_monsters) - len(opp_monsters)
        score += monster_diff * 100.0

        # 6. Threat Analysis: Can Opponent Kill us next turn?
        if opp_total_atk >= state.player_lp and len(player_monsters) == 0:
            score -= 1500.0  # Critical threat: Lethal on empty board!

        # 7. Quality of Monsters on Board (Boss monsters bonus)
        for m in player_monsters:
            info = self.card_db.get_card_by_name(m.card_name)
            if info:
                if "boss" in info.roles:
                    score += 250.0
                if info.atk >= 2400:
                    score += 150.0

        return score
