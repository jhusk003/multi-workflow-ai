"""Tiny, dependency-free Streamlit V1 component for Seller Assist Explore Mode."""
from pathlib import Path
import streamlit.components.v1 as components

FRONTEND = Path(__file__).resolve().parent / "town_game_frontend"
_town = components.declare_component("seller_assist_explore_v21", path=str(FRONTEND))


def explore_town(kind: str, outfit: str, nickname: str, position: dict):
    """Return a building-enter/save event, or None. Movement stays in the browser."""
    return _town(
        kind=kind,
        outfit=outfit,
        nickname=nickname,
        position=position,
        key="seller_assist_explore_game",
        default=None,
    )
