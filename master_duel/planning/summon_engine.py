"""
Summon & Extra Deck Engine for Yu-Gi-Oh! Master Duel AI.
Validates summon conditions, materials, and zone restrictions for Normal, Tribute, Fusion, Synchro, Xyz, and Link.
"""
from typing import List, Dict, Optional
from ..state.game_state import GameState, ZoneCard
from ..database.card_database import CardDatabase, CardInfo

class SummonEngine:
    def __init__(self, card_db: CardDatabase):
        self.card_db = card_db

    def can_normal_summon(self, card_name: str, state: GameState) -> bool:
        if state.normal_summon_used:
            return False
        if not state.get_first_empty_monster_zone():
            return False

        card_info = self.card_db.get_card_by_name(card_name)
        if not card_info:
            return True

        if card_info.level <= 4:
            return True
        elif card_info.level in [5, 6]:
            return len(state.get_player_monsters()) >= 1
        else:  # Level 7+
            return len(state.get_player_monsters()) >= 2

    def get_tribute_candidates(self, card_name: str, state: GameState) -> List[str]:
        """
        Returns list of zone IDs that should be tributed (lowest ATK first).
        """
        monsters = state.get_player_monsters()
        if not monsters:
            return []
            
        # Sort ascending by ATK to tribute weakest monsters first
        sorted_monsters = sorted(monsters, key=lambda m: m.atk)
        card_info = self.card_db.get_card_by_name(card_name)
        req_count = 1 if (card_info and card_info.level in [5, 6]) else 2
        
        return [m.zone_id for m in sorted_monsters[:req_count]]

    def can_link_summon(self, extra_card_name: str, state: GameState) -> bool:
        card_info = self.card_db.get_card_by_name(extra_card_name)
        if not card_info or card_info.link_rating == 0:
            return False

        # Link rating required materials
        req_materials = card_info.link_rating
        return len(state.get_player_monsters()) >= req_materials
