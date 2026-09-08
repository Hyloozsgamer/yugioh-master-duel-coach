"""
Yu-Gi-Oh! Master Duel Coach - Módulo de Internacionalización (i18n)
Soporte completo para Español (ES), Inglés (EN), Francés (FR), Alemán (DE) e Italiano (IT).
"""

LANGUAGES = {
    "ES": "Español",
    "EN": "English",
    "FR": "Français",
    "DE": "Deutsch",
    "IT": "Italiano"
}

TRANSLATIONS = {
    "scan_btn_hotkey": {
        "ES": "[SCAN] ESCANEAR [F5]",
        "EN": "[SCAN] SCAN [F5]",
        "FR": "[SCAN] SCANNER [F5]",
        "DE": "[SCAN] SCANNEN [F5]",
        "IT": "[SCAN] SCANSIONA [F5]"
    },
    "active_deck_label": {
        "ES": "Mazo:",
        "EN": "Deck:",
        "FR": "Deck:",
        "DE": "Deck:",
        "IT": "Deck:"
    },
    "app_title": {
        "ES": "COACH TÁCTICO MASTER DUEL",
        "EN": "MASTER DUEL TACTICAL COACH",
        "FR": "COACH TACTIQUE MASTER DUEL",
        "DE": "MASTER DUEL TAKTIK-COACH",
        "IT": "COACH TATTICO MASTER DUEL"
    },
    "live_badge": {
        "ES": "EN VIVO",
        "EN": "LIVE",
        "FR": "EN DIRECT",
        "DE": "LIVE",
        "IT": "IN DIRETTA"
    },
    "dock_btn": {
        "ES": "[LOCK] Acoplar",
        "EN": "[LOCK] Dock",
        "FR": "[LOCK] Ancrer",
        "DE": "[LOCK] Andocken",
        "IT": "[LOCK] Blocca"
    },
    "scan_deck_btn": {
        "ES": "[GUIA] Escanear Deck",
        "EN": "[GUIA] Scan Deck",
        "FR": "[GUIA] Scanner le Deck",
        "DE": "[GUIA] Deck Scannen",
        "IT": "[GUIA] Scansiona Deck"
    },
    "scanning_status": {
        "ES": "Escaneando Master Duel en tiempo real...",
        "EN": "Scanning Master Duel in real-time...",
        "FR": "Analyse de Master Duel en temps réel...",
        "DE": "Master Duel wird in Echtzeit gescannt...",
        "IT": "Scansione di Master Duel in tempo reale..."
    },
    "loaner_deck_tag": {
        "ES": "DECK PRESTADO",
        "EN": "LOANER DECK",
        "FR": "DECK D'EMPRUNT",
        "DE": "LEIH-DECK",
        "IT": "DECK IN PRESTITO"
    },
    "deck_tag": {
        "ES": "DECK",
        "EN": "DECK",
        "FR": "DECK",
        "DE": "DECK",
        "IT": "DECK"
    },
    "ready_to_play": {
        "ES": "¡Ya puedes darle a jugar! • Modo Solo",
        "EN": "Ready to play! • Solo Mode",
        "FR": "Prêt à jouer ! • Mode Solo",
        "DE": "Bereit zum Spielen! • Solo-Modus",
        "IT": "Pronto a giocare! • Modalità Solo"
    },
    "guide_btn": {
        "ES": "[GUIA] Estrategia",
        "EN": "[GUIA] Strategy",
        "FR": "[GUIA] Stratégie",
        "DE": "[GUIA] Strategie",
        "IT": "[GUIA] Strategia"
    },
    "hero_title": {
        "ES": "⭐ JUGADA RECOMENDADA (JUEGA AHORA)",
        "EN": "⭐ RECOMMENDED PLAY (PLAY NOW)",
        "FR": "⭐ COUP RECOMMANDÉ (JOUER MAINTENANT)",
        "DE": "⭐ EMPFOHLENE AKTION (JETZT SPIELEN)",
        "IT": "⭐ MOSSA RACCOMANDATA (GIOCA ORA)"
    },
    "waiting_duel": {
        "ES": "Esperando detección de duelo...",
        "EN": "Waiting for duel detection...",
        "FR": "En attente de détection du duel...",
        "DE": "Warte auf Duell-Erkennung...",
        "IT": "In attesa di rilevamento duello..."
    },
    "evaluating_hand": {
        "ES": "> Inicia tu turno o abre tu mano para evaluar la mejor jugada.",
        "EN": "> Start your turn or check your hand to evaluate the best play.",
        "FR": "> Commencez votre tour ou ouvrez votre main pour évaluer le coup.",
        "DE": "> Beginne deinen Spielzug, um den besten Zug zu ermitteln.",
        "IT": "> Inizia il tuo turno o apri la mano per valutare la giocata."
    },
    "default_objective": {
        "ES": "[OBJETIVO] Objetivo: Establecer presencia en campo.",
        "EN": "[OBJETIVO] Objective: Establish board presence.",
        "FR": "[OBJETIVO] Objectif : Établir une présence sur le terrain.",
        "DE": "[OBJETIVO] Ziel: Spielfeldpräsenz aufbauen.",
        "IT": "[OBJETIVO] Obiettivo: Stabilire presenza sul terreno."
    },
    "combo_route_title": {
        "ES": "RUTA DEL COMBO (PASO A PASO VISUAL)",
        "EN": "COMBO ROUTE (VISUAL STEP-BY-STEP)",
        "FR": "ROUTE DU COMBO (PAS À PAS VISUEL)",
        "DE": "COMBO-ROUTE (VISUELL SCHRITT FÜR SCHRITT)",
        "IT": "ROTTA DELLA COMBO (PASSO DOPO PASSO VISIVO)"
    },
    "combo_tip": {
        "ES": "[OBJETIVO] Haz clic en cualquier carta de la ruta para ver su detalle.",
        "EN": "[OBJETIVO] Click any card in the route to view its details.",
        "FR": "[OBJETIVO] Cliquez sur n'importe quelle carte pour voir ses détails.",
        "DE": "[OBJETIVO] Klicke auf eine Karte, um ihre Details anzuzeigen.",
        "IT": "[OBJETIVO] Clicca su qualsiasi carta della rotta per vederne i dettagli."
    },
    "tactical_alert_title": {
        "ES": "[ALERTA] ALERTA TÁCTICA DEL ADVERSARIO",
        "EN": "[ALERTA] OPPONENT TACTICAL ALERT",
        "FR": "[ALERTA] ALERTE TACTIQUE DE L'ADVERSAIRE",
        "DE": "[ALERTA] TAKTISCHE GEGNER-WARNUNG",
        "IT": "[ALERTA] AVVISO TATTICO DELL'AVVERSARIO"
    },
    "tactical_alert_default": {
        "ES": "• Evalúa el campo del rival antes de atacar a ciegas.",
        "EN": "• Evaluate opponent's field before blindly attacking.",
        "FR": "• Évaluez le terrain adverse avant d'attaquer à l'aveugle.",
        "DE": "• Beurteile das gegnerische Feld, bevor du blind angreifst.",
        "IT": "• Valuta il terreno avversario prima di attaccare alla cieca."
    },
    "hand_title": {
        "ES": "[MANO] TU MANO (DETECCIÓN EN TIEMPO REAL)",
        "EN": "[MANO] YOUR HAND (REAL-TIME DETECTION)",
        "FR": "[MANO] VOTRE MAIN (DÉTECTION EN TEMPS RÉEL)",
        "DE": "[MANO] DEINE HAND (ECHTZEIT-ERKENNUNG)",
        "IT": "[MANO] LA TUA MANO (RILEVAMENTO IN TEMPO REALE)"
    },
    "hand_empty": {
        "ES": "Mano vacía o en transición de fase",
        "EN": "Hand empty or phase transition",
        "FR": "Main vide ou transition de phase",
        "DE": "Hand leer oder Phasenübergang",
        "IT": "Mano vuota o transizione di fase"
    },
    "play_now_tag": {
        "ES": "> JUGAR AHORA",
        "EN": "> PLAY NOW",
        "FR": "> JOUER",
        "DE": "> JETZT SPIELEN",
        "IT": "> GIOCA ORA"
    },
    "extension_tag": {
        "ES": "Extensión",
        "EN": "Extension",
        "FR": "Extension",
        "DE": "Erweiterung",
        "IT": "Estensione"
    },
    "save_tag": {
        "ES": "Guardar",
        "EN": "Save",
        "FR": "Garder",
        "DE": "Aufheben",
        "IT": "Conserva"
    },
    "close_btn": {
        "ES": " Cerrar",
        "EN": " Close",
        "FR": " Fermer",
        "DE": " Schließen",
        "IT": " Chiudi"
    },
    "phase_start": {
        "ES": "1. INICIO",
        "EN": "1. START",
        "FR": "1. DÉBUT",
        "DE": "1. START",
        "IT": "1. INIZIO"
    },
    "phase_ext": {
        "ES": "2. EXTENSIÓN",
        "EN": "2. EXTEND",
        "FR": "2. EXTENSION",
        "DE": "2. ERWEIT.",
        "IT": "2. ESTENS."
    },
    "phase_extra": {
        "ES": "3. EXTRA DECK",
        "EN": "3. EXTRA DECK",
        "FR": "3. EXTRA DECK",
        "DE": "3. EXTRA DECK",
        "IT": "3. EXTRA DECK"
    },
    "phase_finish": {
        "ES": "4. REMATE",
        "EN": "4. FINISHER",
        "FR": "4. REMATE",
        "DE": "4. FINISHER",
        "IT": "4. FINALE"
    }
}

def t(key: str, lang: str = "ES") -> str:
    """Obtiene el texto localizado para una clave dada en el idioma solicitado."""
    lang_upper = (lang or "ES").upper()
    if lang_upper not in LANGUAGES:
        lang_upper = "ES"
    
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang_upper, entry.get("ES", key))
