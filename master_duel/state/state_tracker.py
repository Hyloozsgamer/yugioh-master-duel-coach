"""
State Tracker for Yu-Gi-Oh! Master Duel AI.
Integrates vision detections into the reactive GameState and tracks diffs across turns and actions.
"""
import copy
from typing import Dict, Any, Optional, List
from .game_state import GameState, ZoneCard, DuelPhase, CardPosition
from ..vision.board_detector import BoardOccupancy, ZoneCoords
from ..database.card_database import CardDatabase

class StateTracker:
    def __init__(self, card_db: Optional[CardDatabase] = None):
        self.card_db = card_db or CardDatabase()
        self.current_state = GameState()
        self.previous_state: Optional[GameState] = None
        self.state_history: List[GameState] = []

    def update_from_vision(
        self,
        board_occupancy: Dict[str, BoardOccupancy],
        ui_info: Dict[str, Any],
        hand_cards: Optional[List[str]] = None,
        confidence: float = 1.0
    ) -> GameState:
        """
        Updates the current GameState using live board vision and UI recognizer data.
        """
        # Save snapshot
        self.previous_state = copy.deepcopy(self.current_state)
        
        # 1. Update Phase and Turn Status
        phase_str = ui_info.get("phase", "").upper()
        if "MAIN 1" in phase_str or phase_str == "MAIN1":
            self.current_state.phase = DuelPhase.MAIN1
            self.current_state.is_player_turn = True
        elif "BATTLE" in phase_str:
            self.current_state.phase = DuelPhase.BATTLE
            self.current_state.is_player_turn = True
        elif "MAIN 2" in phase_str or phase_str == "MAIN2":
            self.current_state.phase = DuelPhase.MAIN2
            self.current_state.is_player_turn = True
        elif "END" in phase_str:
            self.current_state.phase = DuelPhase.END
            self.current_state.is_player_turn = True
        elif ui_info.get("is_opponent_turn", False):
            self.current_state.phase = DuelPhase.OPPONENT
            self.current_state.is_player_turn = False
            
        # Detect turn increment
        if self.previous_state and self.previous_state.phase != DuelPhase.MAIN1 and self.current_state.phase == DuelPhase.MAIN1:
            self.current_state.turn += 1
            self.current_state.normal_summon_used = False
            self.current_state.activated_effects_opt.clear()
            self.current_state.special_summons_this_turn = 0
            for m in self.current_state.monster_zones.values():
                if m:
                    m.can_attack = True
                    m.has_activated_effect_this_turn = False

        # 2. Update Monster & Spell Zones Occupancy
        for zone_name, occ in board_occupancy.items():
            is_occupied = occ.is_occupied
            
            # Player Monster Zones
            if zone_name in self.current_state.monster_zones:
                if not is_occupied:
                    self.current_state.monster_zones[zone_name] = None
                else:
                    existing = self.current_state.monster_zones.get(zone_name)
                    if existing is None:
                        # Newly placed monster
                        self.current_state.monster_zones[zone_name] = ZoneCard(
                            zone_id=zone_name,
                            card_name="UNKNOWN_MONSTER",
                            position=CardPosition.FACEUP_ATTACK,
                            atk=1000  # Default safe placeholder until identified
                        )
            
            # Opponent Monster Zones
            elif zone_name in self.current_state.opp_monster_zones:
                if not is_occupied:
                    self.current_state.opp_monster_zones[zone_name] = None
                else:
                    existing = self.current_state.opp_monster_zones.get(zone_name)
                    if existing is None:
                        self.current_state.opp_monster_zones[zone_name] = ZoneCard(
                            zone_id=zone_name,
                            card_name="OPPONENT_MONSTER",
                            position=CardPosition.FACEUP_ATTACK,
                            atk=1500
                        )

            # Player Spell/Trap Zones
            elif zone_name in self.current_state.spell_trap_zones:
                if not is_occupied:
                    self.current_state.spell_trap_zones[zone_name] = None
                else:
                    if self.current_state.spell_trap_zones.get(zone_name) is None:
                        self.current_state.spell_trap_zones[zone_name] = ZoneCard(
                            zone_id=zone_name,
                            card_name="SET_SPELL_TRAP",
                            position=CardPosition.FACEDOWN_SET
                        )

            # Opponent Spell/Trap Zones
            elif zone_name in self.current_state.opp_spell_trap_zones:
                if not is_occupied:
                    self.current_state.opp_spell_trap_zones[zone_name] = None
                else:
                    if self.current_state.opp_spell_trap_zones.get(zone_name) is None:
                        self.current_state.opp_spell_trap_zones[zone_name] = ZoneCard(
                            zone_id=zone_name,
                            card_name="OPP_SET_CARD",
                            position=CardPosition.FACEDOWN_SET
                        )

        # 3. Update Hand
        if hand_cards is not None:
            self.current_state.hand = hand_cards
            self.current_state.hand_count = len(hand_cards)

        # 4. Chain state
        if ui_info.get("prompt_type") == "chain" or ui_info.get("has_activate_prompt", False):
            self.current_state.is_chain_active = True
        else:
            self.current_state.is_chain_active = False

        self.current_state.confidence = confidence
        self.state_history.append(copy.deepcopy(self.current_state))
        if len(self.state_history) > 50:
            self.state_history.pop(0)

        return self.current_state

    def record_action_executed(self, action_type: str, details: Dict[str, Any]):
        """
        Anticipates immediate state changes when an action is executed.
        """
        if action_type == "NORMAL_SUMMON":
            self.current_state.normal_summon_used = True
            card_name = details.get("card_name", "UNKNOWN_CARD")
            target_zone = details.get("zone", self.current_state.get_first_empty_monster_zone() or "M3")
            
            card_data = self.card_db.get_card_by_name(card_name)
            atk = card_data.atk if card_data else 1500
            def_stat = card_data.def_stat if card_data else 1000
            
            self.current_state.monster_zones[target_zone] = ZoneCard(
                zone_id=target_zone,
                card_name=card_name,
                atk=atk,
                def_stat=def_stat,
                position=CardPosition.FACEUP_ATTACK
            )
            if card_name in self.current_state.hand:
                self.current_state.hand.remove(card_name)
                
            self.current_state.last_action_desc = f"Normal Summon {card_name} -> {target_zone}"

        elif action_type == "SET_SPELL_TRAP":
            card_name = details.get("card_name", "UNKNOWN_CARD")
            target_zone = details.get("zone", self.current_state.get_first_empty_st_zone() or "ST3")
            self.current_state.spell_trap_zones[target_zone] = ZoneCard(
                zone_id=target_zone,
                card_name=card_name,
                position=CardPosition.FACEDOWN_SET
            )
            if card_name in self.current_state.hand:
                self.current_state.hand.remove(card_name)
            self.current_state.last_action_desc = f"Set {card_name} -> {target_zone}"

        elif action_type == "ACTIVATE_EFFECT":
            card_name = details.get("card_name", "EFFECT")
            self.current_state.activated_effects_opt.append(card_name)
            self.current_state.last_action_desc = f"Activate {card_name}"

        elif action_type == "ATTACK":
            attacker = details.get("attacker_zone")
            if attacker and attacker in self.current_state.monster_zones:
                mon = self.current_state.monster_zones[attacker]
                if mon:
                    mon.can_attack = False
            self.current_state.last_action_desc = f"Attack with {attacker} -> {details.get('target', 'DIRECT')}"
