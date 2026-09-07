"""
Deck Analysis Engine for Yu-Gi-Oh! Master Duel.
Evaluates deck composition, categorizes card roles, and maps combo lines:
- Starters, Extenders, Searchers, Defensive, Removal, Boss Monsters, Bricks.
- Extra Deck capabilities.
- Opening hand analysis.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from master_duel.database.card_database import CardDatabase, CardData


@dataclass
class DeckProfile:
    name: str
    main_deck: List[str] = field(default_factory=list)
    extra_deck: List[str] = field(default_factory=list)
    starters: List[str] = field(default_factory=list)
    extenders: List[str] = field(default_factory=list)
    searchers: List[str] = field(default_factory=list)
    defensive_cards: List[str] = field(default_factory=list)
    removal_cards: List[str] = field(default_factory=list)
    boss_monsters: List[str] = field(default_factory=list)
    bricks: List[str] = field(default_factory=list)
    combos: List[Dict] = field(default_factory=list)
    priorities: List[str] = field(default_factory=list)
    heuristics: Dict[str, any] = field(default_factory=dict)


class DeckAnalyzer:
    """Analizador estratégico de barajas de Yu-Gi-Oh! Master Duel."""

    def __init__(self, card_db: Optional[CardDatabase] = None, decks_dir: Optional[str] = None):
        self.db = card_db or CardDatabase()
        self.decks_dir = decks_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "decks")
        self.loaded_profiles: Dict[str, DeckProfile] = {}

    def load_profile(self, profile_name: str = "gladiator_beast") -> DeckProfile:
        """Carga un perfil de baraja desde su directorio en /decks/."""
        if profile_name in self.loaded_profiles:
            return self.loaded_profiles[profile_name]

        profile_dir = os.path.join(self.decks_dir, profile_name)
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir, exist_ok=True)
            self._create_default_profile(profile_dir, profile_name)

        deck_file = os.path.join(profile_dir, "deck.json")
        combos_file = os.path.join(profile_dir, "combos.json")
        priorities_file = os.path.join(profile_dir, "priorities.json")
        heuristics_file = os.path.join(profile_dir, "heuristics.json")

        main_cards, extra_cards = [], []
        if os.path.exists(deck_file):
            with open(deck_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                main_cards = d.get("main", [])
                extra_cards = d.get("extra", [])

        combos = []
        if os.path.exists(combos_file):
            with open(combos_file, "r", encoding="utf-8") as f:
                combos = json.load(f).get("combos", [])

        priorities = []
        if os.path.exists(priorities_file):
            with open(priorities_file, "r", encoding="utf-8") as f:
                priorities = json.load(f).get("summon_priority", [])

        heuristics = {}
        if os.path.exists(heuristics_file):
            with open(heuristics_file, "r", encoding="utf-8") as f:
                heuristics = json.load(f)

        # Analizar roles automáticamente cruzando con la base de datos
        profile = self.analyze_deck(profile_name, main_cards, extra_cards)
        profile.combos = combos
        profile.priorities = priorities
        profile.heuristics = heuristics

        self.loaded_profiles[profile_name] = profile
        return profile

    def analyze_deck(self, name_or_main: any, main_cards: Optional[List[str]] = None, extra_cards: Optional[List[str]] = None) -> DeckProfile:
        """Categoriza las cartas del mazo por su función táctica."""
        if isinstance(name_or_main, list):
            name = "custom_deck"
            extra_cards = main_cards or []
            main_cards = name_or_main
        else:
            name = str(name_or_main)
            main_cards = main_cards or []
            extra_cards = extra_cards or []

        starters, extenders, searchers = [], [], []
        defensive, removal, boss, bricks = [], [], [], []

        for c_name in main_cards:
            card = self.db.get_card(c_name)
            if not card:
                continue

            if card.is_searcher:
                searchers.append(card.name)
            if card.is_starter:
                starters.append(card.name)
            if card.is_extender:
                extenders.append(card.name)
            if card.is_defensive or card.is_negate:
                defensive.append(card.name)
            if card.is_removal:
                removal.append(card.name)
            if card.is_boss:
                boss.append(card.name)

            # Bricks: Monstruos de nivel >= 5 sin métodos de invocación especial propia
            if card.card_type == "MONSTER" and card.level_rank and card.level_rank >= 5:
                if "SPECIAL" not in card.summon_methods:
                    bricks.append(card.name)

        for c_name in extra_cards:
            card = self.db.get_card(c_name)
            if card:
                boss.append(card.name)

        return DeckProfile(
            name=name,
            main_deck=main_cards,
            extra_deck=extra_cards,
            starters=list(set(starters)),
            extenders=list(set(extenders)),
            searchers=list(set(searchers)),
            defensive_cards=list(set(defensive)),
            removal_cards=list(set(removal)),
            boss_monsters=list(set(boss)),
            bricks=list(set(bricks))
        )

    def _create_default_profile(self, target_dir: str, profile_name: str):
        """Crea archivos JSON por defecto si no existen."""
        default_deck = {
            "main": [
                "Gladiator Proving Ground",
                "Gladiator Beast Laquari",
                "Gladiator Beast Attorix",
                "Gladiator Beast Bestiari",
                "Gladiator Beast Vespasius",
                "Gladiator Beast United",
                "Gladiator Beast War Chariot",
                "Monster Reborn",
                "Raigeki"
            ],
            "extra": [
                "Gladiator Beast Gyzarus"
            ]
        }
        with open(os.path.join(target_dir, "deck.json"), "w", encoding="utf-8") as f:
            json.dump(default_deck, f, indent=2)

        default_combos = {
            "combos": [
                {
                    "name": "Search into Laquari",
                    "requires": ["Gladiator Proving Ground"],
                    "steps": [
                        "Activate Gladiator Proving Ground",
                        "Search Gladiator Beast Laquari",
                        "Normal Summon Gladiator Beast Laquari in Attack Position"
                    ]
                },
                {
                    "name": "Attorix Defensive Wall",
                    "requires": ["Gladiator Beast Attorix"],
                    "steps": [
                        "Normal Summon or Set Gladiator Beast Attorix in Defense Position (2000 DEF)"
                    ]
                }
            ]
        }
        with open(os.path.join(target_dir, "combos.json"), "w", encoding="utf-8") as f:
            json.dump(default_combos, f, indent=2)

        default_priorities = {
            "summon_priority": [
                "Gladiator Beast Gyzarus",
                "Gladiator Beast Laquari",
                "Gladiator Beast Bestiari",
                "Gladiator Beast Attorix"
            ]
        }
        with open(os.path.join(target_dir, "priorities.json"), "w", encoding="utf-8") as f:
            json.dump(default_priorities, f, indent=2)

        default_heuristics = {
            "prefer_defense_if_atk_below": 1400,
            "always_search_before_normal_summon": True,
            "never_attack_higher_atk": True,
            "set_traps_before_turn_end": True
        }
        with open(os.path.join(target_dir, "heuristics.json"), "w", encoding="utf-8") as f:
            json.dump(default_heuristics, f, indent=2)
