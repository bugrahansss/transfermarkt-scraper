"""Fetch Transfermarkt pages through the Scrape.do API.

Transfermarkt serves plain server-rendered HTML, so one script with ``requests`` works for a few
pages. Crawling a league (or several) from one IP is where it stops: Transfermarkt rate-limits
heavy traffic and blocks cloud IP ranges. Scrape.do sends each request from a rotating pool, so a
crawl of every squad in a league goes through. Each page costs 1 Scrape.do credit.
"""

from __future__ import annotations

import os
import time
from typing import Iterator, List, Optional

import requests

from .parser import (
    Club,
    Competition,
    Player,
    PlayerProfile,
    competition_url,
    parse_competition,
    parse_player,
    parse_squad,
    player_url,
    squad_url,
)

API_URL = "https://api.scrape.do/"
TOKEN_ENV = "SCRAPEDO_TOKEN"


class ScrapeError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class Transfermarkt:
    """Read Transfermarkt competitions, squads and player profiles.

    >>> tm = Transfermarkt(token="YOUR_SCRAPEDO_TOKEN")
    >>> league = tm.competition("GB1")
    >>> for club in league.clubs:
    ...     print(club.name, club.total_market_value)
    >>> players = tm.squad(281)
    """

    def __init__(self, token: Optional[str] = None, timeout: float = 60.0, retries: int = 2,
                 session: Optional[requests.Session] = None):
        self.token = token or os.environ.get(TOKEN_ENV, "")
        if not self.token:
            raise ValueError(f"A Scrape.do API token is required. Pass token=... or set {TOKEN_ENV}.")
        self.timeout = timeout
        self.retries = max(0, retries)
        self.session = session or requests.Session()
        self.requests_made = 0

    def fetch(self, url: str) -> str:
        params = {"token": self.token, "url": url}
        last: Optional[ScrapeError] = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(API_URL, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last = ScrapeError(f"Request failed: {exc}")
            else:
                self.requests_made += 1
                if response.status_code == 200 and "Transfermarkt" in response.text:
                    return response.text
                last = ScrapeError(f"Request for {url} failed with status {response.status_code}",
                                   response.status_code)
                if response.status_code in (400, 401, 404, 410):
                    break
            if attempt < self.retries:
                time.sleep(2 * (attempt + 1))
        assert last is not None
        raise last

    def competition(self, code: str, season: Optional[int] = None) -> Competition:
        """Clubs of a competition (``GB1`` Premier League, ``ES1`` LaLiga, ``L1`` Bundesliga, ``TR1`` Süper Lig...)."""
        return parse_competition(self.fetch(competition_url(code, season)), code.upper())

    def squad(self, club_id: int, season: Optional[int] = None) -> List[Player]:
        """Every player of a club's squad, from the detailed squad view."""
        return parse_squad(self.fetch(squad_url(club_id, season)), int(club_id))

    def player(self, player_id: int) -> PlayerProfile:
        profile = parse_player(self.fetch(player_url(player_id)), int(player_id))
        if profile is None:
            raise ScrapeError(f"No player profile on {player_url(player_id)}")
        return profile

    def league_players(self, code: str, season: Optional[int] = None, clubs: int = 0) -> Iterator[Player]:
        """Every player of every club in a competition: 1 request for the clubs plus 1 per club."""
        league = self.competition(code, season)
        for n, club in enumerate(league.clubs):
            if clubs and n >= clubs:
                break
            yield from self.squad(club.id, season or club.season)

    @property
    def credits_used(self) -> int:
        return self.requests_made
