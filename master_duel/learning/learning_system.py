"""
Learning and Experience System for Yu-Gi-Oh! Master Duel AI.
Analyzes post-duel replays, identifies tactical mistakes, and refines heuristics without uncontrolled code modification.
Includes automated disk cleanup of temporary screenshots and bloated replay logs.
"""
import os
import glob
import json
import time
from typing import Dict, Any, List, Optional

class LearningSystem:
    def __init__(self, memory_file: Optional[str] = None):
        if memory_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            memory_file = os.path.join(base_dir, "database", "learned_heuristics.json")
        self.memory_file = memory_file
        self.knowledge: Dict[str, Any] = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        default_data = {
            "version": 2.0,
            "summary_stats": {
                "total_duels": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0
            },
            "winning_patterns": [],
            "mistakes_to_avoid": [],
            "active_tactical_rules": [
                "Always transition to Battle Phase on Turn 2+ if player controls attack-ready monsters.",
                "Normal Summon the highest playable ATK monster in Main Phase 1.",
                "Do not activate optional effects that discard unless having immediate combo followup."
            ],
            "recent_matches": []
        }

        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "winning_patterns" in data:
                        return data
                    elif isinstance(data, list):
                        # Migrate legacy list format
                        default_data["recent_matches"] = data[-20:]
                        return default_data
            except Exception as e:
                print(f"[LearningSystem] Warning loading memory: {e}. Resetting to structured format.")
        return default_data

    def _save_memory(self):
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.knowledge, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[LearningSystem] Error saving heuristics: {e}")

    def analyze_match(self, match_log: Dict[str, Any], result: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes a finished duel for strategic success factors or root causes of defeat.
        Updates persistent knowledge base in learned_heuristics.json.
        """
        actual_result = (result or match_log.get("result", "UNKNOWN")).upper()
        actions = match_log.get("actions_executed", [])
        match_id = match_log.get("match_id", f"duel_{int(time.time())}")
        turns_count = len(set(a.get("turn", 1) for a in actions)) or 1

        stats = self.knowledge.setdefault("summary_stats", {"total_duels": 0, "wins": 0, "losses": 0, "win_rate": 0.0})
        stats["total_duels"] += 1

        analysis_report = {
            "match_id": match_id,
            "timestamp": time.time(),
            "result": actual_result,
            "turns": turns_count,
            "findings": [],
            "applied_rule": None
        }

        if "WIN" in actual_result or actual_result == "VICTORY":
            stats["wins"] += 1
            print(f"[VICTORIA] [LearningSystem] Victoria confirmada en {match_id}. Extrayendo motivos del exito...")

            # Extract successful plays
            winning_reasons = []
            monsters_summoned = [
                a.get("chosen_action", {}).get("card_name") or a.get("card_name")
                for a in actions
                if a.get("chosen_action", {}).get("action_type") in ("NORMAL_SUMMON", "SPECIAL_SUMMON", "POSITION_SELECT")
            ]
            if monsters_summoned:
                unique_monsters = list(dict.fromkeys(filter(None, monsters_summoned)))
                winning_reasons.append(f"Monsters deployed successfully: {', '.join(unique_monsters)}")

            battle_actions = [a for a in actions if a.get("phase") in ("BATTLE", "BATTLE_PHASE") or a.get("chosen_action", {}).get("action_type") == "ATTACK"]
            if battle_actions:
                winning_reasons.append(f"Offensive battle execution ({len(battle_actions)} battle actions)")
            else:
                winning_reasons.append("Board presence control and opponent surrender/attrition")

            full_reason = " | ".join(winning_reasons)
            analysis_report["findings"].append(full_reason)

            # Store winning pattern
            self.knowledge.setdefault("winning_patterns", []).append({
                "match_id": match_id,
                "timestamp": time.time(),
                "turns_to_win": turns_count,
                "strategy": full_reason
            })
            # Keep top 15 patterns
            self.knowledge["winning_patterns"] = self.knowledge["winning_patterns"][-15:]

        elif "LOSS" in actual_result or actual_result == "DEFEAT":
            stats["losses"] += 1
            print(f"[DERROTA] [LearningSystem] Derrota en {match_id}. Diagnosticando causa raiz...")

            # Diagnostics:
            # 1. Did we have monsters on field but never attacked?
            had_monsters = any(
                len(a.get("monsters", [])) > 0 or a.get("chosen_action", {}).get("monsters")
                for a in actions
            )
            entered_battle = any(
                a.get("phase") in ("BATTLE", "BATTLE_PHASE") or a.get("chosen_action", {}).get("action_type") == "ATTACK"
                for a in actions
            )
            
            # 2. Did we fail to normal summon?
            summoned_any = any(
                a.get("chosen_action", {}).get("action_type") in ("NORMAL_SUMMON", "SPECIAL_SUMMON", "POSITION_SELECT")
                for a in actions
            )

            # 3. Action verification failures
            failed_verifications = [a for a in actions if not a.get("verified", True)]

            diagnosis = []
            suggested_rule = None

            if had_monsters and not entered_battle and turns_count >= 2:
                diagnosis.append("Causa: Salto pasivo de la Fase de Batalla teniendo monstruos disponibles.")
                suggested_rule = "NUNCA pulsar End Phase en el modal si hay monstruos en campo y es Turno 2+; pulsar siempre BATTLE PHASE (0.78, 0.58)."
            elif not summoned_any and turns_count >= 2:
                diagnosis.append("Causa: No se invocó ningún monstruo en los primeros 2 turnos.")
                suggested_rule = "Priorizar invocación normal de cualquier monstruo jugable de la mano en Main Phase 1."
            elif len(failed_verifications) > 3:
                diagnosis.append(f"Causa: Múltiples ({len(failed_verifications)}) fallos de verificación de acciones / clics.")
                suggested_rule = "Aumentar tiempo de espera tras clics en invocación y animaciones de campo."
            else:
                diagnosis.append("Causa: Desventaja de ATK contra monstruos oponentes o pérdida rápida de LP.")
                suggested_rule = "Priorizar monstruos con mayor ATK o colocar monstruos en Posición de Defensa."

            analysis_report["findings"] = diagnosis
            analysis_report["applied_rule"] = suggested_rule

            self.knowledge.setdefault("mistakes_to_avoid", []).append({
                "match_id": match_id,
                "timestamp": time.time(),
                "issue": diagnosis[0] if diagnosis else "Desconocido",
                "corrective_rule": suggested_rule
            })
            self.knowledge["mistakes_to_avoid"] = self.knowledge["mistakes_to_avoid"][-15:]

            # Add to active rules if not already present
            if suggested_rule and suggested_rule not in self.knowledge.setdefault("active_tactical_rules", []):
                self.knowledge["active_tactical_rules"].append(suggested_rule)
                # Keep top 6 rules
                self.knowledge["active_tactical_rules"] = self.knowledge["active_tactical_rules"][-6:]

        # Recalculate Win Rate
        total = stats["wins"] + stats["losses"]
        stats["win_rate"] = round((stats["wins"] / total * 100.0), 1) if total > 0 else 0.0

        # Save match to recent matches history (last 20)
        self.knowledge.setdefault("recent_matches", []).append(analysis_report)
        self.knowledge["recent_matches"] = self.knowledge["recent_matches"][-20:]

        self._save_memory()
        print(f"[LearningSystem] Aprendizaje guardado: {stats['wins']}V - {stats['losses']}D ({stats['win_rate']}% WR)")
        return analysis_report

    def clean_temporary_files(self) -> Dict[str, Any]:
        """
        Deletes unnecessary temporary screenshots, debug PNGs, and old bloated replay files.
        Keeps database, trained weights, and core configuration intact.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        workspace_dir = os.path.dirname(base_dir)

        deleted_files = 0
        reclaimed_bytes = 0

        # 1. Clean root debug screenshots
        temp_patterns = [
            os.path.join(workspace_dir, "after_*.png"),
            os.path.join(workspace_dir, "live_*.png"),
            os.path.join(workspace_dir, "step*.png"),
            os.path.join(workspace_dir, "yolo_test_*.jpg"),
            os.path.join(workspace_dir, "crop_*.png"),
            os.path.join(workspace_dir, "current_live_screen.png"),
            os.path.join(workspace_dir, "game_screen_*.png"),
            os.path.join(workspace_dir, "deck_*.png"),
            os.path.join(workspace_dir, "master_duel_check_*.png"),
            os.path.join(workspace_dir, "master_duel_live_*.png"),
        ]

        for pat in temp_patterns:
            for fpath in glob.glob(pat):
                try:
                    size = os.path.getsize(fpath)
                    os.remove(fpath)
                    deleted_files += 1
                    reclaimed_bytes += size
                except Exception:
                    pass

        # 2. Prune old replay JSON files in master_duel/logs/replays/ (keep 2 latest)
        replay_dir = os.path.join(base_dir, "logs", "replays")
        if os.path.exists(replay_dir):
            replay_files = glob.glob(os.path.join(replay_dir, "*.json"))
            # Sort by modification time ascending (oldest first)
            replay_files.sort(key=lambda x: os.path.getmtime(x))
            
            # If more than 2, delete the older ones
            if len(replay_files) > 2:
                to_delete = replay_files[:-2]
                for fpath in to_delete:
                    try:
                        size = os.path.getsize(fpath)
                        os.remove(fpath)
                        deleted_files += 1
                        reclaimed_bytes += size
                    except Exception:
                        pass

        reclaimed_mb = round(reclaimed_bytes / (1024 * 1024), 2)
        print(f"[AutoCleanup] Limpieza completada: {deleted_files} archivos eliminados ({reclaimed_mb} MB liberados en disco).")

        return {
            "deleted_files": deleted_files,
            "reclaimed_mb": reclaimed_mb
        }

    def get_tactical_guidelines(self) -> str:
        """
        Returns active learned rules and winning patterns to feed directly into decision prompts.
        """
        rules = self.knowledge.get("active_tactical_rules", [])
        if not rules:
            return ""
        guidelines = ["LEARNED TACTICAL RULES FROM PREVIOUS DUELS:"]
        for r in rules:
            guidelines.append(f"- {r}")
        return "\n".join(guidelines)
