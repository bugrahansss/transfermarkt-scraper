"""Scrape Transfermarkt competitions, squads, market values and player profiles with Python."""

from .client import ScrapeError, Transfermarkt
from .parser import (
    CLUB_FIELDS,
    PLAYER_FIELDS,
    PROFILE_FIELDS,
    Club,
    Competition,
    Player,
    PlayerProfile,
    competition_url,
    money,
    parse_competition,
    parse_player,
    parse_squad,
    player_url,
    squad_url,
)

__version__ = "0.1.0"
__all__ = [
    "Transfermarkt", "ScrapeError", "Club", "Competition", "Player", "PlayerProfile",
    "parse_competition", "parse_squad", "parse_player", "competition_url", "squad_url", "player_url",
    "money", "CLUB_FIELDS", "PLAYER_FIELDS", "PROFILE_FIELDS",
]
