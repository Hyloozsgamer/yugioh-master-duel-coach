"""
Beam Search & Planning Engine for Yu-Gi-Oh! Master Duel AI.
Explores multi-step tactical lines and selects the optimal path without infinite recursion.
"""
import copy
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass

from ..state.game_state import GameState, ZoneCard, CardPosition, DuelPhase
from ..database.card_database import CardDatabase
from .legal_actions import DuelAction, ActionType, LegalActionGenerator
from .evaluator import StateEvaluator

@dataclass
class SearchNode:
    state: GameState
    actions_taken: List[DuelAction]
    score: float
    depth: int

class BeamSearchPlanner:
    def __init__(
        self,
        card_db: CardDatabase,
        beam_width: int = 4,
        max_depth: int = 3,
        time_limit_sec: float = 0.35
    ):
        self.card_db = card_db
        self.action_gen = LegalActionGenerator(card_db)
        self.evaluator = StateEvaluator(card_db)
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.time_limit_sec = time_limit_sec

    def plan_best_line(
        self,
        current_state: GameState,
        is_prompt_open: bool = False
    ) -> Tuple[List[DuelAction], float]:
        """
        Executes bounded Beam Search to determine the best tactical line of actions.
        Returns: (best_actions_list, confidence)
        """
        start_time = time.time()
        
        # Immediate prompt check
        initial_actions = self.action_gen.get_legal_actions(current_state, is_prompt_open=is_prompt_open)
        if not initial_actions:
            return [], 0.5
            
        if is_prompt_open or current_state.is_chain_active:
            # For quick prompts, evaluate single step
            best_act = max(initial_actions, key=lambda a: a.priority)
            return [best_act], 0.95

        initial_node = SearchNode(
            state=current_state,
            actions_taken=[],
            score=self.evaluator.evaluate(current_state),
            depth=0
        )

        current_beam = [initial_node]
        best_overall_node = initial_node

        for depth in range(self.max_depth):
            if time.time() - start_time > self.time_limit_sec:
                break

            candidates: List[SearchNode] = []

            for node in current_beam:
                actions = self.action_gen.get_legal_actions(node.state)
                if not actions:
                    continue

                for action in actions:
                    if time.time() - start_time > self.time_limit_sec:
                        break

                    simulated_state = self._simulate_action(node.state, action)
                    score = self.evaluator.evaluate(simulated_state) + action.priority
                    
                    new_node = SearchNode(
                        state=simulated_state,
                        actions_taken=node.actions_taken + [action],
                        score=score,
                        depth=depth + 1
                    )
                    candidates.append(new_node)

            if not candidates:
                break

            # Sort candidates descending by heuristic score
            candidates.sort(key=lambda n: n.score, reverse=True)
            current_beam = candidates[:self.beam_width]

            if current_beam[0].score > best_overall_node.score:
                best_overall_node = current_beam[0]

        best_line = best_overall_node.actions_taken
        if not best_line and initial_actions:
            initial_actions.sort(key=lambda a: a.priority, reverse=True)
            best_line = [initial_actions[0]]

        # Calculate normalized confidence
        confidence = min(1.0, max(0.6, 0.75 + (len(best_line) * 0.05)))
        return best_line, confidence

    def _simulate_action(self, state: GameState, action: DuelAction) -> GameState:
        """
        Fast forward state simulation without deep mutation.
        """
        sim = copy.deepcopy(state)
        
        if action.action_type == ActionType.NORMAL_SUMMON:
            sim.normal_summon_used = True
            card_info = self.card_db.get_card_by_name(action.card_name)
            atk = card_info.atk if card_info else 1500
            def_stat = card_info.def_stat if card_info else 1000
            
            sim.monster_zones[action.target_zone] = ZoneCard(
                zone_id=action.target_zone,
                card_name=action.card_name,
                atk=atk,
                def_stat=def_stat,
                position=CardPosition.FACEUP_ATTACK
            )
            if action.card_name in sim.hand:
                sim.hand.remove(action.card_name)

        elif action.action_type == ActionType.SET_SPELL_TRAP:
            sim.spell_trap_zones[action.target_zone] = ZoneCard(
                zone_id=action.target_zone,
                card_name=action.card_name,
                position=CardPosition.FACEDOWN_SET
            )
            if action.card_name in sim.hand:
                sim.hand.remove(action.card_name)

        elif action.action_type == ActionType.ATTACK_MONSTER:
            if action.source_zone in sim.monster_zones:
                attacker = sim.monster_zones[action.source_zone]
                if attacker:
                    attacker.can_attack = False
            if action.target_zone in sim.opp_monster_zones:
                defender = sim.opp_monster_zones[action.target_zone]
                if defender and attacker and attacker.atk > defender.atk:
                    # Opponent monster destroyed
                    damage = attacker.atk - defender.atk
                    sim.opponent_lp = max(0, sim.opponent_lp - damage)
                    sim.opp_monster_zones[action.target_zone] = None

        elif action.action_type == ActionType.ATTACK_DIRECT:
            if action.source_zone in sim.monster_zones:
                attacker = sim.monster_zones[action.source_zone]
                if attacker:
                    attacker.can_attack = False
                    sim.opponent_lp = max(0, sim.opponent_lp - attacker.atk)

        elif action.action_type == ActionType.ENTER_BATTLE:
            sim.phase = DuelPhase.BATTLE

        elif action.action_type == ActionType.ENTER_MAIN2:
            sim.phase = DuelPhase.MAIN2

        elif action.action_type == ActionType.END_TURN:
            sim.phase = DuelPhase.END
            sim.is_player_turn = False

        return sim
