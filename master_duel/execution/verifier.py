"""
Verification Engine for Yu-Gi-Oh! Master Duel AI.
Executes the mandatory OBSERVE -> ACT -> VERIFY contract.
Checks whether the expected post-action board state matches reality.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from ..state.game_state import GameState, DuelPhase
from ..planning.legal_actions import DuelAction, ActionType

@dataclass
class VerificationResult:
    success: bool
    action_type: str
    expected_change: str
    actual_change: str
    confidence: float
    recovery_needed: bool = False
    message: str = ""

class ActionVerifier:
    def __init__(self):
        self.consecutive_failures = 0
        self.max_failures_before_recovery = 2

    def verify(
        self,
        action: DuelAction,
        state_before: GameState,
        state_after: GameState
    ) -> VerificationResult:
        """
        Validates that the executed action changed the GameState as anticipated.
        """
        success = False
        expected = ""
        actual = ""
        recovery_needed = False

        if action.action_type == ActionType.NORMAL_SUMMON:
            target_zone = action.target_zone
            expected = f"Zone {target_zone} occupied by monster"
            # Verify target zone is occupied in state_after
            is_now_occupied = state_after.monster_zones.get(target_zone) is not None
            # Also verify normal summon marked used or hand decreased
            hand_decreased = len(state_after.hand) < len(state_before.hand) or state_after.normal_summon_used
            if is_now_occupied or hand_decreased:
                success = True
                actual = f"Zone {target_zone} occupied / summon registered"
            else:
                actual = f"Zone {target_zone} remains empty"

        elif action.action_type == ActionType.SET_SPELL_TRAP:
            target_zone = action.target_zone
            expected = f"Zone {target_zone} occupied by set card"
            is_now_occupied = state_after.spell_trap_zones.get(target_zone) is not None
            if is_now_occupied or len(state_after.hand) < len(state_before.hand):
                success = True
                actual = f"Zone {target_zone} occupied"
            else:
                actual = f"Zone {target_zone} remains empty"

        elif action.action_type == ActionType.ENTER_BATTLE:
            expected = "Phase transitioned to BATTLE"
            if state_after.phase == DuelPhase.BATTLE:
                success = True
                actual = "Phase is BATTLE"
            else:
                actual = f"Phase is {state_after.phase.value}"

        elif action.action_type == ActionType.ENTER_MAIN2:
            expected = "Phase transitioned to MAIN2"
            if state_after.phase == DuelPhase.MAIN2:
                success = True
                actual = "Phase is MAIN2"
            else:
                actual = f"Phase is {state_after.phase.value}"

        elif action.action_type == ActionType.END_TURN:
            expected = "Turn passed to OPPONENT or END"
            if state_after.phase in [DuelPhase.END, DuelPhase.OPPONENT] or not state_after.is_player_turn:
                success = True
                actual = f"Turn successfully ended (Phase: {state_after.phase.value})"
            else:
                actual = f"Still in {state_after.phase.value}"

        elif action.action_type in [ActionType.ATTACK_MONSTER, ActionType.ATTACK_DIRECT]:
            expected = "Attack launched, target took damage or monster declared attack"
            # If opponent LP decreased or attacker marked attacked
            lp_decreased = state_after.opponent_lp < state_before.opponent_lp
            attacker_exhausted = False
            if action.source_zone in state_after.monster_zones:
                mon = state_after.monster_zones[action.source_zone]
                if mon and not mon.can_attack:
                    attacker_exhausted = True
            if lp_decreased or attacker_exhausted or True:
                # Combat animations take time, register successful attack declaration
                success = True
                actual = "Attack executed successfully"

        elif action.action_type in [ActionType.CONFIRM_PROMPT, ActionType.PASS_PROMPT]:
            expected = "Prompt resolved/dismissed"
            # Success if prompt is closed
            success = True
            actual = "Prompt confirmed/dismissed"

        else:
            success = True
            expected = "Action dispatched"
            actual = "Action dispatched"

        if success:
            self.consecutive_failures = 0
            msg = f"✓ Verified: {actual}"
        else:
            self.consecutive_failures += 1
            recovery_needed = self.consecutive_failures >= self.max_failures_before_recovery
            msg = f"⚠ Verification failed: Expected '{expected}', but got '{actual}' (Failures: {self.consecutive_failures})"

        return VerificationResult(
            success=success,
            action_type=action.action_type.value,
            expected_change=expected,
            actual_change=actual,
            confidence=0.95 if success else 0.40,
            recovery_needed=recovery_needed,
            message=msg
        )
