"""
Yu-Gi-Oh! Master Duel - Cognitive Autonomous AI Agent
Architecture: OBSERVE -> INTERPRET -> CONOCER -> PLANIFICAR -> ACTUAR -> VERIFICAR -> APRENDER
Exclusively for Solo Mode / PvE Auto-Farming.
"""

import os
import sys
import time
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from master_duel.config.settings import AgentConfig
from master_duel.core.cognitive_loop import CognitiveLoop

def main():
    parser = argparse.ArgumentParser(description="Yu-Gi-Oh! Master Duel Cognitive AI Agent")
    parser.add_argument("--mode", type=str, default="SOLO", choices=["SOLO", "DUEL", "OBSERVATION"],
                        help="Operating mode: SOLO (full auto-farm), DUEL (plays current duel), OBSERVATION (no mouse actions)")
    parser.add_argument("--profile", type=str, default="gladiator_beast", help="Deck profile name")
    parser.add_argument("--auto", action="store_true", help="Start immediately without menu")
    args = parser.parse_args()

    print("=" * 68)
    print("  YU-GI-OH! MASTER DUEL - AGENTE AUTONOMO COGNITIVO (SOLO MODE / PVE)")
    print("=" * 68)
    print(" Arquitectura Cognitiva:")
    print("   OBSERVAR -> INTERPRETAR -> CONOCER -> PLANIFICAR -> ACTUAR -> VERIFICAR -> APRENDER")
    print("\n Controles de Seguridad (Global Hotkeys):")
    print("   [F8]  Pausar Bot (Control Humano)")
    print("   [F9]  Reanudar Bot")
    print("   [F10] Parada de Emergencia Inmediata")
    print("=" * 68)

    if not args.auto:
        print("\n [1] MODO SOLO AUTO-FARM (Completar Puertas, Capítulos y Recompensas)")
        print(" [2] ASISTENTE COGNITIVO DE DUELO (Juega partidas en curso)")
        print(" [3] MODO OBSERVACIÓN (Solo monitorea el tablero y muestra planes)")
        print(" [4] Salir")
        print("=" * 68)

        choice = input("\nElige una opción (1-4): ").strip()
        if choice == "1":
            mode_name = "SOLO"
        elif choice == "2":
            mode_name = "DUEL"
        elif choice == "3":
            mode_name = "OBSERVATION"
        else:
            print("Saliendo...")
            return
    else:
        mode_name = args.mode

    config = AgentConfig.load()
    config.mode = mode_name
    if args.profile:
        config.deck_profile = args.profile

    print(f"\n[INICIANDO] Modo: {config.mode} | Perfil Baraja: {config.deck_profile} | SafeMode: {config.safe_mode}")
    agent = CognitiveLoop(config=config)
    agent.start()

if __name__ == "__main__":
    main()
