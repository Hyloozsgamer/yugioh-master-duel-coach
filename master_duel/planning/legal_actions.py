"""
Legal Action Generator for Yu-Gi-Oh! Master Duel AI.
Discovers valid tactical actions given the current GameState and Card Database.
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from ..state.game_state import GameState, DuelPhase, CardPosition, ZoneCard
from ..database.card_database import CardDatabase, CardInfo

class ActionType(str, Enum):
    NORMAL_SUMMON = "NORMAL_SUMMON"
    SPECIAL_SUMMON = "SPECIAL_SUMMON"
    SET_MONSTER = "SET_MONSTER"
    ACTIVATE_SPELL = "ACTIVATE_SPELL"
    SET_SPELL_TRAP = "SET_SPELL_TRAP"
    ACTIVATE_EFFECT = "ACTIVATE_EFFECT"
    ENTER_BATTLE = "ENTER_BATTLE"
    ATTACK_MONSTER = "ATTACK_MONSTER"
    ATTACK_DIRECT = "ATTACK_DIRECT"
    ENTER_MAIN2 = "ENTER_MAIN2"
    END_TURN = "END_TURN"
    PASS_PROMPT = "PASS_PROMPT"
    CONFIRM_PROMPT = "CONFIRM_PROMPT"

@dataclass
class DuelAction:
    action_type: ActionType
    card_name: str = ""
    source_zone: str = ""  # "HAND", "M1", "GY", etc.
    target_zone: str = ""  # "M3", "ST2", etc.
    target_card: Optional[str] = None
    priority: float = 0.0
    reasoning: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.action_type.value,
            "card": self.card_name,
            "source": self.source_zone,
            "target": self.target_zone,
            "target_card": self.target_card,
            "priority": round(self.priority, 2),
            "reasoning": self.reasoning
        }

    def __str__(self) -> str:
        s = f"{self.action_type.value}: {self.card_name}"
        if self.target_zone:
            s += f" -> {self.target_zone}"
        if self.target_card:
            s += f" (target: {self.target_card})"
        return s

class LegalActionGenerator:
    def __init__(self, card_db: CardDatabase):
        self.card_db = card_db

    def get_legal_actions(self, state: GameState, is_prompt_open: bool = False) -> List[DuelAction]:
        """
        Generates all currently legal tactical actions.
        """
        actions: List[DuelAction] = []

        # If a prompt/chain is awaiting user confirmation
        if is_prompt_open or state.is_chain_active:
            actions.append(DuelAction(
                action_type=ActionType.CONFIRM_PROMPT,
                reasoning="Accept or activate the currently prompted effect/selection"
            ))
            actions.append(DuelAction(
                action_type=ActionType.PASS_PROMPT,
                reasoning="Decline or cancel currently prompted activation"
            ))
            return actions

        # If not player's turn
        if not state.is_player_turn:
            return [DuelAction(action_type=ActionType.PASS_PROMPT, reasoning="Awaiting opponent move")]

        # Phase-based action generation
        if state.phase in [DuelPhase.MAIN1, DuelPhase.MAIN2]:
            actions.extend(self._get_main_phase_actions(state))
        elif state.phase == DuelPhase.BATTLE:
            actions.extend(self._get_battle_phase_actions(state))

        return actions

    def _get_main_phase_actions(self, state: GameState) -> List[DuelAction]:
        actions: List[DuelAction] = []
        empty_m_zone = state.get_first_empty_monster_zone()
        empty_st_zone = state.get_first_empty_st_zone()

        # 1. Normal Summons & Sets from Hand
        if not state.normal_summon_used and empty_m_zone:
            for card_name in state.hand:
                card_info = self.card_db.get_card_by_name(card_name)
                is_monster = card_info and ("Monster" in card_info.card_type or card_info.level > 0)
                # If unknown, assume normal monster if no other info
                if is_monster or card_info is None:
                    # Check tribute requirement (Level 5-6 requires 1, 7+ requires 2)
                    req_tributes = 0
                    if card_info and card_info.level in [5, 6]:
                        req_tributes = 1
                    elif card_info and card_info.level >= 7:
                        req_tributes = 2

                    player_monsters = state.get_player_monsters()
                    if len(player_monsters) >= req_tributes:
                        actions.append(DuelAction(
                            action_type=ActionType.NORMAL_SUMMON,
                            card_name=card_name,
                            source_zone="HAND",
                            target_zone=empty_m_zone,
                            priority=60.0 + (card_info.atk / 100.0 if card_info else 10.0),
                            reasoning=f"Normal Summon {card_name} to {empty_m_zone} (ATK: {card_info.atk if card_info else '?'})"
                        ))

        # 2. Spells & Traps from Hand
        for card_name in state.hand:
            card_info = self.card_db.get_card_by_name(card_name)
            if card_info and "Spell" in card_info.card_type:
                # Activate Spell
                actions.append(DuelAction(
                    action_type=ActionType.ACTIVATE_SPELL,
                    card_name=card_name,
                    source_zone="HAND",
                    target_zone=empty_st_zone or "ST1",
                    priority=75.0 if "searcher" in card_info.roles or "starter" in card_info.roles else 50.0,
                    reasoning=f"Activate Spell {card_name} from Hand"
                ))
            elif card_info and "Trap" in card_info.card_type and empty_st_zone:
                # Set Trap
                actions.append(DuelAction(
                    action_type=ActionType.SET_SPELL_TRAP,
                    card_name=card_name,
                    source_zone="HAND",
                    target_zone=empty_st_zone,
                    priority=40.0,
                    reasoning=f"Set Trap {card_name} in {empty_st_zone}"
                ))

        # 3. On-field Monster & Spell/Trap Ignition Effects
        for m in state.get_player_monsters():
            if not m.has_activated_effect_this_turn:
                card_info = self.card_db.get_card_by_name(m.card_name)
                if card_info and card_info.effects:
                    actions.append(DuelAction(
                        action_type=ActionType.ACTIVATE_EFFECT,
                        card_name=m.card_name,
                        source_zone=m.zone_id,
                        priority=70.0,
                        reasoning=f"Activate on-field effect of {m.card_name} at {m.zone_id}"
                    ))

        # 4. Phase Transition Actions
        if state.phase == DuelPhase.MAIN1:
            # Transition to Battle Phase (if monsters available)
            actions.append(DuelAction(
                action_type=ActionType.ENTER_BATTLE,
                priority=30.0,
                reasoning="Proceed to Battle Phase"
            ))
            # Or directly to End Phase if no combat is viable
            actions.append(DuelAction(
                action_type=ActionType.END_TURN,
                priority=10.0,
                reasoning="Pass turn directly to End Phase"
            ))
        elif state.phase == DuelPhase.MAIN2:
            actions.append(DuelAction(
                action_type=ActionType.END_TURN,
                priority=20.0,
                reasoning="End Turn from Main Phase 2"
            ))

        return actions

    def _get_battle_phase_actions(self, state: GameState) -> List[DuelAction]:
        actions: List[DuelAction] = []
        opp_monsters = state.get_opponent_monsters()
        player_monsters = [m for m in state.get_player_monsters() if m.can_attack and m.position == CardPosition.FACEUP_ATTACK]

        # 1. Attacks
        for attacker in player_monsters:
            if not opp_monsters:
                # Direct Attack
                actions.append(DuelAction(
                    action_type=ActionType.ATTACK_DIRECT,
                    card_name=attacker.card_name,
                    source_zone=attacker.zone_id,
                    target_zone="OPPONENT_LP",
                    priority=85.0 + (attacker.atk / 100.0),
                    reasoning=f"Direct attack with {attacker.card_name} ({attacker.atk} ATK)"
                ))
            else:
                for defender in opp_monsters:
                    # CRITICAL TACTICAL CHECK: Do NOT commit suicide attacks!
                    # Only attack if attacker.atk > defender.atk or defender is in defense with def < atk
                    can_destroy = False
                    if defender.position == CardPosition.FACEUP_ATTACK:
                        if attacker.atk > defender.atk:
                            can_destroy = True
                    elif defender.position in [CardPosition.FACEUP_DEFENSE, CardPosition.FACEDOWN_DEFENSE]:
                        if attacker.atk > defender.def_stat:
                            can_destroy = True

                    if can_destroy:
                        damage = attacker.atk - defender.atk if defender.position == CardPosition.FACEUP_ATTACK else 0
                        actions.append(DuelAction(
                            action_type=ActionType.ATTACK_MONSTER,
                            card_name=attacker.card_name,
                            source_zone=attacker.zone_id,
                            target_zone=defender.zone_id,
                            target_card=defender.card_name,
                            priority=80.0 + (damage / 100.0),
                            reasoning=f"Attack {defender.card_name} ({defender.atk} ATK) with {attacker.card_name} ({attacker.atk} ATK)"
                        ))

        # 2. Advance to Main Phase 2
        actions.append(DuelAction(
            action_type=ActionType.ENTER_MAIN2,
            priority=25.0,
            reasoning="Conclude Battle Phase and enter Main Phase 2"
        ))

        return actions
