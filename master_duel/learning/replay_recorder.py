"""
Replay and Debug Logger for Yu-Gi-Oh! Master Duel AI.
Records complete structured history of duel states, tactical lines, physical actions, and match outcomes.
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from ..state.game_state import GameState
from ..planning.legal_actions import DuelAction

class ReplayRecorder:
    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(base_dir, "logs", "replays")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.current_match_id = f"duel_{int(time.time())}"
        self.match_log: Dict[str, Any] = {
            "match_id": self.current_match_id,
            "start_time": time.time(),
            "turns": [],
            "actions_executed": [],
            "result": "IN_PROGRESS"
        }

    def start_new_match(self):
        self.current_match_id = f"duel_{int(time.time())}"
        self.match_log = {
            "match_id": self.current_match_id,
            "start_time": time.time(),
            "turns": [],
            "actions_executed": [],
            "result": "IN_PROGRESS"
        }

    def record_step(
        self,
        turn: int,
        phase: str,
        state: GameState,
        candidate_lines: List[DuelAction],
        chosen_action: Optional[DuelAction],
        verification_passed: bool
    ):
        step_entry = {
            "timestamp": time.time(),
            "turn": turn,
            "phase": phase,
            "player_lp": state.player_lp,
            "opp_lp": state.opponent_lp,
            "hand": state.hand,
            "monsters": [m.to_dict() for m in state.get_player_monsters()],
            "candidate_lines": [a.to_dict() for a in candidate_lines[:3]],
            "chosen_action": chosen_action.to_dict() if chosen_action else None,
            "verified": verification_passed
        }
        self.match_log["actions_executed"].append(step_entry)

    def record_action(
        self,
        action_type: str,
        card_name: str = "",
        phase: str = "MAIN1",
        turn: int = 1,
        details: Optional[Dict[str, Any]] = None
    ):
        """Registra una acción directa realizada en el duelo."""
        step_entry = {
            "timestamp": time.time(),
            "turn": turn,
            "phase": phase,
            "chosen_action": {
                "action_type": action_type,
                "card_name": card_name,
                **(details or {})
            },
            "verified": True
        }
        self.match_log["actions_executed"].append(step_entry)

    def record_result(self, result: str):
        """
        result: 'WIN', 'LOSS', or 'ABORTED'
        """
        self.match_log["result"] = result
        self.match_log["end_time"] = time.time()
        self.match_log["duration_sec"] = round(self.match_log["end_time"] - self.match_log["start_time"], 2)

        file_path = os.path.join(self.output_dir, f"{self.current_match_id}_{result.lower()}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.match_log, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ReplayRecorder] Error saving replay: {e}")
