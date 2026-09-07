"""
Screen Capture Module for Yu-Gi-Oh! Master Duel
Captura exclusivamente la ventana de Master Duel (16:9).
Compatible con DirectX / Unity mediante MSS conectado al escritorio interactivo de Windows.
"""

import time
import ctypes
import ctypes.wintypes
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    import win32gui
    import win32con
    import win32process
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class GameWindow:
    hwnd: int
    title: str
    x: int
    y: int
    width: int
    height: int
    is_visible: bool

    @property
    def rect(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def __str__(self):
        v = "visible" if self.is_visible else "oculta"
        return f"GameWindow('{self.title}' [{self.width}x{self.height}] @ ({self.x},{self.y}) hwnd={self.hwnd} [{v}])"


class ScreenCapture:
    """
    Capturador especializado para Yu-Gi-Oh! Master Duel.
    Conexión nativa al escritorio interactivo para captura en tiempo real de DirectX/Unity.
    """

    GAME_TITLES = [
        "masterduel",
        "Yu-Gi-Oh! MASTER DUEL",
        "Yu-Gi-Oh! Master Duel",
        "MASTER DUEL",
        "Master Duel",
    ]
    GAME_PROCESS = "masterduel.exe"

    def __init__(self, game_title: Optional[str] = None):
        self._custom_title = game_title
        if game_title and game_title not in self.GAME_TITLES:
            self.GAME_TITLES.insert(0, game_title)
        self._window: Optional[GameWindow] = None
        self._sct = None
        self._last_capture_time = 0.0
        self._capture_count = 0

    def _attach_to_desktop(self):
        """Asegura que el hilo esté conectado al escritorio interactivo del usuario."""
        try:
            user32 = ctypes.windll.user32
            DESKTOP_ALL = 0x01FF
            hdesk = user32.OpenDesktopW("default", 0, False, DESKTOP_ALL)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
                if MSS_AVAILABLE and self._sct is None:
                    self._sct = mss.MSS()
        except Exception:
            pass

    def find_game_window(self) -> Optional[GameWindow]:
        """Localiza la ventana activa de Master Duel."""
        if not PYWIN32_AVAILABLE:
            print("[ERROR] pywin32 no está disponible. Ejecuta: pip install pywin32")
            return None

        self._attach_to_desktop()

        gw = self._find_by_desktop_enum()
        if gw:
            print(f"[OK] Ventana de Master Duel conectada: {gw}")
            self._window = gw
            self._restore_and_focus(gw)
            return gw

        gw = self._find_by_title_exact()
        if gw:
            print(f"[OK] Ventana de Master Duel encontrada (título exacto): {gw}")
            self._window = gw
            self._restore_and_focus(gw)
            return gw

        print("[WARN] No se encontró la ventana de Master Duel.")
        print(f"       Verifica que {self.GAME_PROCESS} esté abierto.")
        return None

    def _find_by_desktop_enum(self) -> Optional[GameWindow]:
        """Búsqueda directa en el escritorio interactivo."""
        user32 = ctypes.windll.user32
        DESKTOP_ALL = 0x01FF
        hdesk = user32.OpenDesktopW("default", 0, False, DESKTOP_ALL)
        if not hdesk:
            return None

        found_windows = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

        def cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                pid = ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buf, 512)
                title = buf.value.strip()

                pname = ""
                if PSUTIL_AVAILABLE:
                    try:
                        pname = psutil.Process(pid.value).name().lower()
                    except Exception:
                        pass

                # Descartar explorador de archivos
                if pname == "explorer.exe" or "explorador de archivos" in title.lower():
                    return True

                # Prioridad 1: Proceso exacto masterduel.exe
                if pname == self.GAME_PROCESS.lower():
                    gw = self._hwnd_to_gamewindow(hwnd, title or "masterduel")
                    if gw and gw.width >= 300 and gw.height >= 200:
                        found_windows.append((10, gw))
                        return True

                # Prioridad 2: Título exacto
                if title.lower() in [t.lower() for t in self.GAME_TITLES]:
                    gw = self._hwnd_to_gamewindow(hwnd, title)
                    if gw and gw.width >= 300 and gw.height >= 200:
                        found_windows.append((5, gw))
                        return True

            return True

        try:
            user32.EnumDesktopWindows(hdesk, WNDENUMPROC(cb), 0)
        finally:
            user32.CloseDesktop(hdesk)

        if found_windows:
            found_windows.sort(key=lambda item: (item[0], item[1].width * item[1].height), reverse=True)
            return found_windows[0][1]
        return None

    def _find_by_title_exact(self) -> Optional[GameWindow]:
        user32 = ctypes.windll.user32
        for title in self.GAME_TITLES:
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                gw = self._hwnd_to_gamewindow(hwnd, title)
                if gw and gw.width >= 300 and gw.height >= 200:
                    return gw
        return None

    def _hwnd_to_gamewindow(self, hwnd: int, title: str) -> Optional[GameWindow]:
        try:
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            is_vis = bool(win32gui.IsWindowVisible(hwnd))
            return GameWindow(
                hwnd=hwnd,
                title=title,
                x=rect.left,
                y=rect.top,
                width=w,
                height=h,
                is_visible=is_vis
            )
        except Exception:
            return None

    def _restore_and_focus(self, gw: GameWindow):
        try:
            if win32gui.IsIconic(gw.hwnd):
                win32gui.ShowWindow(gw.hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)
        except Exception:
            pass

    def capture_frame(self) -> Optional[np.ndarray]:
        """Captura el frame actual de la ventana de Master Duel (DirectX/Unity)."""
        self._attach_to_desktop()

        if not self._window or not win32gui.IsWindow(self._window.hwnd):
            gw = self.find_game_window()
            if not gw:
                return None
            self._window = gw

        user32 = ctypes.windll.user32
        rect = ctypes.wintypes.RECT()
        if not user32.GetWindowRect(self._window.hwnd, ctypes.byref(rect)):
            return None

        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w < 200 or h < 200:
            return None

        self._window.x = rect.left
        self._window.y = rect.top
        self._window.width = w
        self._window.height = h

        try:
            if not self._sct and MSS_AVAILABLE:
                self._sct = mss.MSS()

            if self._sct:
                mon = {
                    "top": rect.top,
                    "left": rect.left,
                    "width": w,
                    "height": h
                }
                shot = self._sct.grab(mon)
                img = np.array(shot, dtype=np.uint8)[:, :, :3]
                if np.mean(img) > 1.0:
                    self._capture_count += 1
                    self._last_capture_time = time.time()
                    return img
        except Exception:
            try:
                self._sct = mss.MSS() if MSS_AVAILABLE else None
            except Exception:
                pass

        return None

    def capture(self) -> Optional[np.ndarray]:
        """Alias for capture_frame()."""
        return self.capture_frame()

    @property
    def window(self) -> Optional[GameWindow]:
        return self._window
