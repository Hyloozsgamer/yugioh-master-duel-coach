"""
Input Controller Module for Yu-Gi-Oh! Master Duel
Manejo nativo de ratón y teclado con Win32 (pywin32).
Movimiento suave humanizado con curvas de Bézier cúbicas y aceleración natural.
Cero saltos instantáneos robóticos para máxima seguridad e inmersión.
"""

import time
import math
import random
import win32api
import win32gui
import win32con
import win32process
from typing import Optional, Tuple
from master_duel.vision.screen_capture import GameWindow


class InputController:
    """
    Controlador de entrada humanizado Win32 para Master Duel.
    - Trayectorias curvas suaves con micro-aceleración (Bézier).
    - Variación natural en tiempos de pulsación (jitter temporal).
    - Restricción de clics al área interna de la ventana de juego.
    """

    def __init__(self, screen_capture=None):
        self._screen_capture = screen_capture
        self._last_click_pos = (0, 0)

    def _get_window(self) -> Optional[GameWindow]:
        if self._screen_capture:
            if not self._screen_capture.window:
                self._screen_capture.find_game_window()
            return self._screen_capture.window
        return None

    def bring_to_front(self):
        """Asegura que la ventana de Master Duel esté activa y en primer plano."""
        gw = self._get_window()
        if not gw or not win32gui.IsWindow(gw.hwnd):
            return
        try:
            if win32gui.IsIconic(gw.hwnd):
                win32gui.ShowWindow(gw.hwnd, win32con.SW_RESTORE)
                time.sleep(0.08)

            fg_hwnd = win32gui.GetForegroundWindow()
            if fg_hwnd != gw.hwnd:
                # Pulsar y soltar tecla ALT para desbloquear permiso de primer plano en Windows
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                win32gui.ShowWindow(gw.hwnd, win32con.SW_RESTORE)
                win32gui.BringWindowToTop(gw.hwnd)
                win32gui.SetForegroundWindow(gw.hwnd)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

    def to_screen_coords(self, x: float, y: float, normalized: bool = False) -> Tuple[int, int]:
        """Convierte coordenadas normalizadas o relativas a coordenadas de pantalla."""
        gw = self._get_window()
        if not gw:
            return int(x), int(y)

        if normalized:
            screen_x = int(gw.x + x * gw.width)
            screen_y = int(gw.y + y * gw.height)
        else:
            screen_x = int(gw.x + x)
            screen_y = int(gw.y + y)

        # Prevenir hacer clics fuera de la ventana del juego o en la barra de título
        screen_x = max(gw.x + 15, min(screen_x, gw.x + gw.width - 15))
        screen_y = max(gw.y + 40, min(screen_y, gw.y + gw.height - 15))
        return screen_x, screen_y

    def _move_mouse_human(self, target_x: int, target_y: int, duration: float = 0.18):
        """
        Mueve el cursor hacia (target_x, target_y) siguiendo una trayectoria curva natural (Bézier cúbica)
        con curva suave, aceleración y desaceleración humana.
        """
        try:
            start_x, start_y = win32api.GetCursorPos()
        except Exception:
            start_x, start_y = target_x, target_y

        dist = math.hypot(target_x - start_x, target_y - start_y)
        if dist < 4:
            win32api.SetCursorPos((target_x, target_y))
            return

        # Ajustar duración según la distancia (entre 0.10s y 0.28s)
        actual_duration = max(0.08, min(0.28, dist / 2200.0 + random.uniform(0.06, 0.12)))
        steps = max(10, int(actual_duration * 120))

        # Punto de control con curvatura humana aleatoria
        mid_x = (start_x + target_x) / 2.0
        mid_y = (start_y + target_y) / 2.0
        # Desviación perpendicular para crear arco natural
        angle = math.atan2(target_y - start_y, target_x - start_x) + math.pi / 2
        deviation = random.uniform(-dist * 0.15, dist * 0.15)
        ctrl_x = mid_x + math.cos(angle) * deviation
        ctrl_y = mid_y + math.sin(angle) * deviation

        delay = actual_duration / steps
        for i in range(1, steps + 1):
            t = i / float(steps)
            # Easing: smoothstep (aceleración al inicio, frenado al final)
            ease_t = t * t * (3.0 - 2.0 * t)
            
            # Curva cuadrática de Bézier con punto de control
            inv = 1.0 - ease_t
            curr_x = int(inv * inv * start_x + 2 * inv * ease_t * ctrl_x + ease_t * ease_t * target_x)
            curr_y = int(inv * inv * start_y + 2 * inv * ease_t * ctrl_y + ease_t * ease_t * target_y)

            try:
                win32api.SetCursorPos((curr_x, curr_y))
            except Exception:
                pass
            time.sleep(delay)

        try:
            win32api.SetCursorPos((target_x, target_y))
        except Exception:
            pass

    def click(self, x: float, y: float, normalized: bool = False, delay: float = 0.12, jitter: int = 3):
        """
        Realiza un clic izquierdo con movimiento natural humanizado.
        """
        sx, sy = self.to_screen_coords(x, y, normalized)

        if jitter > 0:
            sx += random.randint(-jitter, jitter)
            sy += random.randint(-jitter, jitter)

        try:
            self.bring_to_front()
            self._move_mouse_human(sx, sy)
            time.sleep(random.uniform(0.02, 0.05))

            # Pulsación del botón con retención humana (50ms - 95ms)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(random.uniform(0.05, 0.095))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self._last_click_pos = (sx, sy)
        except Exception:
            pass

        time.sleep(delay)

    def click_relative(self, nx: float, ny: float, delay: float = 0.12):
        """Click using normalized coordinates (0.0 to 1.0)."""
        self.click(nx, ny, normalized=True, delay=delay)

    def click_screen(self, sx: int, sy: int, delay: float = 0.12):
        """Click using absolute screen pixel coordinates."""
        gw = self._get_window()
        # If coordinates are within window, convert to window-relative
        if gw:
            rel_x = sx - gw.x
            rel_y = sy - gw.y
            self.click(rel_x, rel_y, normalized=False, delay=delay)
        else:
            self.click(sx, sy, normalized=False, delay=delay)

    def right_click(self, x: float = 0.5, y: float = 0.5, normalized: bool = True, delay: float = 0.12):
        """Click derecho humanizado (para cancelar prompts o deseleccionar cartas)."""
        sx, sy = self.to_screen_coords(x, y, normalized)
        try:
            self.bring_to_front()
            self._move_mouse_human(sx, sy)
            time.sleep(random.uniform(0.02, 0.04))

            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(random.uniform(0.05, 0.08))
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        except Exception:
            pass
        time.sleep(delay)

    def drag(self, start_x: float, start_y: float, end_x: float, end_y: float,
             normalized: bool = False, duration: float = 0.32):
        """Arrastra suavemente el ratón con aceleración suave."""
        s_x, s_y = self.to_screen_coords(start_x, start_y, normalized)
        e_x, e_y = self.to_screen_coords(end_x, end_y, normalized)

        try:
            self.bring_to_front()
            self._move_mouse_human(s_x, s_y, duration=0.15)
            time.sleep(0.05)

            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)

            # Arrastre con curva
            steps = max(15, int(duration * 60))
            delay_step = duration / steps
            for i in range(1, steps + 1):
                t = i / float(steps)
                ease_t = t * t * (3.0 - 2.0 * t)
                curr_x = int(s_x + (e_x - s_x) * ease_t)
                curr_y = int(s_y + (e_y - s_y) * ease_t)
                win32api.SetCursorPos((curr_x, curr_y))
                time.sleep(delay_step)

            time.sleep(0.04)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception:
            pass

        time.sleep(0.1)

    def safe_dismiss_click(self):
        """Clic neutral en zona vacía para avanzar texto o cerrar pantallas."""
        self.click(0.85, 0.15, normalized=True, delay=0.15)
