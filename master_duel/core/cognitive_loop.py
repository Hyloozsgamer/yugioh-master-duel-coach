"""
Cognitive Loop Orchestrator for Yu-Gi-Oh! Master Duel AI.
Executes the master cycle:
OBSERVE -> INTERPRET -> CONOCER -> PLANIFICAR -> ACTUAR -> VERIFICAR -> APRENDER
Exclusively for Solo Mode / PvE Auto-Farming.
"""
import time
import copy
import cv2
import numpy as np
from typing import Optional, Dict, Any

from master_duel.config.settings import AgentConfig
from master_duel.core.safety import SafetyManager
from master_duel.ui.real_time_console import RealTimeConsole
from master_duel.vision.screen_capture import ScreenCapture
from master_duel.vision.board_detector import BoardDetector
from master_duel.vision.ui_recognizer import UIRecognizer
from master_duel.vision.card_recognizer import CardRecognizer
from master_duel.vision.game_vision import GameVision
from master_duel.database.card_database import CardDatabase
from master_duel.deck.deck_analyzer import DeckAnalyzer
from master_duel.state.game_state import GameState, DuelPhase
from master_duel.state.state_tracker import StateTracker
from master_duel.planning.beam_search import BeamSearchPlanner
from master_duel.planning.legal_actions import DuelAction, ActionType
from master_duel.execution.action_executor import ActionExecutor
from master_duel.execution.verifier import ActionVerifier
from master_duel.farming.solo_farming_engine import SoloFarmingEngine
from master_duel.vision.state_detector import StateDetector, MasterDuelState
from master_duel.core.anti_pvp_shield import AntiPvPShield
from master_duel.learning.replay_recorder import ReplayRecorder
from master_duel.learning.learning_system import LearningSystem
from master_duel.input.input_controller import InputController
from master_duel.brain.gemini_brain import MasterDuelBrain
from master_duel.decision.duel_engine import MasterDuelEngine
from master_duel.farming.solo_playbooks import SoloPlaybookEngine

class CognitiveLoop:
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig.load()
        
        # 1. Core & Safety
        self.safety = SafetyManager(config=self.config)
        self.ui_console = RealTimeConsole()
        
        # 2. Hardware, Input & Vision
        self.screen_cap = ScreenCapture(game_title="masterduel")
        self.input_ctrl = InputController(screen_capture=self.screen_cap)
        self.board_detector = BoardDetector()
        self.ui_recognizer = UIRecognizer()
        self.card_recognizer = CardRecognizer()
        self.state_detector = StateDetector()
        self.anti_pvp = AntiPvPShield(input_ctrl=self.input_ctrl)

        # 2b. YOLO11 Vision Layer — detección visual en tiempo real
        self.game_vision = GameVision(
            confidence=0.45,
            fps=10,
            on_frame=self._on_yolo_frame,
        )
        self._yolo_action_pending: bool = False
        
        # 3. Knowledge & State
        self.card_db = CardDatabase()
        self.deck_analyzer = DeckAnalyzer(card_db=self.card_db)
        self.state_tracker = StateTracker(card_db=self.card_db)
        
        # 4. Reasoning & Execution
        self.planner = BeamSearchPlanner(
            card_db=self.card_db,
            time_limit_sec=min(0.5, self.config.max_decision_time_ms / 1000.0)
        )
        self.executor = ActionExecutor(
            input_ctrl=self.input_ctrl,
            board_detector=self.board_detector,
            ui_recognizer=self.ui_recognizer,
            screen_cap=self.screen_cap
        )
        self.verifier = ActionVerifier()
        
        # 5. Farming & Learning
        self.farming_engine = SoloFarmingEngine(
            input_ctrl=self.input_ctrl,
            screen_cap=self.screen_cap,
            ui_recognizer=self.ui_recognizer
        )
        self.replay_recorder = ReplayRecorder()
        self.learning_system = LearningSystem()

        # 6. Agente Híbrido: Motor Táctico + Cerebro Gemini Vision + Playbooks Anti-Bucle
        self.gemini_brain = MasterDuelBrain()
        self.duel_engine = MasterDuelEngine(
            input_ctrl=self.input_ctrl,
            brain=self.gemini_brain,
            learning_system=self.learning_system,
            replay_recorder=self.replay_recorder
        )
        self.playbook_engine = SoloPlaybookEngine(input_ctrl=self.input_ctrl)

        self.running = False
        self.verification_status = "READY"

    def _on_yolo_frame(self, yolo_frame) -> None:
        """Callback invocado por GameVision cada vez que YOLO procesa un frame."""
        pass

    def start(self):
        """
        Starts the cognitive autonomous loop.
        """
        self.running = True
        self.replay_recorder.start_new_match()

        # Iniciar YOLO11 vision en background
        self.game_vision.start()

        print("[CognitiveLoop] Autonomous Agent started in SOLO MODE.")
        print(f"[CognitiveLoop] YOLO11 Vision: {'✓ Activo' if self.game_vision.yolo_ready else '⚠ Sin modelo'}")
        print("[CognitiveLoop] Controls: F8=PAUSE | F9=RESUME | F10=EMERGENCY STOP\n")

        try:
            while self.running and not self.safety.is_stopped:
                # Check Safety: pause / stop flags
                if self.safety.is_paused:
                    time.sleep(0.5)
                    continue

                self._step()
                time.sleep(0.25)

        except KeyboardInterrupt:
            print("\n[CognitiveLoop] Agent stopped by user.")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        self.game_vision.stop()
        self.safety.stop()
        self.replay_recorder.record_result("ABORTED")

    def _resolve_yolo_buttons(self, frame) -> bool:
        """
        Resuelve botones emergentes cuando hay un diálogo o prompt confirmado.
        Solo actúa con alta confianza (> 0.88) para evitar falsos positivos.
        """
        if not self.game_vision.yolo_ready:
            return False

        yolo_frame = self.game_vision.get_latest()
        if yolo_frame is None:
            return False

        # Solo aceptar botones con alta confianza (> 0.88)
        valid_buttons = [d for d in yolo_frame.buttons() if d.confidence >= 0.88]
        if not valid_buttons:
            return False

        # Priorizar botones en el centro o zona inferior derecha (área típica de prompts de MD)
        best_btn = max(valid_buttons, key=lambda d: d.confidence)
        cx, cy = best_btn.center_norm
        
        # Validar que no sea un clic en los bordes extremos
        if 0.15 < cx < 0.85 and 0.20 < cy < 0.85:
            print(f"[YOLO] 🎯 {best_btn.class_name} confirmado ({best_btn.confidence:.2f}) → clic en ({cx:.2f}, {cy:.2f})")
            self.input_ctrl.click_relative(cx, cy, delay=0.25)
            time.sleep(0.3)
            return True

        return False

    def _step(self):
        frame = self.screen_cap.capture()
        if frame is None:
            time.sleep(0.5)
            return

        # ----------------------------------------------------
        # 1. CLASIFICACIÓN DE ESTADO Y ESCUDO ANTI-PVP
        # ----------------------------------------------------
        screen_state, conf, meta = self.state_detector.detect(frame)

        # ----------------------------------------------------
        # 1.0 VIGILANTE ANTI-BUCLE (WATCHDOG AI RESCUE)
        # ----------------------------------------------------
        is_in_duel = screen_state in (
            MasterDuelState.DUEL_PLAYER_TURN,
            MasterDuelState.DUEL_OPPONENT_TURN,
            MasterDuelState.DUEL_CHAIN_PROMPT,
            MasterDuelState.DUEL_TARGET_SELECT
        )
        if not is_in_duel:
            frame_mean = float(np.mean(frame))
            is_stalled = self.playbook_engine.register_state(screen_state.value, frame_mean)
            if is_stalled:
                print(f"🚨 [ANTI-BUCLE] Estancamiento detectado en '{screen_state.value}'. Consultando a Gemini Vision...")
                self.ui_console.render(
                    state=self.state_tracker.current_state,
                    ai_step="WATCHDOG_AI",
                    status="RECOVERING",
                    current_action="Bucle detectado -> Rescate con Gemini Vision",
                    verification_status="Emergency AI Consult"
                )
                decision = self.gemini_brain.consult(
                    frame,
                    current_state=screen_state.value,
                    extra_context="URGENT ANTI-LOOP: The bot is looping on this exact menu. Identify which button to click to move forward."
                )
                if decision:
                    self.duel_engine._execute_decision(decision)
                    self.playbook_engine.reset_stall_counter()
                    time.sleep(1.0)
                    return

        # 1.1 ESCUDO ANTI-PVP ESTRICTO (Prioridad Absoluta)
        if screen_state == MasterDuelState.PVP_WARNING:
            self.anti_pvp.enforce_safe_exit()
            self.safety.pause(f"Anti-PvP Shield: {meta.get('reason', 'PvP/Ranked detectado')}. Bot detenido para proteger tu cuenta.")
            self.ui_console.render(
                state=self.state_tracker.current_state,
                ai_step="ANTI_PVP_SHIELD",
                status="PAUSED",
                pause_reason="Ranked / PvP Detected & Blocked",
                verification_status="Emergency Exit Executed"
            )
            time.sleep(1.0)
            return

        # 1.2 NAVEGACIÓN EN MENÚ PRINCIPAL -> MODO SOLO (Clic estricto en SOLO, nunca en DUEL)
        if screen_state == MasterDuelState.MAIN_MENU:
            self.ui_console.render(
                state=self.state_tracker.current_state,
                ai_step="MENU_SOLO",
                current_action="Entering SOLO Mode (Click 0.105, 0.366)",
                verification_status="Navigating to Solo"
            )
            self.input_ctrl.click_relative(0.105, 0.366, delay=0.4)
            time.sleep(2.0)
            return

        # 1.2.2 ENTRAR A LA PUERTA ACTIVA DESDE EL HUB DE MODO SOLO (Clic en Last Played 0.78, 0.40)
        if screen_state == MasterDuelState.SOLO_GATE_SELECT:
            self.ui_console.render(
                state=self.state_tracker.current_state,
                ai_step="SOLO_GATE_SELECT",
                current_action="Entering active gate (Click Last Played 0.78, 0.40)",
                verification_status="Selecting Solo Gate"
            )
            self.input_ctrl.click_relative(0.78, 0.40, delay=0.6)
            time.sleep(1.8)
            return

        # 1.3 PANTALLA DE RESULTADOS DE DUELO (Victoria / Derrota / Recompensas)
        if screen_state == MasterDuelState.DUEL_RESULT:
            # 1. Detectar si el duelo concluyó en victoria o derrota
            duel_res = self.ui_recognizer.detect_duel_result(frame) or "UNKNOWN"
            if duel_res == "victory":
                outcome_str = "WIN"
            elif duel_res == "defeat":
                outcome_str = "LOSS"
            else:
                outcome_str = "COMPLETED"

            self.ui_console.render(
                state=self.state_tracker.current_state,
                ai_step="RESULTS",
                current_action=f"Match result: {outcome_str}. Claiming rewards...",
                verification_status="Match Concluded"
            )

            # Avanzar pantallas de recompensas
            self.farming_engine.handle_match_results()
            self.replay_recorder.record_result(outcome_str)

            # 2. Análisis y aprendizaje estratégico post-duelo
            self.learning_system.analyze_match(self.replay_recorder.match_log, result=outcome_str)

            # 3. Limpieza automática de archivos temporales de depuración y replays antiguos
            self.learning_system.clean_temporary_files()

            self.replay_recorder.start_new_match()
            time.sleep(1.5)
            return

        # 1.4 PROGRESIÓN SECUENCIAL EN MODO SOLO (1x1: Scenario -> Practice -> Duel -> Goal -> Ramas)
        if screen_state in (
            MasterDuelState.SOLO_GATE_VIEW,
            MasterDuelState.SOLO_CHAPTER_DETAIL,
            MasterDuelState.SOLO_CUTSCENE
        ):
            step_idx = self.farming_engine.progress_data.get("current_step_index", 0)
            self.ui_console.render(
                state=self.state_tracker.current_state,
                ai_step="SOLO_FARMING",
                current_action=f"Solo Mode Step {step_idx + 1}/7 ({screen_state.value})",
                verification_status="Advancing 1x1 Sequence"
            )
            self.farming_engine.advance_solo_step(screen_state, meta, frame=frame)
            time.sleep(1.0)
            return

        # 1.5 MODALES Y DIÁLOGOS EMERGENTES
        if screen_state == MasterDuelState.MODAL_POPUP:
            self.farming_engine.advance_solo_step(screen_state, meta, frame=frame)
            time.sleep(0.8)
            return

        # 1.6 PANTALLA DE TÍTULO
        if screen_state == MasterDuelState.TITLE_SCREEN:
            self.input_ctrl.click_relative(0.50, 0.50, delay=1.0)
            time.sleep(2.0)
            return

        # 1.7 SI NO ES UN DUELO ACTIVO, NO EJECUTAR ACCIONES DE TABLERO
        is_in_duel = screen_state in (
            MasterDuelState.DUEL_PLAYER_TURN,
            MasterDuelState.DUEL_OPPONENT_TURN,
            MasterDuelState.DUEL_CHAIN_PROMPT,
            MasterDuelState.DUEL_TARGET_SELECT
        )
        if not is_in_duel:
            self.ui_console.render(
                state=self.state_tracker.current_state,
                ai_step="STANDBY",
                current_action=f"Outside duel ({screen_state.value}). Standing by...",
                verification_status="Awaiting Solo Duel"
            )
            time.sleep(0.8)
            return

        # ----------------------------------------------------
        # 2. DECISIÓN DE DUELO HÍBRIDA (OpenCV Local + Gemini Vision)
        # ----------------------------------------------------
        self.ui_console.render(
            state=self.state_tracker.current_state,
            ai_step="DUEL_EVAL",
            candidate_lines=[],
            chosen_action=None,
            confidence=0.95,
            verification_status="Evaluating Duel Board"
        )

        # A. Motor Táctico de Duelo (Acciones locales instantáneas + Consulta Gemini con cooldown)
        handled = self.duel_engine.handle_duel_step(frame, screen_state, meta)
        if handled:
            self.playbook_engine.reset_stall_counter()
            self.safety.notify_action()
            self.ui_console.render(
                state=self.state_tracker.current_state,
                ai_step="DUEL_ACTION",
                current_action="Duel action executed",
                verification_status="Action completed"
            )
            time.sleep(0.4)
            return
        else:
            time.sleep(0.3)
            return
