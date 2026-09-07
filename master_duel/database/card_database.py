"""
Card Knowledge Database for Yu-Gi-Oh! Master Duel.
Structured repository for card attributes, effects, restrictions, and interactions.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


import sqlite3

@dataclass
class CardData:
    name: str
    card_id: str
    card_type: str  # "MONSTER", "SPELL", "TRAP", "EXTRA"
    attribute: Optional[str] = None
    race: Optional[str] = None
    level_rank: Optional[int] = None
    atk: Optional[int] = None
    def_val: Optional[int] = None
    archetype: Optional[str] = None
    effects: List[str] = field(default_factory=list)
    summon_methods: List[str] = field(default_factory=list)
    is_starter: bool = False
    is_extender: bool = False
    is_searcher: bool = False
    is_boss: bool = False
    is_removal: bool = False
    is_negate: bool = False
    is_defensive: bool = False
    requires_gy: bool = False
    opt: bool = False  # Once per turn
    name_es: Optional[str] = None
    effect_es: Optional[str] = None
    art_url: Optional[str] = None
    md_rarity: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def level(self) -> int:
        return self.level_rank or 0

    @property
    def def_stat(self) -> int:
        return self.def_val or 0

    @property
    def once_per_turn(self) -> bool:
        return self.opt

    @property
    def link_rating(self) -> int:
        return self.level_rank if "LINK" in self.card_type.upper() else 0

    @property
    def roles(self) -> List[str]:
        r = []
        if self.is_starter: r.append("starter")
        if self.is_extender: r.append("extender")
        if self.is_searcher: r.append("searcher")
        if self.is_boss: r.append("boss")
        if self.is_removal: r.append("removal")
        if self.is_negate: r.append("negate")
        if self.is_defensive: r.append("defensive")
        return r

CardInfo = CardData


class CardDatabase:
    """Base de datos de conocimiento de cartas de Yu-Gi-Oh! Master Duel (14.600+ cartas)."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "card_definitions.json")
        self.sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ygo_cards.db")
        self.cards_by_name: Dict[str, CardData] = {}
        self.cards_by_id: Dict[str, CardData] = {}
        self.load_database()

    def load_database(self):
        """Carga las definiciones de cartas prioritarias desde el archivo JSON local."""
        if not os.path.exists(self.db_path):
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for name, item in data.items():
                card = CardData(
                    name=item.get("name", name),
                    card_id=item.get("card_id", ""),
                    card_type=item.get("card_type", "MONSTER"),
                    attribute=item.get("attribute"),
                    race=item.get("race"),
                    level_rank=item.get("level_rank"),
                    atk=item.get("atk"),
                    def_val=item.get("def_val"),
                    archetype=item.get("archetype"),
                    effects=item.get("effects", []),
                    summon_methods=item.get("summon_methods", []),
                    is_starter=item.get("is_starter", False),
                    is_extender=item.get("is_extender", False),
                    is_searcher=item.get("is_searcher", False),
                    is_boss=item.get("is_boss", False),
                    is_removal=item.get("is_removal", False),
                    is_negate=item.get("is_negate", False),
                    is_defensive=item.get("is_defensive", False),
                    requires_gy=item.get("requires_gy", False),
                    opt=item.get("opt", False),
                    raw_data=item
                )
                self.cards_by_name[card.name.lower()] = card
                if card.card_id:
                    self.cards_by_id[card.card_id] = card

        except Exception as e:
            print(f"[WARN] Error loading card database: {e}")

    def _query_sqlite(self, query_str: str) -> Optional[CardData]:
        """Consulta la base de datos SQLite maestra (14.600+ cartas)."""
        if not os.path.exists(self.sqlite_path):
            return None

        q = query_str.strip()
        if not q:
            return None

        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            # 1. Búsqueda exacta por name_en, name_es o passcode
            cursor.execute("""
            SELECT id, passcode, name_en, name_es, effect_en, effect_es,
                   card_type, attribute, race, level_rank, atk, def_val, scale,
                   md_rarity, art_url, card_url, is_boss, is_negate, is_opt
            FROM cards
            WHERE name_en = ? OR name_es = ? OR passcode = ?
            LIMIT 1
            """, (q, q, q))
            row = cursor.fetchone()

            # 2. Si no hay coincidencia exacta, probar búsqueda flexible LIKE
            if not row and len(q) >= 3:
                cursor.execute("""
                SELECT id, passcode, name_en, name_es, effect_en, effect_es,
                       card_type, attribute, race, level_rank, atk, def_val, scale,
                       md_rarity, art_url, card_url, is_boss, is_negate, is_opt
                FROM cards
                WHERE name_en LIKE ? OR name_es LIKE ?
                ORDER BY length(name_en) ASC
                LIMIT 1
                """, (f"%{q}%", f"%{q}%"))
                row = cursor.fetchone()

            conn.close()

            if not row:
                return None

            (c_id, passcode, name_en, name_es, effect_en, effect_es,
             card_type, attr, race, level_rank, atk, def_val, scale,
             md_rarity, art_url, card_url, is_boss, is_negate, is_opt) = row

            effects_list = [effect_en] if effect_en else []
            card = CardData(
                name=name_en,
                card_id=passcode or c_id,
                card_type=card_type or "MONSTER",
                attribute=attr,
                race=race,
                level_rank=level_rank,
                atk=atk,
                def_val=def_val,
                effects=effects_list,
                is_starter=bool(level_rank and level_rank <= 4 and card_type == "MONSTER"),
                is_boss=bool(is_boss),
                is_negate=bool(is_negate),
                opt=bool(is_opt),
                name_es=name_es,
                effect_es=effect_es,
                art_url=art_url,
                md_rarity=md_rarity,
                raw_data={"passcode": passcode, "scale": scale, "card_url": card_url}
            )

            # Guardar en memoria caché para futuras consultas O(1)
            self.cards_by_name[name_en.lower()] = card
            if name_es:
                self.cards_by_name[name_es.lower()] = card
            if passcode:
                self.cards_by_id[passcode] = card

            return card

        except Exception as e:
            return None

    def get_card(self, name_or_id: str) -> Optional[CardData]:
        """Busca una carta por nombre (en inglés o español) o ID."""
        if not name_or_id:
            return None
        
        q = name_or_id.lower().strip()

        # 1. Búsqueda en memoria caché rápida
        c = self.cards_by_name.get(q)
        if c:
            return c

        c = self.cards_by_id.get(name_or_id.strip())
        if c:
            return c

        for k, v in self.cards_by_name.items():
            if q == k or (len(q) > 4 and q in k):
                return v

        # 2. Búsqueda en la base de datos maestra SQLite (14.616 cartas)
        return self._query_sqlite(name_or_id)

    def get_card_by_name(self, name: str) -> Optional[CardData]:
        """Convenience lookup strictly by card name."""
        return self.get_card(name)

    def register_card(self, card: CardData):
        """Registra dinámicamente una nueva carta aprendida en la base de datos."""
        self.cards_by_name[card.name.lower()] = card
        if card.name_es:
            self.cards_by_name[card.name_es.lower()] = card
        if card.card_id:
            self.cards_by_id[card.card_id] = card
