"""
Solo Farming Engine for Yu-Gi-Oh! Master Duel AI.
Automates Solo Mode progression strictly 1-by-1 in sequence:
Scenario -> Practice -> Duel -> Goal -> Locked branches (100% Gate Completion).
Visually detects completed nodes (yellow checkmark ✔) so it NEVER repeats completed nodes.
Advances from left to right across Solo gates and persists progression to disk.
"""

import os
import json
import time
import cv2
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from master_duel.input.input_controller import InputController
from master_duel.vision.screen_capture import ScreenCapture
from master_duel.vision.ui_recognizer import UIRecognizer
from master_duel.vision.state_detector import MasterDuelState

PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "solo_progress.json")

# Visual specifications for nodes in a gate (coordinates normalized 0.0 - 1.0)
NODES_SPECS = [
    {"name": "Scenario",    "type": "scenario",  "click": (0.18, 0.53), "check": (0.215, 0.605)},
    {"name": "Practice",    "type": "practice",  "click": (0.31, 0.53), "check": (0.342, 0.605)},
    {"name": "Duel",        "type": "duel",      "click": (0.44, 0.53), "check": (0.472, 0.605)},
    {"name": "Goal",        "type": "scenario",  "click": (0.56, 0.53), "check": (0.592, 0.605)},
    {"name": "Locked",      "type": "gate_lock", "click": (0.56, 0.28), "check": (0.592, 0.355)},
    {"name": "BranchDuel1", "type": "duel",      "click": (0.69, 0.28), "check": (0.722, 0.355)},
    {"name": "BranchDuel2", "type": "duel",      "click": (0.81, 0.28), "check": (0.842, 0.355)},
]


class SoloFarmingEngine:
    def __init__(
        self,
        input_ctrl: InputController,
        screen_cap: ScreenCapture,
        ui_recognizer: UIRecognizer
    ):
        self.input_ctrl = input_ctrl
        self.screen_cap = screen_cap
        self.ui_recognizer = ui_recognizer
        self.duels_completed: int = 0
        self.duels_won: int = 0
        self.progress_data: Dict[str, Any] = self._load_progress()
        self._last_action_time: float = 0.0
        self.current_target_name: str = "Duel"

    def _load_progress(self) -> Dict[str, Any]:
        """Loads persistent progression from disk."""
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[SoloEngine] Warning loading progress: {e}")
        return {
            "current_gate": "The Tribe of the Abyssal Waters",
            "completed_gates": [],
            "completed_nodes": {},
            "current_step_index": 0,
            "last_updated": datetime.now().isoformat()
        }

    def _save_progress(self):
        """Saves current progression to disk."""
        self.progress_data["last_updated"] = datetime.now().isoformat()
        try:
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.progress_data, f, indent=2)
            print(f"[SoloEngine] Progress persisted to {PROGRESS_FILE}")
        except Exception as e:
            print(f"[SoloEngine] Error saving progress: {e}")

    @property
    def current_gate(self) -> str:
        return self.progress_data.get("current_gate", "The Tribe of the Abyssal Waters")

    def scan_visual_nodes_status(self, frame: np.ndarray) -> Tuple[List[str], Optional[Dict[str, Any]]]:
        """
        Scans the gate tree frame for yellow completion checkmarks (✔).
        Returns: (completed_node_names, next_uncompleted_target_node)
        """
        if frame is None or frame.size == 0:
            return [], NODES_SPECS[0]

        h, w = frame.shape[:2]
        completed: List[str] = []
        next_target: Optional[Dict[str, Any]] = None

        for node in NODES_SPECS:
            chk = node.get("check")
            if chk is None:
                # Locked node or gate with no checkmark
                if next_target is None and len(completed) >= 4:
                    next_target = node
                continue

            chk_x, chk_y = chk
            cx = int(chk_x * w)
            cy = int(chk_y * h)
            crop = frame[max(0, cy - 20):min(h, cy + 20), max(0, cx - 20):min(w, cx + 20)]
            if crop.size == 0:
                continue

            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            # Detección de círculo amarillo (Scenario/Practice), naranja (Duel Loaner) o azul (Duel My Deck)
            gold_orange = cv2.inRange(hsv, np.array([5, 90, 90]), np.array([40, 255, 255]))
            blue_clear = cv2.inRange(hsv, np.array([90, 90, 90]), np.array([130, 255, 255]))
            done_mask = gold_orange + blue_clear
            is_done = np.count_nonzero(done_mask) > 120

            if is_done:
                completed.append(node["name"])
            elif next_target is None:
                next_target = node

        # Update persistent data with verified completed nodes
        gate = self.current_gate
        if "completed_nodes" not in self.progress_data:
            self.progress_data["completed_nodes"] = {}
        self.progress_data["completed_nodes"][gate] = completed

        if next_target:
            self.current_target_name = next_target["name"]
            # Find index in specs
            for idx, spec in enumerate(NODES_SPECS):
                if spec["name"] == next_target["name"]:
                    self.progress_data["current_step_index"] = idx
                    break
        self._save_progress()

        return completed, next_target

    def mark_gate_completed(self, gate_name: str):
        """Marks a gate 100% completed and prepares transition to next gate."""
        if gate_name not in self.progress_data["completed_gates"]:
            self.progress_data["completed_gates"].append(gate_name)
        print(f"[SoloEngine] 🎉 GATE '{gate_name}' 100% COMPLETED!")
        self.progress_data["current_step_index"] = 0
        self._save_progress()

    def advance_solo_step(self, screen_state: MasterDuelState, meta: Dict[str, Any], frame: Optional[np.ndarray] = None) -> bool:
        """
        Executes the exact next step according to the 1-by-1 sequence.
        Returns: True if action was executed.
        """
        now = time.time()
        if now - self._last_action_time < 0.8:
            return False

        # ---------------------------------------------------------
        # A. CINEMÁTICA / DIÁLOGO DE HISTORIA (Scenario Cutscene)
        # ---------------------------------------------------------
        if screen_state == MasterDuelState.SOLO_CUTSCENE:
            has_skip = meta.get("has_skip_visible", False)
            if not has_skip:
                print("[SoloEngine] Cutscene active -> Opening menu (0.936, 0.907)")
                self.input_ctrl.click_relative(0.936, 0.907, delay=0.4)
            else:
                print("[SoloEngine] Cutscene menu open -> Clicking SKIP (0.92, 0.62)")
                self.input_ctrl.click_relative(0.92, 0.62, delay=0.5)
            self._last_action_time = now
            return True

        # ---------------------------------------------------------
        # B. MODAL DE CONFIRMACIÓN O TUTORIAL (CLOSE / YES / OK)
        # ---------------------------------------------------------
        if screen_state == MasterDuelState.MODAL_POPUP:
            click_target = meta.get("click", None)
            if click_target:
                print(f"[SoloEngine] Modal detected -> Clicking designated target {click_target}")
                self.input_ctrl.click_relative(click_target[0], click_target[1], delay=0.5)
            else:
                print("[SoloEngine] Modal detected -> Clicking YES / Confirm / Close")
                self.input_ctrl.click_relative(0.40, 0.77, delay=0.3)   # CLOSE button on Event / Appreciation popups
                self.input_ctrl.click_relative(0.50, 0.915, delay=0.3)  # CLOSE button on tutorial
                self.input_ctrl.click_relative(0.59, 0.60, delay=0.3)   # YES button on skip
                self.input_ctrl.click_relative(0.50, 0.73, delay=0.3)   # OK button on reward dialogs
                self.input_ctrl.click_relative(0.50, 0.65, delay=0.3)   # OK button on generic popups
            self._last_action_time = now
            return True

        # ---------------------------------------------------------
        # C. PANEL DE DETALLE DE CAPÍTULO ABIERTO (Botón Play/Duel)
        # ---------------------------------------------------------
        if screen_state == MasterDuelState.SOLO_CHAPTER_DETAIL:
            btn_color = meta.get("btn_color", "green")
            can_play = meta.get("can_play", True)
            print(f"[SoloEngine] Chapter detail panel open (button: {btn_color}, can_play: {can_play})")
            
            # 1. Asegurar pestaña Loaner seleccionada (0.75, 0.31)
            self.input_ctrl.click_relative(0.75, 0.31, delay=0.3)
            time.sleep(0.3)

            # 2. Clic en botón Play verde inferior derecho (0.816, 0.846)
            self.input_ctrl.click_relative(0.816, 0.846, delay=0.6)
            time.sleep(0.5)

            # 3. Confirmar inicio de duelo si aparece popup
            self.input_ctrl.click_relative(0.50, 0.75, delay=0.4)
            self.input_ctrl.click_relative(0.60, 0.70, delay=0.4)
            self._last_action_time = now
            return True

        # ---------------------------------------------------------
        # D. VISTA DEL ÁRBOL DE LA PUERTA (Selección Visual del siguiente nodo 1x1)
        # ---------------------------------------------------------
        if screen_state == MasterDuelState.SOLO_GATE_VIEW:
            if frame is None:
                frame = self.screen_cap.capture()

            completed_nodes, next_target = self.scan_visual_nodes_status(frame)
            print(f"[SoloEngine] Visually verified completed: {completed_nodes}")

            if next_target is None:
                print(f"[SoloEngine] All nodes in '{self.current_gate}' 100% completed! Returning to Gate Menu...")
                self.mark_gate_completed(self.current_gate)
                self.input_ctrl.click_relative(0.035, 0.08, delay=1.0)
                self._last_action_time = now
                return True

            target_name = next_target["name"]
            tx, ty = next_target["click"]
            print(f"[SoloEngine] NEXT UNCOMPLETED TARGET: '{target_name}' at ({tx}, {ty}) -> Clicking to open detail panel...")
            self.input_ctrl.click_relative(tx, ty, delay=0.7)
            self._last_action_time = now
            return True

        return False

    def handle_match_results(self) -> bool:
        """
        Handles post-match Victory / Defeat screens, claims rewards, and advances node.
        Returns: True if duel concluded and dismissed, False if still in duel.
        """
        frame = self.screen_cap.capture()
        if frame is None:
            return False

        res = self.ui_recognizer.detect_duel_result(frame)
        if res in ("victory", "defeat"):
            if res == "victory":
                self.duels_won += 1
            self.duels_completed += 1

            print(f"[SoloEngine] Match result concluded ({res}). Claiming rewards...")
            # Click screen to advance reward animations
            for _ in range(5):
                self.input_ctrl.click_relative(0.50, 0.75, delay=0.5)

            return True

        return False
