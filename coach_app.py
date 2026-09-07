"""
Yu-Gi-Oh! MASTER DUEL — HEAD COACH PROFESIONAL
Sistema Autónomo de Alto Rendimiento para Entrenamiento Competitivo Diamond-Master.
"""

import os
import sys
import time
from coach.database import CoachDatabase
from coach.board import BoardDiagram
from coach.drills import DRILLS
from coach.deck_doctor import DeckDoctor

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_header():
    print("=" * 72)
    print("  YU-GI-OH! MASTER DUEL — HEAD COACH PROFESIONAL (DIAMOND-MASTER)")
    print("  Sistema Autónomo de Alto Rendimiento | Análisis de EV y Jugadas")
    print("=" * 72)
    print()

def run_drill(drill_idx: int, db: CoachDatabase):
    if drill_idx >= len(DRILLS):
        print(f"\n[INFO] Drill {drill_idx + 1} no disponible.")
        return False

    drill = DRILLS[drill_idx]
    print("\n" + "#" * 72)
    print(f"  {drill['title'].upper()}")
    print(f"  Enfoque: {drill['focus']}")
    print("#" * 72 + "\n")

    # Diagrama de Campo
    print("DIAGRAMA DE ESTADO:")
    diagram = BoardDiagram.render(
        rival_lp=8000,
        my_lp=8000,
        my_hand=drill["hand"],
        my_deck_count=35
    )
    print(diagram)

    print("MANO INICIAL EVALUADA:")
    for card in drill["hand"]:
        card_info = db.get_card(card)
        if card_info:
            print(f" • {card_info['name_es']} / {card_info['name_en']} [Passcode: {card_info['passcode']}]")
            print(f"   ![{card_info['name_en']}](https://images.ygoprodeck.com/images/cards/{card_info['passcode']}.jpg)")
        else:
            print(f" • {card} [SIN ARTE]")
    print()

    print(f"PREGUNTA TÁCTICA:\n{drill['question']}\n")
    for opt in drill["options"]:
        print(f"  {opt}")
    print("  E) Otra: escribe tu propia secuencia")
    print()

    choice = input("Tu elección (A/B/C/D/E): ").strip().upper()
    print()

    if choice == drill["correct_option"]:
        print(" verdict: ¡CORRECTA! Línea de valor máximo (EV).")
    else:
        print(f" verdict: INCORRECTA O SUBÓPTIMA. La línea óptima es la ({drill['correct_option']}).")

    print("\n" + "=" * 72)
    print("### Lectura y Análisis Táctico")
    print(drill["analysis"])
    print(f"\n### Línea Recomendada — {drill['best_line_title']}")
    print(f"Tipo: {drill['line_type']}\n")

    print("### Ejecución en Master Duel (Paso a Paso de Cliente)")
    for s in drill.get("steps", []):
        print(f"\nPASO {s['step']} — [{s['action']}]")
        print(f"Carta: {s['card_es']} / {s['card_name']} (Passcode: {s['passcode']})")
        print(f"![{s['card_name']}](https://images.ygoprodeck.com/images/cards/{s['passcode']}.jpg)")
        print(f"Dónde: {s['where']}")
        print("Procedimiento en Cliente:")
        for idx, inp in enumerate(s["inputs"], 1):
            print(f"  {idx}. {inp}")
        print(f"Resultado: {s['result']}")
        print(f"Timing: {s['timing']}")
        print(f"Notas de Chain: {s['chain_notes']}")

    print("\n" + "-" * 72)
    print(f"End Board Esperado:\n{drill['end_board']}")
    print(f"Follow-up Próximo Turno:\n{drill['follow_up']}")
    print(f"Plan B (Anti-Handtraps):\n{drill['plan_b']}")
    print(f"Principio Táctico:\n\"{drill['principle']}\"")
    print("=" * 72)
    return True

def search_card_tool(db: CoachDatabase):
    print("\n--- CONSULTA DE CARTA VERIFICADA (Passcodes & Artes Oficiales) ---")
    query = input("Nombre (ES/EN) o Passcode de la carta: ").strip()
    if not query:
        return
    card = db.get_card(query)
    if card:
        print("\n" + db.format_card_visual(card))
    else:
        print(f"[ERROR] No se encontró ninguna carta que coincida con '{query}'.")

def deck_doctor_tool(db: CoachDatabase):
    print("\n--- DECK DOCTOR (Optimización de Proporciones y Ratios Meta) ---")
    print("Introduce las cartas clave de tu baraja separadas por comas (o presiona Enter para usar lista por defecto):")
    raw = input("> ").strip()
    if raw:
        cards = [c.strip() for c in raw.split(",") if c.strip()]
    else:
        cards = [
            "WANTED: Seeker of Sinful Spoils", "Snake-Eye Ash", "Snake-Eye Poplar",
            "Bonfire", "Diabellstar the Black Witch", "Called by the Grave",
            "Ash Blossom & Joyous Spring", "Maxx \"C\"", "Infinite Impermanence"
        ]
    
    doc = DeckDoctor(db)
    result = doc.analyze_deck(cards)
    print("\n" + "=" * 72)
    print(f"DIAGNÓSTICO DEL MAZO ({result['total_cards']} cartas analizadas):")
    print(f" • Starters identificados: {result['starters_count']}")
    print(f" • Non-Engine / Interrupciones: {result['handtraps_count']}")
    print("\n3 FORTALEZAS:")
    for s in result["strengths"]:
        print(f" [+] {s}")
    print("\n3 DEBILIDADES / AGUJEROS:")
    for w in result["weaknesses"]:
        print(f" [-] {w}")
    print("\nAJUSTES RECOMENDADOS (+X / -X):")
    for r in result["recommendations"]:
        print(f" [!] {r}")
    print("=" * 72)

def main():
    db = CoachDatabase()
    while True:
        print_header()
        print("  [1] Iniciar Sesión de Drills Competitivos (Drills 1 a 8)")
        print("  [2] Ejecutar un Drill Específico (1 a 8)")
        print("  [3] Consultor de Cartas (Passcode exacto, Arte YGOPRODeck, Efectos ES/EN)")
        print("  [4] Deck Doctor (Análisis de Ratios y Ajustes Competitivos)")
        print("  [5] Diseñador de Diagrama de Campo ASCII")
        print("  [6] Salir")
        print()
        opc = input("Selecciona una opción (1-6): ").strip()

        if opc == "1":
            for i in range(len(DRILLS)):
                run_drill(i, db)
                if i < len(DRILLS) - 1:
                    cont = input("\n¿Avanzar al siguiente Drill? (S/N): ").strip().upper()
                    if cont != "S":
                        break
            input("\nPresiona Enter para volver al menú...")
        elif opc == "2":
            num = input("Número de Drill a ejecutar (1-8): ").strip()
            if num.isdigit() and 1 <= int(num) <= len(DRILLS):
                run_drill(int(num) - 1, db)
            else:
                print("Número no válido.")
            input("\nPresiona Enter para continuar...")
        elif opc == "3":
            search_card_tool(db)
            input("\nPresiona Enter para continuar...")
        elif opc == "4":
            deck_doctor_tool(db)
            input("\nPresiona Enter para continuar...")
        elif opc == "5":
            print("\n" + BoardDiagram.render())
            input("\nPresiona Enter para continuar...")
        elif opc == "6":
            print("Cerrando sesión de Coaching...")
            break

if __name__ == "__main__":
    main()
