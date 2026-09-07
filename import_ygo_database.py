"""
Importador de la base de datos YGOJSON a SQLite para Master Duel Bot.
Lee 'individual/mas/cards.json' (14.616+ cartas) y genera 'master_duel/database/ygo_cards.db'.
Incluye nombres y efectos en Español e Inglés, stats, arquetipos, enlaces a artworks y rarezas MD.
"""

import os
import sys
import json
import sqlite3
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "individual" / "mas" / "cards.json"
DB_PATH = BASE_DIR / "master_duel" / "database" / "ygo_cards.db"

def determine_card_type(item: dict) -> str:
    ctype = item.get("cardType", "").upper()
    classifs = [c.upper() for c in item.get("classifications", []) or []]
    
    if "SPELL" in ctype:
        return "SPELL"
    if "TRAP" in ctype:
        return "TRAP"
    
    if "LINK" in classifs:
        return "LINK"
    if "XYZ" in classifs:
        return "XYZ"
    if "SYNCHRO" in classifs:
        return "SYNCHRO"
    if "FUSION" in classifs:
        return "FUSION"
    if "RITUAL" in classifs:
        return "RITUAL"
    
    return "MONSTER"

def import_database():
    if not JSON_PATH.exists():
        print(f"[ERROR] No se encuentra el archivo maestro: {JSON_PATH}")
        return False

    print("=" * 65)
    print("  IMPORTANDO BASE DE DATOS MAESTRA YU-GI-OH! (14.600+ CARTAS)")
    print("=" * 65)
    print(f"  Origen:  {JSON_PATH}")
    print(f"  Destino: {DB_PATH}\n")

    t0 = time.time()
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        cards_raw = json.load(f)

    total_cards = len(cards_raw)
    print(f"  Cartas leídas del archivo JSON: {total_cards}")

    # Crear directorio si no existe
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Conectar a SQLite
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except Exception:
            pass

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        id TEXT PRIMARY KEY,
        passcode TEXT,
        name_en TEXT COLLATE NOCASE,
        name_es TEXT COLLATE NOCASE,
        effect_en TEXT,
        effect_es TEXT,
        card_type TEXT,
        attribute TEXT,
        race TEXT,
        level_rank INTEGER,
        atk INTEGER,
        def_val INTEGER,
        scale INTEGER,
        md_rarity TEXT,
        art_url TEXT,
        card_url TEXT,
        is_boss BOOLEAN,
        is_negate BOOLEAN,
        is_opt BOOLEAN
    )
    """)

    # Índices para búsqueda instantánea en < 0.1ms
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name_en ON cards(name_en);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name_es ON cards(name_es);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_passcode ON cards(passcode);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_card_type ON cards(card_type);")

    rows = []
    for c in cards_raw:
        card_id = c.get("id", "")
        passwords = c.get("passwords", []) or []
        passcode = str(passwords[0]) if passwords else ""

        text = c.get("text", {}) or {}
        en_info = text.get("en", {}) or {}
        es_info = text.get("es", {}) or {}

        name_en = en_info.get("name", "").strip()
        name_es = es_info.get("name", "").strip() or name_en
        effect_en = en_info.get("effect", "").strip()
        effect_es = es_info.get("effect", "").strip() or effect_en

        card_type = determine_card_type(c)
        attr = (c.get("attribute") or "").upper()
        race = (c.get("type") or "").upper()
        # Parsear stats que pueden ser "?" o string
        def safe_int(val):
            if val is None:
                return None
            try:
                return int(val)
            except (ValueError, TypeError):
                return None

        level_rank = safe_int(c.get("level"))
        atk_num = safe_int(c.get("atk"))
        def_num = safe_int(c.get("def"))
        scale = safe_int(c.get("scale"))

        md_info = c.get("masterDuel") or {}
        md_rarity = (md_info.get("rarity") or "").upper()

        images = c.get("images", []) or []
        art_url = images[0].get("art", "") if images else ""
        card_url = images[0].get("card", "") if images else ""

        # Roles tácticos automáticos
        full_text_en = effect_en.lower()
        full_text_es = effect_es.lower()
        
        is_boss = bool((atk_num and atk_num >= 2500) or (level_rank and level_rank >= 7 and card_type == "MONSTER"))
        is_negate = "negate" in full_text_en or "niega" in full_text_es or "negar" in full_text_es
        is_opt = "once per turn" in full_text_en or "una vez por turno" in full_text_es or "1 vez por turno" in full_text_es

        rows.append((
            card_id, passcode, name_en, name_es, effect_en, effect_es,
            card_type, attr, race, level_rank, atk_num, def_num, scale,
            md_rarity, art_url, card_url,
            is_boss, is_negate, is_opt
        ))

    cursor.executemany("""
    INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)

    conn.commit()
    conn.close()

    elapsed = time.time() - t0
    db_size_mb = DB_PATH.stat().st_size / (1024 * 1024)
    print(f"\n[OK] Base de datos creada con éxito en {elapsed:.2f}s!")
    print(f"     Total cartas insertadas: {len(rows)}")
    print(f"     Tamaño del archivo DB:  {db_size_mb:.2f} MB")
    print(f"     Ubicación:               {DB_PATH}")
    print("=" * 65)
    return True

if __name__ == "__main__":
    import_database()
