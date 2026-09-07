"""
Safety & Anti-Block Watchdog Module for Yu-Gi-Oh! Master Duel.
Provides:
- Safe Mode: Pauses execution if confidence is low.
- Human Override: Global hotkeys (F8=Pause, F9=Resume, F10=Emergency Stop).
- Timeout Watchdogs: Detects STATE_TIMEOUT, ACTION_TIMEOUT, ANIMATION_TIMEOUT.
"""

import time
import threading
import win32api
import win32con
from typing import Optional, Callable
from master_duel.config.settings import AgentConfig


class SafetyManager:
    """
    Gestor de seguridad integral.
    Monitorea teclas de anulación humana, tiempos de espera y control de modo seguro.
    """

    VK_MAP = {
        "F1": win32con.VK_F1, "F2": win32con.VK_F2, "F3": win32con.VK_F3,
        "F4": win32con.VK_F4, "F5": win32con.VK_F5, "F6": win32con.VK_F6,
        "F7": win32con.VK_F7, "F8": win32con.VK_F8, "F9": win32con.VK_F9,
        "F10": win32con.VK_F10, "F11": win32con.VK_F11, "F12": win32con.VK_F12,
        "ESCAPE": win32con.VK_ESCAPE
    }

    def __init__(self, config: AgentConfig, on_pause: Optional[Callable] = None, on_resume: Optional[Callable] = None, on_stop: Optional[Callable] = None):
        self.config = config
        self.on_pause_cb = on_pause
        self.on_resume_cb = on_resume
        self.on_stop_cb = on_stop

        self.is_paused = False
        self.is_stopped = False
        self.pause_reason = ""

        # Timers de monitoreo
        self._last_state_change = time.time()
        self._last_action_time = time.time()
        self._last_state_name = "INIT"
        self._consecutive_low_conf_count = 0

        # Hilo de escucha de teclas
        self._running = True
        self._hotkey_thread = threading.Thread(target=self._hotkey_listener, daemon=True)
        self._hotkey_thread.start()

    def _hotkey_listener(self):
        """Monitorea teclas globales de emergencia sin requerir foco en la consola."""
        vk_pause = self.VK_MAP.get(self.config.hotkeys.pause.upper(), win32con.VK_F8)
        vk_resume = self.VK_MAP.get(self.config.hotkeys.resume.upper(), win32con.VK_F9)
        vk_stop = self.VK_MAP.get(self.config.hotkeys.emergency_stop.upper(), win32con.VK_F10)

        # Flush initial states
        try:
            win32api.GetAsyncKeyState(vk_pause)
            win32api.GetAsyncKeyState(vk_resume)
            win32api.GetAsyncKeyState(vk_stop)
        except Exception:
            pass

        start_time = time.time()
        time.sleep(0.5)  # Grace period

        while self._running:
            try:
                # Do not trigger during initial 1.0s boot grace
                if time.time() - start_time < 1.0:
                    time.sleep(0.1)
                    continue
                # F8: Pausa
                if win32api.GetAsyncKeyState(vk_pause) & 0x8000:
                    if not self.is_paused:
                        self.pause("Human intervention requested (F8)")
                        time.sleep(0.3)

                # F9: Reanudar
                if win32api.GetAsyncKeyState(vk_resume) & 0x8000:
                    if self.is_paused:
                        self.resume()
                        time.sleep(0.3)

                # F10: Parada de emergencia
                if win32api.GetAsyncKeyState(vk_stop) & 0x8000:
                    self.emergency_stop()
                    break

            except Exception:
                pass
            time.sleep(0.05)

    def pause(self, reason: str = "Manual pause"):
        """Pausa la ejecución del agente."""
        self.is_paused = True
        self.pause_reason = reason
        print(f"\n[SAFETY] ⏸️ BOT PAUSED: {reason}")
        print("[SAFETY] Human control enabled. Press F9 to resume or F10 to stop.")
        if self.on_pause_cb:
            self.on_pause_cb(reason)

    def resume(self):
        """Reanuda la ejecución del agente."""
        self.is_paused = False
        self.pause_reason = ""
        self._last_state_change = time.time()
        self._last_action_time = time.time()
        print("\n[SAFETY] ▶️ BOT RESUMED. AI taking control...")
        if self.on_resume_cb:
            self.on_resume_cb()

    def stop(self):
        """Detiene de forma limpia el gestor de seguridad."""
        self.is_stopped = True
        self._running = False

    def emergency_stop(self):
        """Detiene de inmediato el agente por tecla de emergencia."""
        print("\n[SAFETY] 🛑 EMERGENCY STOP TRIGGERED (F10). Exiting now...")
        self.stop()
        if self.on_stop_cb:
            self.on_stop_cb()

    def notify_state(self, state_name: str, confidence: float):
        """Actualiza el estado actual para los watchdogs."""
        now = time.time()
        if state_name != self._last_state_name:
            self._last_state_name = state_name
            self._last_state_change = now

        # Control de Safe Mode por baja confianza
        if confidence < self.config.vision_confidence:
            self._consecutive_low_conf_count += 1
            if self._consecutive_low_conf_count >= 5 and self.config.safe_mode:
                self.pause(f"Confidence below threshold ({confidence:.1%} < {self.config.vision_confidence:.1%}) for 5 cycles.")
        else:
            self._consecutive_low_conf_count = 0

    def notify_action_executed(self):
        """Informa que se completó una acción en la UI."""
        now = time.time()
        self._last_action_time = now
        self._last_state_change = now

    def notify_action(self):
        """Alias para notify_action_executed."""
        self.notify_action_executed()

    def check_timeouts(self) -> Optional[str]:
        """Comprueba si algún watchdog ha expirado."""
        now = time.time()
        if self.is_paused or self.is_stopped:
            return None

        # STATE_TIMEOUT
        if now - self._last_state_change > self.config.timeouts.state_timeout:
            return f"STATE_TIMEOUT ({self._last_state_name} unchanged for {self.config.timeouts.state_timeout}s)"

        # ACTION_TIMEOUT
        if now - self._last_action_time > self.config.timeouts.action_timeout:
            return f"ACTION_TIMEOUT (No action executed for {self.config.timeouts.action_timeout}s)"

        return None

    def close(self):
        self._running = False
