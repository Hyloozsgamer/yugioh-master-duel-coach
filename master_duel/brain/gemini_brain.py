"""
Gemini Multimodal Brain for Yu-Gi-Oh! Master Duel
Analiza visualmente la pantalla 16:9 de Master Duel con razonamiento táctico rápido:
- Reglas estrictas de combate Yu-Gi-Oh! (cálculo de daño, comparación de ATK y prevención de ataques suicidas).
- Modo de respuesta rápida (sin sobrecarga de pensamiento innecesaria).
- Navegación por Modo Solo y resolución de cadenas/prompts.
"""

import os
import sys
import json
import base64
import time
import re
import logging
import urllib.request
import urllib.error
import cv2
import numpy as np
from typing import Optional, Dict, Any

log = logging.getLogger("MD_GeminiBrain")


class MasterDuelBrain:
    """Cerebro multimodal optimizado para Yu-Gi-Oh! Master Duel."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.model = model or self._load_model() or "gemini-3.7-flash"
        
        # Pool de modelos con fallback automático
        pool = [self.model, "gemini-3.7-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash"]
        self.models_pool = []
        for m in pool:
            if m and m not in self.models_pool:
                self.models_pool.append(m)
        self.current_model_idx = 0

        self._last_call_time = 0.0
        self._min_interval = 2.0  # Mínimo 2 segundos entre consultas para evitar agotar cuota
        self._rate_limited_until = 0.0
        self._last_frame_hash = None

    def _load_api_key(self) -> str:
        env_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        ]
        for env_path in env_paths:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY="):
                            return line.split("=", 1)[1].strip()
        return os.environ.get("GEMINI_API_KEY", "")

    def _load_model(self) -> str:
        env_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        ]
        for env_path in env_paths:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_MODEL="):
                            return line.split("=", 1)[1].strip()
        return "gemini-3.7-flash"

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        if time.time() < self._rate_limited_until:
            return False
        return True

    def _compress_frame(self, frame: np.ndarray, target_width: int = 854) -> str:
        """Comprime el frame respetando la relación 16:9 para envío ultrarrápido."""
        h, w = frame.shape[:2]
        new_w = target_width
        new_h = int(h * (new_w / w))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        _, buf = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 68])
        return base64.b64encode(buf).decode('utf-8')

    def consult(self, frame: np.ndarray, current_state: str = "UNKNOWN", extra_context: str = "") -> Optional[Dict[str, Any]]:
        """Envía el frame a Gemini y retorna la decisión táctica en JSON."""
        if not self.api_key:
            log.warning("Gemini API Key no configurada.")
            return None

        now = time.time()
        if now < self._rate_limited_until:
            rem = int(self._rate_limited_until - now)
            log.info(f"⏳ Enfriando peticiones Gemini tras límite de cuota ({rem}s restantes)...")
            return None

        # Control de cadencia para no saturar los 15 RPM de la API
        elapsed = now - self._last_call_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        img_b64 = self._compress_frame(frame)

        system_instruction = (
            "You are a MASTER competitive Yu-Gi-Oh! AI playing Yu-Gi-Oh! Master Duel on PC in Solo Mode / PvE.\n"
            "Resolution: 16:9 aspect ratio. Coordinates x and y are normalized [0.00 to 1.00].\n\n"
            "### PRO-LEVEL DUEL TACTICS & SEQUENCING (FOLLOW EXACT ORDER):\n"
            "1. SEQUENCING - PLAY SEARCH SPELLS FIRST:\n"
            "   - If you have Search or Draw Spells (e.g., 'Gladiator Proving Ground', 'Reinforcement of the Army', Pot spells):\n"
            "     ALWAYS activate them FIRST before Normal Summoning! This puts your best monster into your hand.\n"
            "   - NEVER set Normal Spells face-down (especially 'Monster Reborn' when no monsters are in GY yet).\n\n"
            "2. SMART MONSTER SUMMONING (ATK vs DEF):\n"
            "   - Always check the monster's ATK and DEF numbers:\n"
            "     * HIGH ATK (>= 1600): Summon in ATTACK position.\n"
            "     * HIGH DEF & LOW ATK (e.g., 800 ATK / 2000 DEF like Attorix): Summon or Set in DEFENSE position so it walls opponent attacks instead of giving them free damage!\n"
            "   - EXTRA DECK: If the Extra Deck (bottom-left corner ~x=0.08, y=0.88) is glowing blue/gold/purple, check if you can Contact Fuse, Link, or XYZ summon your boss monster!\n\n"
            "3. SET TRAPS BEFORE PASSING:\n"
            "   - Before passing turn, click Trap Cards (pink) and Quick-Play Spells in hand and select 'Set' to protect yourself during opponent's turn.\n\n"
            "4. TURN 1 (GOING FIRST) RESTRICTION:\n"
            "   - On Turn 1 (First turn of the duel), Battle Phase DOES NOT EXIST in Yu-Gi-Oh!.\n"
            "   - After summoning and setting traps, DO NOT search for battle; click the Phase button (x=0.77, y=0.46) to pass directly to End Phase.\n\n"
            "5. BATTLE PHASE (GOING SECOND OR LATER - NO SUICIDE ATTACKS):\n"
            "   - ALWAYS compare your monster's ATK vs the opponent's monster's ATK.\n"
            "   - STRICT PROHIBITION: NEVER attack an enemy monster whose ATK is HIGHER or EQUAL to yours!\n"
            "     (e.g., Never attack a 1900/2000 ATK monster with a 600/800 ATK monster. That is suicide).\n"
            "   - ONLY attack if:\n"
            "     a) Opponent has ZERO monsters (Direct Attack).\n"
            "     b) Your ATK > Opponent ATK (if enemy is in Attack position).\n"
            "     c) Your ATK > Opponent DEF (if enemy is in Defense position).\n"
            "   - If you cannot beat their monsters: DO NOT ATTACK! Switch your monsters to Defense and click 'End Phase' (x=0.91, y=0.92).\n\n"
            "6. CHAIN & PROMPTS:\n"
            "   - When your Trap (like 'War Chariot') or Quick effect asks to activate in response to opponent: Click 'Activate' (blue/gold) to negate/destroy their play.\n\n"
            "Output ONLY a valid JSON object in this exact format with NO markdown commentary outside:\n"
            "```json\n"
            "{\n"
            "  \"action\": \"CLICK\",\n"
            "  \"target\": \"Name of card or button\",\n"
            "  \"x\": 0.50,\n"
            "  \"y\": 0.50,\n"
            "  \"summary\": \"Tactical explanation\"\n"
            "}\n"
            "```"
        )

        prompt_text = f"Game State: {current_state}\n{extra_context}\nDetermine the next best tactical action immediately."

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_instruction + "\n" + prompt_text},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": img_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        num_models = len(self.models_pool)
        for attempt in range(num_models):
            idx = (self.current_model_idx + attempt) % num_models
            model_name = self.models_pool[idx]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

            # Si el modelo no es 3.7, remover thinkingConfig si diera error
            curr_payload = payload
            if "3.7" not in model_name and "thinkingConfig" in curr_payload["generationConfig"]:
                curr_payload = json.loads(json.dumps(payload))
                del curr_payload["generationConfig"]["thinkingConfig"]

            req = urllib.request.Request(
                url,
                data=json.dumps(curr_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            try:
                t0 = time.time()
                self._last_call_time = t0
                with urllib.request.urlopen(req, timeout=12) as response:
                    raw_res = json.loads(response.read().decode("utf-8"))
                    latency = round(time.time() - t0, 2)
                    raw_text = raw_res["candidates"][0]["content"]["parts"][0]["text"]

                    # Extraer bloque JSON
                    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
                    if match:
                        try:
                            dec = json.loads(match.group(1))
                            log.info(f"💡 Gemini ({model_name}, {latency}s): {dec.get('summary')} -> {dec.get('target')} @ ({dec.get('x')}, {dec.get('y')})")
                            self.current_model_idx = idx
                            return dec
                        except Exception:
                            pass

                    match = re.search(r"\{[^{}]*\}", raw_text, re.DOTALL)
                    if match:
                        try:
                            dec = json.loads(match.group(0))
                            log.info(f"💡 Gemini ({model_name}, {latency}s): {dec.get('summary')} -> {dec.get('target')} @ ({dec.get('x')}, {dec.get('y')})")
                            self.current_model_idx = idx
                            return dec
                        except Exception:
                            pass

                    log.warning(f"Respuesta no JSON de {model_name}: {raw_text[:100]}")

            except urllib.error.HTTPError as e:
                if e.code in (429, 503):
                    log.warning(f"⚠️ Modelo {model_name} devolvió {e.code}. Probando siguiente modelo...")
                    continue
                elif e.code == 400 and "thinkingConfig" in str(e):
                    # Si falla por thinkingConfig, intentar sin él
                    continue
                else:
                    log.error(f"HTTP Error {e.code} con {model_name}: {e}")
                    continue
            except Exception as ex:
                log.error(f"Error consultando Gemini ({model_name}): {ex}")
                continue

        # Si todos agotaron cuota temporal
        self._rate_limited_until = time.time() + 30.0
        log.warning("⏳ Cuota gratuita en espera. Enfriando peticiones por 30s...")
        return None
