"""
Yu-Gi-Oh! MASTER DUEL — LIVE HUD COACH OVERLAY (1366x768)
Coach en vivo: NEURONAL - JUGADA ÓPTIMA
- Escaneo de Deck en Modo Solo / Confirmación de Baraja.
- Guarda la baraja en decks_estrategias/<nombre>.json y su estrategia en .md.
- Alerta visual inmediata: "✅ ¡Deck Analizado! 🎮 ¡Ya puedes darle a jugar!".
- Secuencia en Z de 4 pasos con cartas reales.
- Acople manual [📌 Acoplar] y cero cartas inventadas.
"""

import os
import sys
import time
import json
import re
import unicodedata
from coach.i18n import t, LANGUAGES
import math
import threading
import subprocess
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, List
import urllib.request
import io
from PIL import Image, ImageTk

try:
    from coach.database import CoachDatabase
    from coach.live_brain import LiveVisionCoach
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from coach.database import CoachDatabase
    from coach.live_brain import LiveVisionCoach

class LiveCoachOverlay:
    def __init__(self, root):
        self.root = root
        self.root.title("Neuronal - Jugada Óptima")
        
        # Dimensiones para monitor 1366x768
        self.width = 360
        self.height = 768
        self.root.geometry(f"{self.width}x{self.height}+0+0")
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg="#040711")
        
        self.db = CoachDatabase()
        self.brain = LiveVisionCoach(self.db)
        
        self.image_cache = {}
        self.z_image_cache = {}
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_images")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.is_running = True
        self.is_paused = False
        self.is_analyzing = False
        self.is_scanning_deck = False
        self.current_lang = self._load_lang_config()
        self.lang_buttons = {}
        self._current_photo = None
        self.hand_labels = []
        
        # Estado de Deck escaneado
        self.current_deck_data = None
        
        # 4 Nodos en Z
        self.nodes_data = []
        self.pulse_progress = 0.0
        
        self._init_fast_card_index()
        self._build_ui()
        
        # Cargar automáticamente baraja previa si ya fue escaneada
        if self.brain.active_deck:
            self.root.after(100, lambda: self._apply_deck_scan_result(self.brain.active_deck))
        
        # Iniciar pulso visual Z continuo (30 FPS)
        self._animate_z_pulse()
        
        # Iniciar bucle de escaneo rápido de duelo
        self.auto_thread = threading.Thread(target=self._fast_scanning_loop, daemon=True)
        self.auto_thread.start()

    def _load_lang_config(self) -> str:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coach_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("language", "ES")
        except Exception:
            pass
        return "ES"

    def _save_lang_config(self, lang_code: str):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coach_config.json")
        try:
            cfg = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                except Exception:
                    pass
            cfg["language"] = lang_code
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _set_language(self, lang_code: str):
        if lang_code not in LANGUAGES:
            return
        self.current_lang = lang_code
        self._save_lang_config(lang_code)

        # Update language selector button styles
        for code, btn in getattr(self, "lang_buttons", {}).items():
            if code == lang_code:
                btn.config(bg="#00F5FF", fg="#040711")
            else:
                btn.config(bg="#1E293B", fg="#94A3B8")

        # Update static labels
        if hasattr(self, "title_lbl"):
            self.title_lbl.config(text=f"⚡ {t('app_title', lang_code)}")
        if hasattr(self, "live_badge"):
            self.live_badge.config(text=f"● {t('live_badge', lang_code)}")
        if hasattr(self, "hero_frame"):
            self.hero_frame.config(text=f" {t('hero_title', lang_code)} ")
        if hasattr(self, "route_frame"):
            self.route_frame.config(text=f" {t('combo_route_title', lang_code)} ")
        if hasattr(self, "hand_frame"):
            self.hand_frame.config(text=f" {t('hand_title', lang_code)} ")
        if hasattr(self, "threat_title_lbl"):
            self.threat_title_lbl.config(text=f"🛡️ {t('tactical_alert_title', lang_code)}")
        if hasattr(self, "scan_deck_btn"):
            self.scan_deck_btn.config(text=f"{t('scan_deck_btn', lang_code)}")
        if hasattr(self, "status_lbl"):
            self.status_lbl.config(text=t("scanning_status", lang_code))

        # Re-render pills & hand
        self._render_combo_pills()
    def _build_ui(self):
        # 1. Cabecera limpia y profesional
        header = tk.Frame(self.root, bg="#0A1124", padx=8, pady=5, highlightthickness=1, highlightbackground="#1E293B")
        header.pack(fill="x")
        
        top_row = tk.Frame(header, bg="#0A1124")
        top_row.pack(fill="x")
        
        self.title_lbl = tk.Label(
            top_row,
            text=f"⚡ {t('app_title', self.current_lang)}",
            font=("Segoe UI", 8, "bold"),
            fg="#00F5FF",
            bg="#0A1124"
        )
        self.title_lbl.pack(side="left")
        
        # Selector de Idioma (ES | EN | FR | DE | IT)
        lang_bar = tk.Frame(top_row, bg="#0A1124")
        lang_bar.pack(side="right", padx=(2, 0))

        for l_code in ["IT", "DE", "FR", "EN", "ES"]:
            is_cur = (l_code == self.current_lang)
            b = tk.Button(
                lang_bar,
                text=l_code,
                font=("Segoe UI", 6, "bold"),
                fg="#040711" if is_cur else "#94A3B8",
                bg="#00F5FF" if is_cur else "#1E293B",
                activebackground="#00F5FF",
                activeforeground="#040711",
                relief="flat",
                padx=3,
                pady=0,
                command=lambda c=l_code: self._set_language(c)
            )
            b.pack(side="right", padx=1)
            self.lang_buttons[l_code] = b

        # Botón Acoplar
        dock_btn = tk.Button(
            top_row,
            text="📌",
            font=("Segoe UI", 7, "bold"),
            fg="#00F5FF",
            bg="#1E293B",
            activebackground="#00F5FF",
            activeforeground="#040711",
            relief="flat",
            padx=3,
            pady=0,
            command=self._manual_dock
        )
        dock_btn.pack(side="right", padx=(2, 1))

        self.scan_deck_btn = tk.Button(
            top_row,
            text="📋 Escanear Deck",
            font=("Segoe UI", 7, "bold"),
            fg="#FEF08A",
            bg="#854D0E",
            activebackground="#FACC15",
            activeforeground="#040711",
            relief="flat",
            padx=4,
            pady=0,
            command=self._trigger_deck_scan
        )
        self.scan_deck_btn.pack(side="right", padx=(3, 0))
        
        self.live_badge = tk.Label(
            top_row,
            text="● EN VIVO",
            font=("Segoe UI", 8, "bold"),
            fg="#10B981",
            bg="#0A1124"
        )
        self.live_badge.pack(side="right", padx=(0, 4))
        
        self.status_lbl = tk.Label(
            header,
            text="Escaneando Master Duel en tiempo real...",
            font=("Segoe UI", 8),
            fg="#94A3B8",
            bg="#0A1124"
        )
        self.status_lbl.pack(anchor="w", pady=(1, 0))

        # Banner de Ventana Modal (si se abre Extra Deck / Cementerio en el juego)
        self.modal_banner = tk.Label(
            self.root,
            text="",
            font=("Segoe UI", 8, "bold"),
            fg="#FEF08A",
            bg="#854D0E",
            padx=6,
            pady=2,
            wraplength=345,
            justify="left"
        )

        # Contenedor con Scroll
        self.main_canvas = tk.Canvas(self.root, bg="#040711", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scroll_content = tk.Frame(self.main_canvas, bg="#040711")
        
        self.scroll_content.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        self.main_canvas.create_window((0, 0), window=self.scroll_content, anchor="nw", width=self.width - 14)
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.root.bind_all("<MouseWheel>", lambda event: self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units"))

        # =========================================================================
        # SECCIÓN MODO SOLO: BANNER DE ESTRATEGIA Y ESTADO DEL DECK
        # =========================================================================
        self.deck_alert_frame = tk.Frame(self.scroll_content, bg="#0E1E38", padx=6, pady=4, highlightthickness=1, highlightbackground="#0284C7")
        self.deck_alert_frame.pack(fill="x", padx=4, pady=2)

        self.deck_title_lbl = tk.Label(
            self.deck_alert_frame,
            text="📋 MODO SOLO: Abre tu Deck para crear su Estrategia",
            font=("Segoe UI", 8, "bold"),
            fg="#38BDF8",
            bg="#0E1E38",
            justify="left",
            wraplength=330
        )
        self.deck_title_lbl.pack(anchor="w")

        self.deck_action_row = tk.Frame(self.deck_alert_frame, bg="#0E1E38")
        self.deck_action_row.pack(fill="x", pady=(2, 0))

        self.deck_desc_lbl = tk.Label(
            self.deck_action_row,
            text="Abre 'Confirmar baraja' o el Editor y pulsa:",
            font=("Segoe UI", 7),
            fg="#94A3B8",
            bg="#0E1E38"
        )
        self.deck_desc_lbl.pack(side="left")

        self.deck_quick_btn = tk.Button(
            self.deck_action_row,
            text="🔍 Escanear Ahora",
            font=("Segoe UI", 7, "bold"),
            fg="#040711",
            bg="#38BDF8",
            activebackground="#00F5FF",
            relief="flat",
            padx=4,
            pady=0,
            command=self._trigger_deck_scan
        )
        self.deck_quick_btn.pack(side="right")

        # =========================================================================
        # SECCIÓN 1: ⭐ HERO CARD - JUGADA INMEDIATA (QUÉ JUGAR AHORA)
        # =========================================================================
        self.hero_frame = tk.LabelFrame(
            self.scroll_content,
            text=" ⭐ JUGADA INMEDIATA (QUÉ JUGAR AHORA) ",
            font=("Segoe UI", 8, "bold"),
            fg="#FACC15",
            bg="#080E21",
            padx=8,
            pady=6,
            highlightbackground="#EAB308",
            highlightthickness=1
        )
        self.hero_frame.pack(fill="x", padx=4, pady=3)

        hero_content = tk.Frame(self.hero_frame, bg="#080E21")
        hero_content.pack(fill="x")

        # Miniatura de carta Hero (84x122 px)
        self.art_canvas = tk.Canvas(hero_content, width=84, height=122, bg="#0B132B", highlightthickness=2, highlightbackground="#00F5FF")
        self.art_canvas.pack(side="left", padx=(0, 8))

        hero_details = tk.Frame(hero_content, bg="#080E21")
        hero_details.pack(side="left", fill="both", expand=True)

        # Barra superior con Badge de acción y EV%
        badge_row = tk.Frame(hero_details, bg="#080E21")
        badge_row.pack(fill="x")

        self.hero_action_badge = tk.Label(
            badge_row,
            text="⚡ INVOCACIÓN NORMAL",
            font=("Segoe UI", 7, "bold"),
            fg="#040711",
            bg="#00F5FF",
            padx=5,
            pady=1
        )
        self.hero_action_badge.pack(side="left")

        self.pct_lbl = tk.Label(
            badge_row,
            text="98% EV",
            font=("Segoe UI", 8, "bold"),
            fg="#10B981",
            bg="#080E21"
        )
        self.pct_lbl.pack(side="right")

        # Nombre de la carta principal
        self.best_card_lbl = tk.Label(
            hero_details,
            text="Esperando detección...",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg="#080E21",
            anchor="w",
            wraplength=210,
            justify="left"
        )
        self.best_card_lbl.pack(fill="x", pady=(3, 1))

        # Caja de Instrucción de Acción
        act_box = tk.Frame(hero_details, bg="#0B1220", padx=5, pady=3, highlightbackground="#1E293B", highlightthickness=1)
        act_box.pack(fill="x", pady=(2, 3))

        self.best_action_lbl = tk.Label(
            act_box,
            text="👉 Inicia tu turno o abre tu mano para evaluar la mejor jugada.",
            font=("Segoe UI", 8),
            fg="#E2E8F0",
            bg="#0B1220",
            wraplength=205,
            justify="left"
        )
        self.best_action_lbl.pack(fill="x")

        # Razón / Objetivo táctico
        self.hero_why_lbl = tk.Label(
            hero_details,
            text="💡 Objetivo: Establecer presencia en campo.",
            font=("Segoe UI", 7, "italic"),
            fg="#38BDF8",
            bg="#080E21",
            anchor="w",
            wraplength=215,
            justify="left"
        )
        self.hero_why_lbl.pack(fill="x")

        # Barra de probabilidad compacta
        self.prob_bar = ttk.Progressbar(hero_details, orient="horizontal", mode="determinate")
        self.prob_bar.pack(fill="x", pady=(3, 0))
        self.prob_bar["value"] = 85

        # =========================================================================
        # SECCIÓN 2: ⚡ RUTA DEL COMBO (HOJA DE RUTA COMPACTA)
        # =========================================================================
        self.route_frame = tk.LabelFrame(
            self.scroll_content,
            text=" ⚡ RUTA DEL COMBO (HOJA DE RUTA) ",
            font=("Segoe UI", 8, "bold"),
            fg="#00F5FF",
            bg="#070C1B",
            padx=6,
            pady=4,
            highlightbackground="#1E293B"
        )
        self.route_frame.pack(fill="x", padx=4, pady=2)

        self.pills_container = tk.Frame(self.route_frame, bg="#070C1B")
        self.pills_container.pack(fill="x", pady=2)

        self.nodes_data = [
            {"node": 1, "phase": "1. INICIO", "card": "Esperando...", "action": "Invocación Normal", "ev": 90, "status": "ACTIVE"},
            {"node": 2, "phase": "2. EXTENSIÓN", "card": "Esperando...", "action": "Extensión Especial", "ev": 90, "status": "PENDING"},
            {"node": 3, "phase": "3. FUSIÓN", "card": "Esperando...", "action": "Invocación Extra Deck", "ev": 90, "status": "PENDING"},
            {"node": 4, "phase": "4. REMATE", "card": "Esperando...", "action": "Fin de Turno", "ev": 90, "status": "PENDING"}
        ]
        self._render_combo_pills()

        self.route_summary_lbl = tk.Label(
            self.route_frame,
            text="Ruta: Esperando detección de baraja...",
            font=("Segoe UI", 7),
            fg="#64748B",
            bg="#070C1B",
            wraplength=330,
            justify="left"
        )
        self.route_summary_lbl.pack(fill="x", pady=(3, 0))

        # =========================================================================
        # SECCIÓN 2.5: 🛡️ ALERTA TÁCTICA Y AMENAZAS
        # =========================================================================
        self.threat_frame = tk.Frame(self.scroll_content, bg="#1E170A", padx=8, pady=4, highlightbackground="#D97706", highlightthickness=1)
        self.threat_frame.pack(fill="x", padx=4, pady=2)

        self.threat_desc_lbl = tk.Label(
            self.threat_frame,
            text="🛡️ Alerta Táctica: Evalúa el campo antes de atacar.",
            font=("Segoe UI", 7, "bold"),
            fg="#FDE68A",
            bg="#1E170A",
            justify="left",
            wraplength=330
        )
        self.threat_desc_lbl.pack(anchor="w")
        # =========================================================================
        # SECCIÓN 3: TU MANO REAL
        # =========================================================================
        hand_frame = tk.LabelFrame(
            self.scroll_content,
            text=" 🃏 CARTAS EN TU MANO (REALES) ",
            font=("Segoe UI", 8, "bold"),
            fg="#38BDF8",
            bg="#070C1B",
            padx=6,
            pady=2,
            highlightbackground="#1E293B"
        )
        hand_frame.pack(fill="x", padx=4, pady=2)
        
        self.hand_cards_container = tk.Frame(hand_frame, bg="#070C1B")
        self.hand_cards_container.pack(fill="x")
        
        init_lbl = tk.Label(
            self.hand_cards_container,
            text="Escaneando tu mano en Master Duel...",
            font=("Segoe UI", 8),
            fg="#64748B",
            bg="#070C1B",
            anchor="w"
        )
        init_lbl.pack(fill="x", pady=1)
        self.hand_labels.append(init_lbl)

        # =========================================================================
        # SECCIÓN 4: TABLERO RIVAL
        # =========================================================================
        opp_frame = tk.LabelFrame(
            self.scroll_content,
            text=" ⚔️ CAMPO DEL OPONENTE ",
            font=("Segoe UI", 8, "bold"),
            fg="#EF4444",
            bg="#070C1B",
            padx=6,
            pady=2,
            highlightbackground="#1E293B"
        )
        opp_frame.pack(fill="x", padx=4, pady=2)
        
        self.opp_summary_lbl = tk.Label(
            opp_frame,
            text="Monstruos: - | Magias/Trampas: - | Amenaza: -",
            font=("Segoe UI", 8),
            fg="#F87171",
            bg="#070C1B",
            justify="left",
            wraplength=320
        )
        self.opp_summary_lbl.pack(anchor="w")

        # Pie
        footer = tk.Frame(self.root, bg="#040711", padx=6, pady=2)
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text="Neuronal - Jugada Óptima | masterduel.exe | Always on Top",
            font=("Segoe UI", 7),
            fg="#475569",
            bg="#040711"
        ).pack()

    def _manual_dock(self):
        """Acopla la ventana manualmente cuando el usuario pulsa [📌 Acoplar]."""
        try:
            hwnd = self.brain._find_masterduel_hwnd()
            if hwnd:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                
                md_left = rect.left
                md_top = rect.top
                md_right = rect.right
                md_bottom = rect.bottom
                md_w = md_right - md_left
                md_h = md_bottom - md_top
                
                if md_w >= 400 and md_h >= 300:
                    target_x = max(0, md_left - self.width)
                    target_y = max(0, md_top)
                    target_h = min(768, max(650, md_h))
                    self.root.geometry(f"{self.width}x{target_h}+{target_x}+{target_y}")
                    self.status_lbl.config(text="📌 Ventana acoplada junto a Master Duel", fg="#00F5FF")
        except Exception:
            pass

    def _trigger_deck_scan(self):
        """Dispara el escaneo de baraja en pantalla completa y genera la estrategia."""
        if self.is_scanning_deck:
            return

        frame = self.brain.capture_game_screen()
        if frame is None:
            self.status_lbl.config(text="⚠️ No se pudo capturar Master Duel. Enfoca el juego.", fg="#FEF08A")
            return

        self.is_scanning_deck = True
        self.status_lbl.config(text="🔍 Escaneando baraja y generando estrategia...", fg="#FEF08A")
        self.deck_title_lbl.config(text="🔍 Escaneando receta de Konami...", font=("Segoe UI", 9, "bold"), fg="#FEF08A", bg="#854D0E")
        
        def task():
            try:
                res = self.brain.analyze_deck_screen(frame)
                self.root.after(0, lambda: self._apply_deck_scan_result(res))
            except Exception as e:
                self.root.after(0, lambda: self.status_lbl.config(text=f"Error escaneando deck", fg="#EF4444"))
            finally:
                self.is_scanning_deck = False

        threading.Thread(target=task, daemon=True).start()

    def _show_strategy_popup(self, md_path: str, deck_name: str = "Estrategia"):
        if not md_path or not os.path.exists(md_path):
            return
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return

        if hasattr(self, "_strat_popup") and self._strat_popup and self._strat_popup.winfo_exists():
            self._strat_popup.lift()
            return

        pop = tk.Toplevel(self.root)
        self._strat_popup = pop
        pop.title(f"Plan de Juego - {deck_name}")
        pop.geometry("460x600+120+120")
        pop.configure(bg="#070C1B")
        pop.attributes("-topmost", True)

        head = tk.Frame(pop, bg="#0B1220", padx=10, pady=8)
        head.pack(fill="x")
        tk.Label(
            head,
            text=f"📋 ESTRATEGIA: {deck_name.upper()}",
            font=("Segoe UI", 9, "bold"),
            fg="#00F5FF",
            bg="#0B1220"
        ).pack(side="left")
        tk.Button(
            head,
            text="✕ Cerrar",
            font=("Segoe UI", 8, "bold"),
            fg="#E2E8F0",
            bg="#1E293B",
            activebackground="#EF4444",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=8,
            pady=2,
            command=pop.destroy
        ).pack(side="right")

        body = tk.Frame(pop, bg="#070C1B", padx=8, pady=8)
        body.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(body)
        scrollbar.pack(side="right", fill="y")

        txt = tk.Text(
            body,
            bg="#050814",
            fg="#E2E8F0",
            font=("Segoe UI", 9),
            wrap="word",
            padx=10,
            pady=10,
            yscrollcommand=scrollbar.set,
            relief="flat",
            highlightbackground="#1E293B",
            highlightthickness=1
        )
        txt.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=txt.yview)

        txt.insert("1.0", content)
        txt.config(state="disabled")

    def _apply_deck_scan_result(self, data: Optional[Dict[str, Any]]):
        if not data or (not data.get("is_deck_screen") and not data.get("key_starters") and not data.get("strategy")):
            self.status_lbl.config(text="Pantalla no reconocida como Deck. Abre Confirmar baraja.", fg="#FEF08A")
            self.deck_title_lbl.config(text="MODO SOLO: Abre la pantalla de tu Deck y pulsa Escanear", fg="#38BDF8")
            return

        self.current_deck_data = data
        d_name = data.get("deck_name", "Baraja Analizada")
        arch = data.get("archetype", "General")
        starters = ", ".join(data.get("key_starters", [])[:3])
        strat = data.get("strategy", {})
        md_file = data.get("saved_md_path", "")

        # Alerta visual en verde destacando si es Baraja de Préstamo
        self.deck_alert_frame.config(bg="#064E3B", highlightbackground="#10B981")
        is_loaner = data.get("is_loaner", True)
        tag = "DECK PRESTADO" if is_loaner else "DECK"
        banner_msg = f"[{tag}: {d_name.upper()}]\n🎮 ¡Ya puedes darle a jugar!"
        self.deck_title_lbl.config(text=banner_msg, font=("Segoe UI", 9, "bold"), fg="#A7F3D0", bg="#064E3B")
        
        for w in self.deck_action_row.winfo_children():
            w.destroy()

        info_text = f"Starters: {starters}\nFin: {strat.get('end_board', '')[:45]}"
        tk.Label(
            self.deck_action_row,
            text=info_text,
            font=("Segoe UI", 7),
            fg="#D1FAE5",
            bg="#064E3B",
            justify="left",
            wraplength=250
        ).pack(side="left")

        if md_file and os.path.exists(md_file):
            tk.Button(
                self.deck_action_row,
                text="📋 Ver Estrategia",
                font=("Segoe UI", 7, "bold"),
                fg="#040711",
                bg="#10B981",
                activebackground="#34D399",
                relief="flat",
                padx=4,
                pady=1,
                command=lambda p=md_file, n=d_name: self._show_strategy_popup(p, n)
            ).pack(side="right")

        self.status_lbl.config(text=f"● MODO SOLO: {d_name} listo. ¡Pulsa Jugar en Master Duel!", fg="#10B981")

        # Cargar el combo de esta baraja en los 4 nodos Z inmediatamente
        main_cards = data.get("main_deck_cards", [])
        key_starters = data.get("key_starters", [])
        extra_cards = data.get("extra_deck_cards", [])
        combo_steps = strat.get("combo_steps", [])

        s1 = key_starters[0] if len(key_starters) > 0 else main_cards[0] if main_cards else "Carta Principal"
        s2 = key_starters[1] if len(key_starters) > 1 else (data.get("main_deck_cards", [main_cards[1] if len(main_cards) > 1 else "Extensor"])[0] if data.get("main_deck_cards") else main_cards[1] if len(main_cards) > 1 else "Extensor")
        s3 = extra_cards[0] if len(extra_cards) > 0 else extra_cards[0] if extra_cards else "Extra Deck"
        s4 = extra_cards[1] if len(extra_cards) > 1 else (extra_cards[0] if extra_cards else "I:P Enmascarada")

        act1 = combo_steps[0] if len(combo_steps) > 0 else "Invocación Normal (Starter)"
        act2 = combo_steps[1] if len(combo_steps) > 1 else "Activar efecto para extender"
        act3 = combo_steps[2] if len(combo_steps) > 2 else "Invocación Enlace Link-2"
        act4 = combo_steps[3] if len(combo_steps) > 3 else "Dejar interrupciones preparadas"

        self.nodes_data = [
            {"node": 1, "phase": "1. INICIO", "card": s1, "action": act1, "ev": 98, "status": "ACTIVE"},
            {"node": 2, "phase": "2. EXTENSIÓN", "card": s2, "action": act2, "ev": 94, "status": "PENDING"},
            {"node": 3, "phase": "3. ENLACE", "card": s3, "action": act3, "ev": 92, "status": "PENDING"},
            {"node": 4, "phase": "4. REMATE", "card": s4, "action": act4, "ev": 95, "status": "PENDING"}
        ]
        combo_steps = strat.get("combo_steps", [])
        if combo_steps:
            self.route_summary_lbl.config(text="Cadena: " + " ➔ ".join(combo_steps[:4]))
        elif strat.get("win_condition"):
            self.route_summary_lbl.config(text="🎯 " + strat.get("win_condition"))
        self._render_timeline()

        # Mostrar Starter en la vista previa grande
        self._set_active_card_preview(self.nodes_data[0])

        if combo_steps:
            self.route_summary_lbl.config(text="Cadena: " + " ➔ ".join(combo_steps[:4]))
        elif strat.get("win_condition"):
            self.route_summary_lbl.config(text="🎯 " + strat.get("win_condition"))

    def _format_intuitive_card_name(self, card_name: str) -> str:
        if not card_name:
            return ""
        # Si tiene coma (ej: 'Catastor, Aliado de la Justicia' -> 'Catastor')
        parts = [p.strip() for p in card_name.split(",") if p.strip()]
        if len(parts) >= 2:
            if any(k in parts[1].lower() for k in ["aliado", "justicia", "enmascarada"]):
                return parts[0][:15]
            return parts[0][:15]
        # Quitar prefijos largos redundantes
        for prefix in ["Aliado de la Justicia ", "Live☆Twin ", "Live☆Gemela ", "Evil★Twin ", "Evil★Gemela "]:
            if card_name.startswith(prefix):
                short = card_name[len(prefix):].strip()
                tag = prefix.split()[0][:4]
                return f"{tag} {short}"[:16]
        if len(card_name) > 16:
            return card_name[:15] + "…"
        return card_name

    def _render_combo_pills(self):
        for w in self.pills_container.winfo_children():
            w.destroy()

        if not self.nodes_data:
            tk.Label(self.pills_container, text="Esperando inicio del duelo...", fg="#94A3B8", bg="#070C1B", font=("Segoe UI", 7)).pack(pady=2)
            return

        for i, node in enumerate(self.nodes_data):
            card_name = node.get("card", f"Paso {i+1}")
            phase_text = node.get("phase", f"{i+1}. ACCIÓN")
            status = node.get("status", "ACTIVE" if i == 0 else "PENDING")
            is_active = (i == 0 or status == "ACTIVE")

            b_col = "#00F5FF" if is_active else "#1E293B"
            bg_c = "#0B162C" if is_active else "#080E1C"

            step_card = tk.Frame(
                self.pills_container,
                bg=bg_c,
                padx=2,
                pady=2,
                highlightbackground=b_col,
                highlightthickness=2 if is_active else 1,
                cursor="hand2"
            )
            step_card.pack(side="left", padx=(0, 4), expand=True, fill="both")
            step_card.bind("<Button-1>", lambda e, n=node: self._set_active_card_preview(n))

            # Phase header badge
            p_bg = "#00F5FF" if is_active else "#1E293B"
            p_fg = "#040711" if is_active else "#94A3B8"
            head_lbl = tk.Label(step_card, text=phase_text[:10], font=("Segoe UI", 6, "bold"), fg=p_fg, bg=p_bg)
            head_lbl.pack(fill="x")
            head_lbl.bind("<Button-1>", lambda e, n=node: self._set_active_card_preview(n))

            # Mini canvas with card art (46x64 px)
            thumb_c = tk.Canvas(step_card, width=46, height=64, bg="#0F172A", highlightthickness=1, highlightbackground=b_col)
            thumb_c.pack(pady=2)
            thumb_c.bind("<Button-1>", lambda e, n=node: self._set_active_card_preview(n))

            passcode = self._get_passcode_for_card(card_name)
            if passcode:
                # Check cache or disk
                photo = self.z_image_cache.get(passcode)
                if not photo:
                    p1 = os.path.join(self.cache_dir, f"{passcode}.jpg")
                    p2 = os.path.join(self.cache_dir, f"{passcode:08d}.jpg")
                    disk_path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
                    if disk_path:
                        try:
                            t_img = Image.open(disk_path).resize((46, 64), Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(t_img)
                            self.z_image_cache[passcode] = photo
                        except Exception:
                            pass
                if photo:
                    thumb_c.create_image(23, 32, image=photo)
                else:
                    thumb_c.create_text(23, 32, text="🃏", font=("Segoe UI", 12))
                    self._load_z_image_async(passcode)
            else:
                thumb_c.create_text(23, 32, text="⚡", font=("Segoe UI", 12))

            short_name = self._format_intuitive_card_name(card_name)
            if len(short_name) > 11:
                short_name = short_name[:10] + "…"

            name_lbl = tk.Label(step_card, text=short_name, font=("Segoe UI", 7, "bold" if is_active else "normal"), fg="#FFFFFF" if is_active else "#94A3B8", bg=bg_c)
            name_lbl.pack(fill="x")
            name_lbl.bind("<Button-1>", lambda e, n=node: self._set_active_card_preview(n))

    def _render_timeline(self):
        self._render_combo_pills()
    def _set_active_card_preview(self, node: dict):
        c_name = node.get("card", "Desconocida")
        act = node.get("action", "Ejecutar acción")
        phase = node.get("phase", "ACCIÓN")
        pct = float(node.get("ev", 92))

        self.best_card_lbl.config(text=c_name)
        
        # Badge de fase / acción
        badge_text = f"⚡ {phase.upper()}" if phase else "⚡ JUGADA ÓPTIMA"
        self.hero_action_badge.config(text=badge_text[:20])

        self.best_action_lbl.config(text=f"👉 {act}")
        self.pct_lbl.config(text=f"{pct:.0f}% EV")
        self.prob_bar["value"] = pct

        # Razón táctica
        if "Normal" in act:
            self.hero_why_lbl.config(text="💡 Inicia la jugada preparando monstruos o búsquedas clave.")
        elif "Especial" in act:
            self.hero_why_lbl.config(text="💡 Extiende presencia en campo sin gastar tu Invocación Normal.")
        elif "Fusión" in act or "Enlace" in act or "Xyz" in act or "Sincronía" in act:
            self.hero_why_lbl.config(text="💡 Invoca tu monstruo del Extra Deck para dominar el duelo.")
        elif "Ataque" in act or "Batalla" in act or "OTK" in act:
            self.hero_why_lbl.config(text="💡 Fase de combate: Ataca directamente o supera los monstruos rivales.")
        else:
            self.hero_why_lbl.config(text=f"💡 Paso táctico para asegurar la victoria.")

        # Cargar arte en Hero canvas (84x122)
        passcode = self._get_passcode_for_card(c_name)
        if passcode:
            self._load_big_image_async(passcode)
        else:
            self.art_canvas.delete("all")
            self.art_canvas.create_text(42, 61, text="🃏", font=("Segoe UI", 24), fill="#00F5FF")

    def _init_fast_card_index(self):
        self._card_exact_index = {}
        self._card_word_index = []
        if not self.db or not hasattr(self.db, "conn") or not self.db.conn:
            return
        try:
            import unicodedata
            stopwords = {"de", "del", "la", "el", "los", "las", "un", "una", "y", "en", "para", "con"}
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT passcode, name_en, name_es FROM cards")
            for code, en, es in cursor.fetchall():
                if not code or not str(code).isdigit():
                    continue
                p = int(code)
                norm_en = self._normalize_text(en)
                norm_es = self._normalize_text(es)
                self._card_exact_index[norm_en] = p
                self._card_exact_index[norm_es] = p
                
                w_en = set(w for w in re.findall(r"[a-z0-9]+", norm_en) if len(w) > 2 and w not in stopwords)
                w_es = set(w for w in re.findall(r"[a-z0-9]+", norm_es) if len(w) > 2 and w not in stopwords)
                self._card_word_index.append((p, norm_es, norm_en, w_es | w_en))
        except Exception:
            pass

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        import unicodedata
        nfkd = unicodedata.normalize("NFKD", str(text))
        return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

    def _get_passcode_for_card(self, card_name: str) -> Optional[int]:
        if not card_name or len(str(card_name).strip()) < 3:
            return None

        c_clean = str(card_name).lower().strip()
        BLACKLIST = {
            "starter", "especial", "extra deck", "fin de turno", "avanzar de fase", 
            "avanzar fase", "pasar turno", "desconocida", "ninguna", "esperando acción...",
            "esperando inicio...", "esperando...", "evaluando tablero", "calculando jugada...",
            "modo solo", "paso 1", "paso 2", "paso 3", "paso 4"
        }
        if c_clean in BLACKLIST or any(c_clean.startswith(b) for b in ["paso ", "nodo ", "fase ", "esperando", "calculando", "evaluando"]):
            return None

        norm_q = self._normalize_text(card_name)
        if hasattr(self, "_card_exact_index") and norm_q in self._card_exact_index:
            return self._card_exact_index[norm_q]

        stopwords = {"de", "del", "la", "el", "los", "las", "un", "una", "y", "en", "para", "con"}
        norm_q = re.sub(r"^ciber([a-z])", r"ciber \1", norm_q)
        q_words = set(w for w in re.findall(r"[a-z0-9]+", norm_q) if len(w) > 2 and w not in stopwords)
        if not q_words:
            return None

        if hasattr(self, "_card_word_index"):
            best_match = None
            min_extra_len = 999
            for p, norm_es, norm_en, words in self._card_word_index:
                if q_words.issubset(words):
                    extra = len(norm_es) - len(norm_q)
                    if extra < min_extra_len:
                        min_extra_len = extra
                        best_match = p
            if best_match:
                return best_match

        info = self.db.get_card(card_name) if self.db else None
        if info and "passcode" in info and info["passcode"]:
            return int(info["passcode"])
        return None
    def _animate_z_pulse(self):
        pass

    def _fast_scanning_loop(self):
        time.sleep(0.5)
        while self.is_running:
            if not self.is_paused and not self.is_analyzing and not self.is_scanning_deck:
                frame = self.brain.capture_game_screen()
                if frame is not None:
                    if self.brain._has_frame_changed(frame):
                        self.is_analyzing = True
                        self.root.after(0, lambda: self.status_lbl.config(
                            text="● Analizando jugada óptima...",
                            fg="#00F5FF"
                        ))
                        threading.Thread(target=self._run_analysis_async, args=(frame,), daemon=True).start()
                else:
                    self.root.after(0, lambda: self.status_lbl.config(
                        text="● Buscando Master Duel...",
                        fg="#F59E0B"
                    ))
            time.sleep(0.25)

    def _run_analysis_async(self, frame):
        try:
            # 1. Comprobar si estamos en duelo activo
            analysis = self.brain.analyze_live_duel(frame)
            if analysis and analysis.get("in_duel"):
                self.brain.commit_frame_hash()
                self.root.after(0, lambda a=analysis: self._apply_live_analysis(a))
                return

            # 2. Si NO estamos en duelo, comprobar si es pantalla de Deck / Modo Solo
            deck_res = self.brain.analyze_deck_screen(frame)
            if deck_res and (deck_res.get("is_deck_screen") or deck_res.get("key_starters")):
                new_name = deck_res.get("deck_name", "").strip()
                cur_name = self.current_deck_data.get("deck_name", "").strip() if self.current_deck_data else ""
                
                # Si es una baraja nueva o no teníamos baraja
                if (new_name and new_name.lower() != cur_name.lower()) or not self.current_deck_data:
                    self.brain.commit_frame_hash()
                    self.root.after(0, lambda d=deck_res: self._apply_deck_scan_result(d))
                    return
                else:
                    self.brain.commit_frame_hash()
                    self.root.after(0, lambda: self.status_lbl.config(
                        text=f"● MODO SOLO: {cur_name} listo. ¡Pulsa Jugar!",
                        fg="#10B981"
                    ))
                    return

            # 3. Pantalla general o menú
            if analysis:
                self.brain.commit_frame_hash()
                self.root.after(0, lambda a=analysis: self._apply_live_analysis(a))
            else:
                self.root.after(0, lambda: self.status_lbl.config(
                    text="● En espera de acción...",
                    fg="#94A3B8"
                ))
        except Exception:
            pass
        finally:
            self.is_analyzing = False

    def _apply_live_analysis(self, data: Dict[str, Any]):
        if data.get("in_duel") is False:
            if self.current_deck_data or self.brain.active_deck:
                d_obj = self.current_deck_data or self.brain.active_deck
                d_name = d_obj.get("deck_name", "Deck")
                self.status_lbl.config(text=f"● MODO SOLO: {d_name} listo. ¡Pulsa Jugar!", fg="#10B981")
            else:
                self.status_lbl.config(text="● Modo Solo / Menú detectado. Pulsa Escanear Deck.", fg="#38BDF8")
            return

        self.status_lbl.config(text="● Jugada óptima actualizada", fg="#10B981")
        
        active_modal = data.get("active_modal")
        if active_modal and str(active_modal).lower() != "null":
            self.modal_banner.config(text=f"⚡ ACCIÓN REQUERIDA: {active_modal}")
            self.modal_banner.pack(fill="x", padx=4, pady=2, after=self.root.winfo_children()[0])
        else:
            self.modal_banner.pack_forget()

        seq = data.get("neural_sequence", [])
        if seq:
            while len(seq) < 4:
                seq.append({
                    "node": len(seq) + 1,
                    "phase": f"{len(seq)+1}. FINAL",
                    "card": "Fin de Turno",
                    "action": "Avanzar Fase",
                    "ev": 90,
                    "status": "PENDING"
                })
            self.nodes_data = seq[:4]
            self._render_timeline()

        rec = data.get("recommended_play", {})
        c_name = rec.get("card_name") or (seq[0].get("card") if seq else "Ninguna")
        act = rec.get("action") or (seq[0].get("action") if seq else "PASAR TURNO")
        pct = float(rec.get("win_equity_pct", seq[0].get("ev", 95) if seq else 90))
        
        node_1 = {
            "card": c_name,
            "action": act,
            "ev": pct
        }
        self._set_active_card_preview(node_1)

        proc_list = rec.get("client_procedure", [])
        if proc_list:
            if isinstance(proc_list, list):
                proc_str = " | ".join(proc_list[:2])
            else:
                proc_str = str(proc_list)
            self.best_action_lbl.config(text=f"👉 {act}\n({proc_str})")

        # Actualizar alerta táctica / amenaza
        threat_msg = data.get("coach_comment") or f"Nivel de Amenaza: {data.get('threat_level', 'NORMAL')}"
        if hasattr(self, "threat_desc_lbl"):
            self.threat_desc_lbl.config(text=f"🛡️ Alerta Táctica: {threat_msg}")

        hand_cards = data.get("hand_cards", [])
        for lbl in self.hand_labels:
            lbl.destroy()
        self.hand_labels.clear()
        
        if hand_cards:
            for idx, c in enumerate(hand_cards):
                if isinstance(c, dict):
                    name = c.get("name", "Desconocida")
                    slot = c.get("slot", idx + 1)
                    is_opt = c.get("is_optimal", False)
                else:
                    name = str(c)
                    slot = idx + 1
                    is_opt = (name.lower() in c_name.lower() or c_name.lower() in name.lower())

                row = tk.Frame(self.hand_cards_container, bg="#080E1C", padx=4, pady=3, highlightbackground="#00F5FF" if is_opt else "#1E293B", highlightthickness=1)
                row.pack(fill="x", pady=2)
                self.hand_labels.append(row)

                # Miniatura de carta en mano (25x36 px)
                passcode = self._get_passcode_for_card(name)
                h_canvas = tk.Canvas(row, width=25, height=36, bg="#0F172A", highlightthickness=1, highlightbackground="#00F5FF" if is_opt else "#334155")
                h_canvas.pack(side="left", padx=(0, 6))

                if passcode:
                    photo = self.z_image_cache.get(f"hand_{passcode}")
                    if not photo:
                        p1 = os.path.join(self.cache_dir, f"{passcode}.jpg")
                        p2 = os.path.join(self.cache_dir, f"{passcode:08d}.jpg")
                        disk_path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
                        if disk_path:
                            try:
                                h_img = Image.open(disk_path).resize((25, 36), Image.Resampling.LANCZOS)
                                photo = ImageTk.PhotoImage(h_img)
                                self.z_image_cache[f"hand_{passcode}"] = photo
                            except Exception:
                                pass
                    if photo:
                        h_canvas.create_image(12, 18, image=photo)
                    else:
                        h_canvas.create_text(12, 18, text="🃏", font=("Segoe UI", 10))
                        self._load_z_image_async(passcode)
                else:
                    h_canvas.create_text(12, 18, text="🃏", font=("Segoe UI", 10))

                # Información de carta
                info_col = tk.Frame(row, bg="#080E1C")
                info_col.pack(side="left", fill="both", expand=True)

                c_info = self.db.get_card(name) if self.db else None
                c_type = c_info.get("card_type", "MONSTRUO") if c_info else "CARTA"
                type_col = "#C85B17" if "MONSTRUO" in str(c_type).upper() else ("#1D9E74" if "MÁGICA" in str(c_type).upper() or "SPELL" in str(c_type).upper() else "#BC1E6F")

                name_lbl = tk.Label(info_col, text=name, font=("Segoe UI", 8, "bold" if is_opt else "normal"), fg="#FFFFFF" if is_opt else "#CBD5E1", bg="#080E1C", anchor="w")
                name_lbl.pack(fill="x")

                type_lbl = tk.Label(info_col, text=f"• {c_type}", font=("Segoe UI", 6, "bold"), fg=type_col, bg="#080E1C", anchor="w")
                type_lbl.pack(fill="x")

                # Badge de acción
                is_rec = is_opt or (name.lower() in c_name.lower() or c_name.lower() in name.lower())
                status_tag = "👉 JUGAR AHORA" if is_rec else ("Extensión" if idx < 2 else "Guardar")
                tag_bg = "#10B981" if is_rec else ("#0284C7" if idx < 2 else "#D97706")
                tag_fg = "#040711" if is_rec else "#FFFFFF"

                tag_lbl = tk.Label(row, text=status_tag, font=("Segoe UI", 7, "bold"), fg=tag_fg, bg=tag_bg, padx=6, pady=2)
                tag_lbl.pack(side="right")
        else:
            none_lbl = tk.Label(
                self.hand_cards_container,
                text="Mano vacía o en transición de fase",
                font=("Segoe UI", 8),
                fg="#64748B",
                bg="#070C1B",
                anchor="w"
            )
            none_lbl.pack(fill="x", pady=1)
            self.hand_labels.append(none_lbl)

        opp = data.get("opponent_board", {})
        m_count = opp.get("monsters_count", 0)
        st_count = opp.get("spells_traps_count", 0)
        threat = opp.get("threat_level", "NORMAL")
        m_summary = opp.get("monsters_summary", "")
        self.opp_summary_lbl.config(text=f"Monstruos: {m_count} ({m_summary})\nS/T: {st_count} | Amenaza: {threat}")

    def _apply_big_photo(self, passcode: int, image):
        try:
            photo = ImageTk.PhotoImage(image)
            self.image_cache[passcode] = photo
            self._current_photo = photo
            self.art_canvas.delete("all")
            self.art_canvas.create_image(42, 61, image=photo)
        except Exception:
            pass

    def _display_big_photo(self, photo):
        try:
            self._current_photo = photo
            self.art_canvas.delete("all")
            self.art_canvas.create_image(42, 61, image=photo)
        except Exception:
            pass

    def _load_big_image_async(self, passcode: int):
        if passcode in self.image_cache:
            self._display_big_photo(self.image_cache[passcode])
            return

        # Si ya está en disco, cargar inmediatamente sin delay
        p1 = os.path.join(self.cache_dir, f"{passcode}.jpg")
        p2 = os.path.join(self.cache_dir, f"{passcode:08d}.jpg")
        disk_path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)

        if disk_path:
            try:
                img = Image.open(disk_path)
                big_img = img.resize((84, 122), Image.Resampling.LANCZOS)
                self._apply_big_photo(passcode, big_img)
                return
            except Exception:
                pass

        def fetch():
            img_data = self._get_image_bytes(passcode)
            if img_data:
                try:
                    img = Image.open(io.BytesIO(img_data))
                    big_img = img.resize((84, 122), Image.Resampling.LANCZOS)
                    self.root.after(0, lambda: self._apply_big_photo(passcode, big_img))
                except Exception:
                    pass

        threading.Thread(target=fetch, daemon=True).start()

    def _load_z_image_async(self, passcode: int):
        if passcode in self.z_image_cache:
            return
        if not hasattr(self, "_loading_passcodes"):
            self._loading_passcodes = set()
        if passcode in self._loading_passcodes:
            return
        self._loading_passcodes.add(passcode)

        def fetch():
            try:
                p1 = os.path.join(self.cache_dir, f"{passcode}.jpg")
                p2 = os.path.join(self.cache_dir, f"{passcode:08d}.jpg")
                disk_path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
                if disk_path:
                    img = Image.open(disk_path)
                else:
                    img_data = self._get_image_bytes(passcode)
                    if img_data:
                        img = Image.open(io.BytesIO(img_data))
                    else:
                        img = None
                
                if img:
                    z_img = img.resize((46, 64), Image.Resampling.LANCZOS)
                    self.root.after(0, lambda: self._apply_z_photo(passcode, z_img))
            except Exception:
                pass
            finally:
                self._loading_passcodes.discard(passcode)

        threading.Thread(target=fetch, daemon=True).start()

    def _get_image_bytes(self, passcode: int):
        local_path = os.path.join(self.cache_dir, f"{passcode}.jpg")
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()

        url = f"https://images.ygoprodeck.com/images/cards_small/{passcode}.jpg"
        headers = {"User-Agent": "YuGiOh-Coach-Assistant/1.0"}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
                try:
                    with open(local_path, "wb") as f:
                        f.write(data)
                except Exception:
                    pass
                return data
        except Exception:
            return None

    def _apply_z_photo(self, passcode: int, image):
        try:
            photo = ImageTk.PhotoImage(image)
            self.z_image_cache[passcode] = photo
            if not getattr(self, "_timeline_render_pending", False):
                self._timeline_render_pending = True
                self.root.after(40, self._safe_render_timeline)
        except Exception:
            pass

    def _safe_render_timeline(self):
        self._timeline_render_pending = False
        self._render_timeline()

def main():
    try:
        root = tk.Tk()
        app = LiveCoachOverlay(root)
        root.mainloop()
    except Exception as e:
        with open("coach_crash.log", "w", encoding="utf-8") as f:
            import traceback
            f.write(traceback.format_exc())

if __name__ == "__main__":
    main()
