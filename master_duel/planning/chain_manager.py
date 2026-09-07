"""
Chain Manager for Yu-Gi-Oh! Master Duel AI.
Evaluates chain links and decides whether to ACTIVATE or PASS on prompts.
"""
from typing import Dict, Any, Optional
from ..database.card_database import CardDatabase
from ..state.game_state import GameState

class ChainManager:
    def __init__(self, card_db: CardDatabase):
        self.card_db = card_db

    def should_activate_in_chain(
        self,
        prompt_card_name: str,
        state: GameState,
        triggering_event: Optional[str] = None
    ) -> bool:
        """
        Determines whether the bot should activate an effect on a prompt or decline/pass.
        Returns: True (Activate/Yes), False (Pass/No)
        """
        card_info = self.card_db.get_card_by_name(prompt_card_name)
        if not card_info:
            # If completely unknown, default to safe activation if it's player's turn,
            # or pass if opponent is acting and we aren't sure
            return state.is_player_turn

        # Check if already used Once Per Turn
        if card_info.once_per_turn and prompt_card_name in state.activated_effects_opt:
            return False

        # If it's a searcher or starter on player's turn, always activate
        if state.is_player_turn and ("searcher" in card_info.roles or "starter" in card_info.roles):
            return True

        # If it's a negate (e.g. Ash Blossom, Solemn Judgment, Impermanence)
        if "negate" in card_info.roles:
            # Only negate if opponent is performing an impactful action
            if not state.is_player_turn:
                return True
            return False

        # If it's removal (e.g. Raigeki Break, destruction effect)
        if "removal" in card_info.roles:
            # Activate if opponent has monsters on the field
            return len(state.get_opponent_monsters()) > 0

        # General rule: If it gives free advantage or extends board, activate
        if "extender" in card_info.roles:
            return True

        return True
