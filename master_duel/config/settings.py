"""Configuration manager for Master Duel Autonomous Agent."""
import os
import json
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class TimeoutsConfig:
    state_timeout: float = 25.0
    action_timeout: float = 12.0
    animation_timeout: float = 4.0
    ui_timeout: float = 15.0


@dataclass
class HotkeysConfig:
    pause: str = "F8"
    resume: str = "F9"
    emergency_stop: str = "F10"


@dataclass
class AgentConfig:
    mode: str = "SOLO"
    auto_farm: bool = True
    safe_mode: bool = True
    max_decision_time_ms: int = 5000
    vision_confidence: float = 0.85
    allow_human_intervention: bool = True
    debug: bool = True
    deck_profile: str = "gladiator_beast"
    timeouts: TimeoutsConfig = field(default_factory=TimeoutsConfig)
    hotkeys: HotkeysConfig = field(default_factory=HotkeysConfig)

    @classmethod
    def load(cls, config_path: str = None) -> "AgentConfig":
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        
        if not os.path.exists(config_path):
            return cls()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            timeouts_data = data.get("timeouts", {})
            timeouts = TimeoutsConfig(
                state_timeout=timeouts_data.get("stateTimeout", 25.0),
                action_timeout=timeouts_data.get("actionTimeout", 12.0),
                animation_timeout=timeouts_data.get("animationTimeout", 4.0),
                ui_timeout=timeouts_data.get("uiTimeout", 15.0)
            )

            hotkeys_data = data.get("hotkeys", {})
            hotkeys = HotkeysConfig(
                pause=hotkeys_data.get("pause", "F8"),
                resume=hotkeys_data.get("resume", "F9"),
                emergency_stop=hotkeys_data.get("emergencyStop", "F10")
            )

            return cls(
                mode=data.get("mode", "SOLO"),
                auto_farm=data.get("autoFarm", True),
                safe_mode=data.get("safeMode", True),
                max_decision_time_ms=data.get("maxDecisionTime", 5000),
                vision_confidence=data.get("visionConfidence", 0.85),
                allow_human_intervention=data.get("allowHumanIntervention", True),
                debug=data.get("debug", True),
                deck_profile=data.get("deckProfile", "gladiator_beast"),
                timeouts=timeouts,
                hotkeys=hotkeys
            )
        except Exception as e:
            print(f"[WARN] Error loading config.json: {e}. Using defaults.")
            return cls()
