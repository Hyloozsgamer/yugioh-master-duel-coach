"""
Game State Model for Yu-Gi-Oh! Master Duel AI.
Maintains in-memory representation of Turn, Phase, LP, Zones, Hand, GY, Chain, and Opponent known cards.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import json
import time

class DuelPhase(str, Enum):
    DRAW = "DRAW"
    STANDBY = "STANDBY"
    MAIN1 = "MAIN1"
    BATTLE = "BATTLE"
    MAIN2 = "MAIN2"
    END = "END"
    OPPONENT = "OPPONENT"
    UNKNOWN = "UNKNOWN"

class CardPosition(str, Enum):
    FACEUP_ATTACK = "FACEUP_ATTACK"
    FACEUP_DEFENSE = "FACEUP_DEFENSE"
    FACEDOWN_DEFENSE = "FACEDOWN_DEFENSE"
    FACEDOWN_SET = "FACEDOWN_SET"
    FACEUP_SPELL = "FACEUP_SPELL"
    UNKNOWN = "UNKNOWN"

@dataclass
class ZoneCard:
    zone_id: str
    card_name: str = "UNKNOWN_CARD"
    card_id: Optional[str] = None
    position: CardPosition = CardPosition.FACEUP_ATTACK
    atk: int = 0
    def_stat: int = 0
    can_attack: bool = True
    effects_negated: bool = False
    has_activated_effect_this_turn: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "card_name": self.card_name,
            "card_id": self.card_id,
            "position": self.position.value,
            "atk": self.atk,
            "def": self.def_stat,
            "can_attack": self.can_attack,
            "effects_negated": self.effects_negated,
            "has_activated_effect_this_turn": self.has_activated_effect_this_turn
        }

@dataclass
class ChainLink:
    link_number: int
    player: str  # "PLAYER" or "OPPONENT"
    card_name: str
    effect_description: str = ""
    target: Optional[str] = None

@dataclass
class GameState:
    turn: int = 1
    is_player_turn: bool = True
    phase: DuelPhase = DuelPhase.MAIN1
    
    # Life Points
    player_lp: int = 8000
    opponent_lp: int = 8000
    
    # Hand
    hand: List[str] = field(default_factory=list)
    hand_count: int = 0
    
    # Player zones
    monster_zones: Dict[str, Optional[ZoneCard]] = field(default_factory=lambda: {
        "M1": None, "M2": None, "M3": None, "M4": None, "M5": None,
        "EMZ_LEFT": None, "EMZ_RIGHT": None
    })
    spell_trap_zones: Dict[str, Optional[ZoneCard]] = field(default_factory=lambda: {
        "ST1": None, "ST2": None, "ST3": None, "ST4": None, "ST5": None
    })
    
    # Opponent zones
    opp_monster_zones: Dict[str, Optional[ZoneCard]] = field(default_factory=lambda: {
        "OPP_M1": None, "OPP_M2": None, "OPP_M3": None, "OPP_M4": None, "OPP_M5": None
    })
    opp_spell_trap_zones: Dict[str, Optional[ZoneCard]] = field(default_factory=lambda: {
        "OPP_ST1": None, "OPP_ST2": None, "OPP_ST3": None, "OPP_ST4": None, "OPP_ST5": None
    })
    opp_hand_count: int = 5
    
    # Graveyards & Banished
    player_gy: List[str] = field(default_factory=list)
    opponent_gy: List[str] = field(default_factory=list)
    player_banished: List[str] = field(default_factory=list)
    opponent_banished: List[str] = field(default_factory=list)
    
    # Deck & Extra Deck counts
    deck_count: int = 40
    extra_deck_count: int = 15
    
    # Chain management
    current_chain: List[ChainLink] = field(default_factory=list)
    is_chain_active: bool = False
    
    # Tactical memory & restrictions
    normal_summon_used: bool = False
    special_summons_this_turn: int = 0
    activated_effects_opt: List[str] = field(default_factory=list)
    opponent_known_cards: List[str] = field(default_factory=list)
    
    # Meta / AI attributes
    confidence: float = 1.0
    last_action_desc: str = "Init"
    timestamp: float = field(default_factory=time.time)

    def get_player_monsters(self) -> List[ZoneCard]:
        return [m for m in self.monster_zones.values() if m is not None]

    def get_opponent_monsters(self) -> List[ZoneCard]:
        return [m for m in self.opp_monster_zones.values() if m is not None]

    def get_first_empty_monster_zone(self) -> Optional[str]:
        for zone in ["M3", "M2", "M4", "M1", "M5"]:
            if self.monster_zones.get(zone) is None:
                return zone
        return None

    def get_first_empty_st_zone(self) -> Optional[str]:
        for zone in ["ST3", "ST2", "ST4", "ST1", "ST5"]:
            if self.spell_trap_zones.get(zone) is None:
                return zone
        return None

    def get_highest_atk_player_monster(self) -> Optional[ZoneCard]:
        monsters = self.get_player_monsters()
        if not monsters:
            return None
        return max(monsters, key=lambda m: m.atk)

    def get_highest_atk_opp_monster(self) -> Optional[ZoneCard]:
        monsters = self.get_opponent_monsters()
        if not monsters:
            return None
        return max(monsters, key=lambda m: m.atk)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn": self.turn,
            "is_player_turn": self.is_player_turn,
            "phase": self.phase.value if hasattr(self.phase, "value") else str(self.phase),
            "player_lp": self.player_lp,
            "opponent_lp": self.opponent_lp,
            "hand": self.hand,
            "hand_count": len(self.hand) if self.hand else self.hand_count,
            "player_monsters": [m.to_dict() for m in self.get_player_monsters()],
            "player_st": [s.to_dict() for s in self.spell_trap_zones.values() if s is not None],
            "opp_monsters": [m.to_dict() for m in self.get_opponent_monsters()],
            "opp_st": [s.to_dict() for s in self.opp_spell_trap_zones.values() if s is not None],
            "player_gy_count": len(self.player_gy),
            "normal_summon_used": self.normal_summon_used,
            "chain_active": self.is_chain_active,
            "confidence": round(self.confidence, 3),
            "last_action_desc": self.last_action_desc
        }

    def summary(self) -> str:
        monsters_str = ", ".join(f"{m.zone_id}:{m.card_name}({m.atk})" for m in self.get_player_monsters()) or "None"
        opp_monsters_str = ", ".join(f"{m.zone_id}:{m.card_name}({m.atk})" for m in self.get_opponent_monsters()) or "None"
        hand_str = ", ".join(self.hand) if self.hand else f"({self.hand_count} cards)"
        return (
            f"Turn {self.turn} [{self.phase.value}] LP: {self.player_lp}/{self.opponent_lp} | "
            f"Hand: [{hand_str}] | Player Field: [{monsters_str}] | Opp Field: [{opp_monsters_str}]"
        )
