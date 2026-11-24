from pathlib import Path

import pytest

from transfermarkt_scraper import (
    Transfermarkt,
    competition_url,
    money,
    parse_competition,
    parse_player,
    parse_squad,
    player_url,
    squad_url,
)

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_money():
    assert money("€1.50B") == 1_500_000_000
    assert money("€45.00M") == 45_000_000
    assert money("€300.0K") == 300_000
    assert money("-") is None
    assert money("") is None


def test_urls():
    assert competition_url("gb1") == "https://www.transfermarkt.com/-/startseite/wettbewerb/GB1"
    assert competition_url("GB1", 2025).endswith("/wettbewerb/GB1/saison_id/2025")
    assert squad_url(281, 2026) == "https://www.transfermarkt.com/-/kader/verein/281/saison_id/2026/plus/1"
    assert squad_url(281) == "https://www.transfermarkt.com/-/kader/verein/281/plus/1"
    assert player_url(990002) == "https://www.transfermarkt.com/-/profil/spieler/990002"


def test_competition():
    league = parse_competition(load("competition.html"))
    assert league.code == "EX1"
    assert league.name == "Example League"
    assert league.season == 2026
    assert league.total_market_value_eur == 1_330_000_000
    assert [c.id for c in league.clubs] == [900001, 900002, 900003]
    first, second, third = league.clubs
    assert first.name == "Example FC" and first.squad_size == 25 and first.average_age == 26.1
    assert first.foreigners == 12 and first.total_market_value_eur == 1_000_000_000
    assert second.name == "Exemple Athletic & Co"
    assert third.average_market_value_eur == 900_000
    assert first.squad_url.endswith("/kader/verein/900001/saison_id/2026/plus/1")


def test_squad():
    players = parse_squad(load("squad.html"))
    assert [p.id for p in players] == [990001, 990002, 990003]
    jane, john, alex = players
    assert jane.club_id == 900001 and jane.club_name == "Example FC" and jane.season == 2026
    assert jane.number == 1 and jane.position == "Goalkeeper" and jane.position_group == "Goalkeeper"
    assert jane.date_of_birth == "1998-02-01" and jane.age == 28
    assert jane.height_m == 1.90 and jane.foot == "right"
    assert jane.signed_from == "Sample Rovers" and jane.signed_from_club_id == 900003
    assert jane.transfer_fee == "€5.00M" and jane.contract_until == "2029-06-30"
    assert jane.market_value_eur == 12_000_000
    assert john.nationalities == ["Exampleland", "Samplestan"]
    assert john.signed_from == "Exemple Athletic & Co" and john.transfer_fee == "free transfer"
    assert john.market_value_eur == 850_000 and john.position_group == "Defender"


def test_squad_missing_values():
    alex = parse_squad(load("squad.html"))[2]
    assert alex.number is None
    assert alex.date_of_birth == "2008-03-03" and alex.age == 18
    assert alex.height_m is None and alex.foot == ""
    assert alex.joined == "" and alex.signed_from == "" and alex.contract_until == ""
    assert alex.market_value == "" and alex.market_value_eur is None
    assert alex.to_dict()["nationalities"] == "Samplestan"


def test_player():
    p = parse_player(load("player.html"))
    assert p.id == 990002 and p.name == "John Doe"
    assert p.full_name == "Johnathan Example Doe"
    assert p.date_of_birth == "2003-11-15" and p.age == 22
    assert p.place_of_birth == "Example City"
    assert p.height_m == 1.85
    assert p.citizenship == ["Exampleland", "Samplestan"]
    assert p.position == "Defender - Centre-Back" and p.foot == "left"
    assert p.agent == "Example Agency"
    assert p.current_club == "Example FC" and p.current_club_id == 900001
    assert p.joined == "2026-01-10" and p.contract_expires == "2031-06-30"
    assert p.market_value == "€850.0K" and p.market_value_eur == 850_000
    assert p.market_value_updated == "2026-10-05"


def test_player_missing():
    assert parse_player("<html><body>nothing</body></html>", 1) is None


class FakeResponse:
    def __init__(self, text, status=200):
        self.text, self.status_code = text, status


class FakeSession:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params["url"])
        for key, (status, body) in self.pages.items():
            if key in params["url"]:
                return FakeResponse(body, status)
        return FakeResponse("not found", 404)


def test_client_league_players():
    session = FakeSession({"/wettbewerb/EX1": (200, load("competition.html")),
                           "/kader/verein/": (200, load("squad.html"))})
    tm = Transfermarkt(token="t", session=session)
    players = list(tm.league_players("EX1", clubs=2))
    assert len(players) == 6
    assert tm.credits_used == 3
    assert session.calls[1].endswith("/kader/verein/900001/saison_id/2026/plus/1")


def test_client_player_and_errors():
    session = FakeSession({"/profil/spieler/990002": (200, load("player.html"))})
    tm = Transfermarkt(token="t", session=session, retries=0)
    assert tm.player(990002).name == "John Doe"
    with pytest.raises(Exception):
        tm.player(1)


def test_token_required(monkeypatch):
    monkeypatch.delenv("SCRAPEDO_TOKEN", raising=False)
    with pytest.raises(ValueError):
        Transfermarkt()
