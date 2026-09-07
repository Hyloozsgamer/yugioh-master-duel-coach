"""
Unit & Integration tests for Yu-Gi-Oh! Master Duel Cognitive Autonomous AI.
Validates:
1. CardDatabase and DeckAnalyzer
2. GameState & StateTracker
3. LegalActionGenerator & Strategic StateEvaluator
4. BeamSearchPlanner (optimal tactical lines & suicide attack prevention)
5. ActionVerifier (OBSERVE -> ACT -> VERIFY contract)
6. Farming Strategy Evaluator
"""
import unittest
import copy

from master_duel.database.card_database import CardDatabase
from master_duel.deck.deck_analyzer import DeckAnalyzer
from master_duel.state.game_state import GameState, ZoneCard, DuelPhase, CardPosition
from master_duel.state.state_tracker import StateTracker
from master_duel.planning.legal_actions import LegalActionGenerator, ActionType, DuelAction
from master_duel.planning.evaluator import StateEvaluator
from master_duel.planning.beam_search import BeamSearchPlanner
from master_duel.planning.chain_manager import ChainManager
from master_duel.execution.verifier import ActionVerifier
from master_duel.farming.farming_strategy import FarmingStrategy

class TestCognitiveAgent(unittest.TestCase):

    def setUp(self):
        self.card_db = CardDatabase()
        self.deck_analyzer = DeckAnalyzer(self.card_db)
        self.evaluator = StateEvaluator(self.card_db)
        self.planner = BeamSearchPlanner(self.card_db)
        self.verifier = ActionVerifier()

    def test_01_card_database_lookup(self):
        """Verifies card knowledge database attributes and roles."""
        card = self.card_db.get_card_by_name("Gladiator Beast Bestiari")
        self.assertIsNotNone(card)
        self.assertEqual(card.atk, 1500)
        self.assertEqual(card.def_stat, 800)
        self.assertIn("removal", card.roles)

        unknown = self.card_db.get_card_by_name("NonExistentCard_12345")
        self.assertIsNone(unknown)

    def test_02_deck_analysis(self):
        """Verifies starter, extender, searcher, and boss classification."""
        sample_deck = [
            "Gladiator Beast Bestiari",
            "Gladiator Beast Darius",
            "Gladiator Beast Gyzarus",
            "Gladiator Proving Ground",
            "Mystical Space Typhoon"
        ]
        analysis = self.deck_analyzer.analyze_deck(sample_deck)
        self.assertIn("Gladiator Proving Ground", analysis.searchers)
        self.assertIn("Gladiator Beast Gyzarus", analysis.boss_monsters)

    def test_03_no_suicide_attacks(self):
        """
        CRITICAL TACTICAL TEST:
        A monster with 600 ATK should NEVER attack a 2000 ATK monster.
        """
        state = GameState(
            phase=DuelPhase.BATTLE,
            is_player_turn=True,
            player_lp=8000,
            opponent_lp=4000
        )
        # Player has 600 ATK monster
        state.monster_zones["M3"] = ZoneCard(
            zone_id="M3",
            card_name="WeakMonster",
            atk=600,
            position=CardPosition.FACEUP_ATTACK,
            can_attack=True
        )
        # Opponent has 2000 ATK monster
        state.opp_monster_zones["OPP_M3"] = ZoneCard(
            zone_id="OPP_M3",
            card_name="StrongOpponentMonster",
            atk=2000,
            position=CardPosition.FACEUP_ATTACK
        )

        gen = LegalActionGenerator(self.card_db)
        battle_actions = gen.get_legal_actions(state)

        # Ensure NO attack action was generated targeting the 2000 ATK monster
        attack_actions = [a for a in battle_actions if a.action_type == ActionType.ATTACK_MONSTER]
        self.assertEqual(len(attack_actions), 0, "Bot must not attempt suicide attacks against stronger monsters!")

        # Instead, bot should choose to enter Main Phase 2
        m2_actions = [a for a in battle_actions if a.action_type == ActionType.ENTER_MAIN2]
        self.assertTrue(len(m2_actions) > 0, "Bot should generate transition to Main 2 when combat is disadvantageous")

    def test_04_beam_search_planning(self):
        """Verifies multi-step tactical line generation."""
        state = GameState(
            turn=1,
            phase=DuelPhase.MAIN1,
            is_player_turn=True,
            hand=["Gladiator Beast Bestiari", "Mystical Space Typhoon"]
        )
        best_line, confidence = self.planner.plan_best_line(state)
        self.assertTrue(len(best_line) > 0)
        self.assertEqual(best_line[0].action_type, ActionType.NORMAL_SUMMON)
        self.assertEqual(best_line[0].card_name, "Gladiator Beast Bestiari")
        self.assertGreater(confidence, 0.6)

    def test_05_action_verifier(self):
        """Verifies OBSERVE -> ACT -> VERIFY post-condition."""
        state_before = GameState(
            turn=1,
            phase=DuelPhase.MAIN1,
            hand=["Gladiator Beast Darius"]
        )
        state_after = copy.deepcopy(state_before)
        state_after.hand.clear()
        state_after.monster_zones["M3"] = ZoneCard(
            zone_id="M3",
            card_name="Gladiator Beast Darius",
            atk=1700
        )
        state_after.normal_summon_used = True

        action = DuelAction(
            action_type=ActionType.NORMAL_SUMMON,
            card_name="Gladiator Beast Darius",
            target_zone="M3"
        )

        res = self.verifier.verify(action, state_before, state_after)
        self.assertTrue(res.success)
        self.assertFalse(res.recovery_needed)

    def test_06_chain_manager(self):
        """Verifies strategic chain activation logic."""
        cm = ChainManager(self.card_db)
        state = GameState(is_player_turn=True)
        # Searchers should activate
        self.assertTrue(cm.should_activate_in_chain("Gladiator Proving Ground", state))

    def test_07_farming_strategy(self):
        """Verifies Solo Mode efficiency calculation."""
        fs = FarmingStrategy()
        target = fs.select_best_target()
        self.assertIsNotNone(target)
        self.assertGreater(target.efficiency_score, 0.0)

if __name__ == "__main__":
    unittest.main()
