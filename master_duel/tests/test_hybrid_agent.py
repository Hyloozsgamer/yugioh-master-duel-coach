"""
Test Hybrid Agent Integration (Gemini Vision + Solo Playbooks + Fast OpenCV Engine)
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def test_imports():
    print("Testing imports...")
    from master_duel.brain.gemini_brain import MasterDuelBrain
    from master_duel.decision.duel_engine import MasterDuelEngine
    from master_duel.farming.solo_playbooks import SoloPlaybookEngine
    from master_duel.core.cognitive_loop import CognitiveLoop
    print("✓ All modules imported successfully.")

def test_initialization():
    print("Testing initialization of Hybrid Agent components...")
    from master_duel.brain.gemini_brain import MasterDuelBrain
    from master_duel.farming.solo_playbooks import SoloPlaybookEngine
    
    brain = MasterDuelBrain()
    print(f"✓ GeminiBrain initialized. Model pool: {brain.models_pool}, has_api_key: {bool(brain.api_key)}")
    
    playbooks = SoloPlaybookEngine()
    stalled = playbooks.register_state("TEST_STATE", 128.0)
    print(f"✓ Playbooks initialized. Watchdog stall test (tick 1): {stalled}")
    
    for _ in range(3):
        stalled = playbooks.register_state("TEST_STATE", 128.0)
    print(f"✓ Watchdog stall trigger test (after repeats): {stalled}")
    assert stalled is True, "Watchdog should declare stall after 3 identical ticks"
    playbooks.reset_stall_counter()
    print("✓ Watchdog stall counter reset.")

if __name__ == "__main__":
    test_imports()
    test_initialization()
    print("\n[SUCCESS] Hybrid Agent verification passed 100%!")
