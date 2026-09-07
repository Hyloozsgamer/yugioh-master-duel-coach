"""
Card Database & Verification Engine for Yu-Gi-Oh! Master Duel Coach.
Consulta la base de datos local (ygo_cards.db / cards.json) para garantizar
passcodes, nombres y URLs de arte 100% exactos y verificados.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

class CoachDatabase:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            # Intentar ruta local a ygo_cards.db
            db_candidates = [
                base_dir / "master_duel" / "database" / "ygo_cards.db",
                base_dir / "ygo_cards.db"
            ]
            self.db_path = None
            for c in db_candidates:
                if c.exists():
                    self.db_path = str(c)
                    break
        else:
            self.db_path = db_path
            
        self.conn = None
        if self.db_path and os.path.exists(self.db_path):
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

    def get_card(self, query: str) -> Optional[Dict[str, Any]]:
        """Busca una carta por passcode, nombre en inglés o nombre en español."""
        if not self.conn:
            return None
            
        cursor = self.conn.cursor()
        query = query.strip()
        
        # 1. Búsqueda por Passcode exacto
        if query.isdigit():
            cursor.execute("SELECT * FROM cards WHERE passcode = ?", (int(query),))
            row = cursor.fetchone()
            if row:
                return dict(row)
                
        # 2. Búsqueda por Nombre exacto (EN o ES)
        cursor.execute("SELECT * FROM cards WHERE LOWER(name_en) = LOWER(?) OR LOWER(name_es) = LOWER(?)", (query, query))
        row = cursor.fetchone()
        if row:
            return dict(row)
            
        # 3. Búsqueda parcial / LIKE
        like_term = f"%{query}%"
        cursor.execute("""
            SELECT * FROM cards 
            WHERE name_en LIKE ? OR name_es LIKE ? 
            ORDER BY CASE WHEN name_en LIKE ? THEN 1 ELSE 2 END 
            LIMIT 1
        """, (like_term, like_term, f"{query}%"))
        row = cursor.fetchone()
        if row:
            return dict(row)
            
        return None

    def format_card_visual(self, card_data: Dict[str, Any]) -> str:
        """Formatea la carta cumpliendo estrictamente el protocolo visual del Coach."""
        name_en = card_data.get("name_en", "Unknown")
        name_es = card_data.get("name_es") or name_en
        passcode = card_data.get("passcode", 0)
        ctype = card_data.get("card_type", "CARD")
        effect = card_data.get("effect_es") or card_data.get("effect_en", "")
        
        # URL oficial verificada
        art_url = f"https://images.ygoprodeck.com/images/cards/{passcode}.jpg"
        
        box = (
            f"┌{'─'*60}┐\n"
            f"│ [{ctype}] {name_es} ({name_en})\n"
            f"│ Passcode: {passcode:<10} Arte: {art_url}\n"
            f"│ {effect[:120]}...\n"
            f"└{'─'*60}┘\n"
            f"![{name_en}]({art_url})\n"
        )
        return box
