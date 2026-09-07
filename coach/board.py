"""
Field Board Renderer for Master Duel Coach.
Dibuja el diagrama de campo con ancho fijo y convenciones exactas.
"""

from typing import List, Dict, Optional

class BoardDiagram:
    @staticmethod
    def render(
        rival_lp: int = 8000,
        my_lp: int = 8000,
        rival_hand_count: int = 5,
        my_hand: List[str] = None,
        my_deck_count: int = 35,
        rival_emz: List[str] = None,
        my_emz: List[str] = None,
        rival_mz: List[str] = None,
        my_mz: List[str] = None,
        rival_st: List[str] = None,
        my_st: List[str] = None,
        rival_gy: str = "-",
        my_gy: str = "-",
        rival_banish: str = "-",
        my_banish: str = "-",
        active_card: Optional[str] = None,
        target_zone: Optional[str] = None
    ) -> str:
        my_hand = my_hand or []
        rival_emz = rival_emz or ["-", "-"]
        my_emz = my_emz or ["-", "-"]
        rival_mz = rival_mz or ["-"] * 5
        my_mz = my_mz or ["-"] * 5
        rival_st = rival_st or ["-"] * 5
        my_st = my_st or ["-"] * 5

        def fmt_cell(val: str, zone_name: str) -> str:
            if target_zone and zone_name == target_zone:
                return f">>{val}<<"
            if active_card and val == active_card:
                return f"*{val}*"
            return val

        r_emz_str = f"[{fmt_cell(rival_emz[0], 'R_EMZ1')}] [{fmt_cell(rival_emz[1], 'R_EMZ2')}]"
        r_mz_str = " ".join(f"[{fmt_cell(rival_mz[i], f'R_M{i+1}')}]" for i in range(5))
        r_st_str = " ".join(f"[{fmt_cell(rival_st[i], f'R_S{i+1}')}]" for i in range(5))

        m_emz_str = f"[{fmt_cell(my_emz[0], 'M_EMZ1')}] [{fmt_cell(my_emz[1], 'M_EMZ2')}]"
        m_mz_str = " ".join(f"[{fmt_cell(my_mz[i], f'M_M{i+1}')}]" for i in range(5))
        m_st_str = " ".join(f"[{fmt_cell(my_st[i], f'M_S{i+1}')}]" for i in range(5))

        hand_str = " | ".join(my_hand) if my_hand else "Vacía"

        diagram = (
            f"```text\n"
            f"RIVAL  LP: {rival_lp} | Mano: {rival_hand_count}\n"
            f"EMZ: {r_emz_str}\n"
            f"M/Z: {r_mz_str}\n"
            f"S/T: {r_st_str}\n"
            f"GY: {rival_gy} | Banish: {rival_banish}\n"
            f"──────────── campo ────────────\n"
            f"EMZ: {m_emz_str}\n"
            f"M/Z: {m_mz_str}\n"
            f"S/T: {m_st_str}\n"
            f"GY: {my_gy} | Banish: {my_banish}\n"
            f"TÚ     LP: {my_lp} | Mano: {len(my_hand)} | Deck: {my_deck_count}\n"
            f"MANO:  {hand_str}\n"
            f"```\n"
        )
        return diagram
