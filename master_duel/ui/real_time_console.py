"""
Real-Time AI HUD Console for Yu-Gi-Oh! Master Duel.
Renders an elegant ASCII/Unicode HUD showing real-time cognition:
- Current Duel state, Gate, Turn, Phase, LP.
- Hand and Field composition.
- AI Thinking pipeline & simulated candidate lines.
- Best chosen line, action, and verification status.
- Confidence progress bar.
"""

import os
import sys
import time
from typing import List, Dict, Any, Optional


class RealTimeConsole:
    """Consola visual interactiva en tiempo real para el agente."""

    def __init__(self):
        self.enabled = True
        self._last_render_time = 0.0

    def render(
        self,
        state: Any = None,
        ai_step: str = "OBSERVE",
        candidate_lines: Any = None,
        chosen_action: Any = None,
        confidence: float = 0.95,
        verification_status: str = "IDLE",
        status: str = "RUNNING",
        mode: str = "SOLO FARM",
        gate: str = "Solo Gate",
        duel: str = "Practice",
        pause_reason: str = "",
        **kwargs
    ):
        now = time.time()
        # Limitar render a máximo 5 veces por segundo para evitar parpadeo
        if now - self._last_render_time < 0.18:
            return
        self._last_render_time = now

        # Extract from state if provided
        if state is not None:
            turn = getattr(state, "turn", 1)
            phase_val = getattr(state, "phase", "MAIN 1")
            phase = phase_val.value if hasattr(phase_val, "value") else str(phase_val)
            player_lp = getattr(state, "player_lp", 8000)
            opponent_lp = getattr(state, "opponent_lp", 8000)
            hand_cards = getattr(state, "hand", [])
            
            p_monsters = state.get_player_monsters() if hasattr(state, "get_player_monsters") else []
            player_monsters = [f"{m.card_name}({m.atk})" for m in p_monsters]
            
            st_zones = getattr(state, "spell_trap_zones", {})
            player_spells = [s.card_name for s in st_zones.values() if s is not None]
            
            opp_m = state.get_opponent_monsters() if hasattr(state, "get_opponent_monsters") else []
            opponent_monsters = [f"{m.card_name}({m.atk})" for m in opp_m]
            
            thinking_steps = [f"Step: {ai_step}", f"Confidence: {int(confidence * 100)}%", f"Hand: {len(hand_cards)} cards"]
            best_lines = [str(a) for a in candidate_lines] if candidate_lines else ["Searching optimal tactical lines..."]
            current_action = str(chosen_action) if chosen_action else f"{ai_step} in progress"
        else:
            turn = kwargs.get("turn", 1)
            phase = kwargs.get("phase", "MAIN 1")
            player_lp = kwargs.get("player_lp", 8000)
            opponent_lp = kwargs.get("opponent_lp", 8000)
            hand_cards = kwargs.get("hand_cards", [])
            player_monsters = kwargs.get("player_monsters", [])
            player_spells = kwargs.get("player_spells", [])
            opponent_monsters = kwargs.get("opponent_monsters", [])
            thinking_steps = kwargs.get("thinking_steps", [ai_step])
            best_lines = kwargs.get("best_lines", ["Calculating optimal lines..."])
            current_action = kwargs.get("current_action", f"{ai_step}...")

        hand_cards = hand_cards or []
        player_monsters = player_monsters or []
        player_spells = player_spells or []
        opponent_monsters = opponent_monsters or []
        thinking_steps = thinking_steps or ["Observing board state"]
        best_lines = best_lines or ["Calculating optimal lines..."]

        # Barra de confianza
        bar_len = 20
        filled_len = int(round(bar_len * max(0.0, min(1.0, confidence))))
        conf_bar = "█" * filled_len + "░" * (bar_len - filled_len)
        conf_pct = int(confidence * 100)

        # Formato de status
        status_display = status
        if status == "PAUSED":
            status_display = f"PAUSED ({pause_reason})" if pause_reason else "PAUSED [Human Control]"

        lines = [
            "┌────────────────────────────────────────────────────────────────────────┐",
            f"│  ⚔️  YU-GI-OH! MASTER DUEL - COGNITIVE AUTONOMOUS AI                   │",
            "├────────────────────────────────────────────────────────────────────────┤",
            f"│  STATUS: {status_display:<40} MODE: {mode:<18}│",
            f"│  GATE:   {gate:<24} DUEL:  {duel:<23}│",
            f"│  TURN:   {turn:<5} PHASE: {phase:<16} LP: [{player_lp} vs {opponent_lp}]        │",
            "├────────────────────────────────────────────────────────────────────────┤",
            "│  📦 ESTADO DEL TABLERO:                                                │",
            f"│  • Mano ({len(hand_cards)}): {', '.join(hand_cards[:4]):<58}│",
            f"│  • Monstruos Propios: {', '.join(player_monsters[:3]) if player_monsters else 'Ninguno':<47}│",
            f"│  • Magias/Trampas:    {', '.join(player_spells[:3]) if player_spells else 'Ninguna':<47}│",
            f"│  • Monstruos Rivales: {', '.join(opponent_monsters[:3]) if opponent_monsters else 'Ninguno':<47}│",
            "├────────────────────────────────────────────────────────────────────────┤",
            "│  🧠 AI COGNITION PIPELINE:                                             │",
        ]

        for step in thinking_steps[-3:]:
            lines.append(f"│  ✓ {step:<67}│")

        lines.append("├────────────────────────────────────────────────────────────────────────┤")
        lines.append("│  🎯 LÍNEA TÁCTICA ELEGIDA:                                             │")
        for i, b_line in enumerate(best_lines[:3], 1):
            lines.append(f"│  {i}. {b_line:<67}│")

        lines.extend([
            "├────────────────────────────────────────────────────────────────────────┤",
            f"│  ACCION:    {current_action:<57}│",
            f"│  VERIFICA:  {verification_status:<57}│",
            f"│  CONFIANZA: [{conf_bar}] {conf_pct:>3}%                           │",
            "├────────────────────────────────────────────────────────────────────────┤",
            "│  CONTROLES: [F8 = PAUSAR]  [F9 = REANUDAR]  [F10 = PARADA DE EMERGENCIA]│",
            "└────────────────────────────────────────────────────────────────────────┘"
        ])

        # Render con limpieza de cursor ANSI y compatibilidad Windows CP1252/UTF-8
        output = "\n".join(lines)
        try:
            sys.stdout.write("\033[H" + output + "\n")
            sys.stdout.flush()
        except UnicodeEncodeError:
            safe_output = output.encode("ascii", errors="replace").decode("ascii")
            try:
                sys.stdout.write("\033[H" + safe_output + "\n")
                sys.stdout.flush()
            except Exception:
                pass
        except Exception:
            pass
