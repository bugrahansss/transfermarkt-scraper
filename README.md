# Transfermarkt Scraper

[![PyPI](https://img.shields.io/pypi/v/transfermarkt-scraper)](https://pypi.org/project/transfermarkt-scraper/)
[![Python](https://img.shields.io/pypi/pyversions/transfermarkt-scraper)](https://pypi.org/project/transfermarkt-scraper/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Scrape [Transfermarkt](https://www.transfermarkt.com) into structured data. Pull **every club in a league** (squad size, average age, foreigners, average and total market value), **every player in a squad** (shirt number, position, date of birth, nationalities, height, foot, joined date, previous club and transfer fee, contract end, market value in euros) and **player profiles** (full name, birthplace, citizenship, agent, contract, current market value and when it was last updated). JSON or CSV.

```bash
pip install transfermarkt-scraper
export SCRAPEDO_TOKEN=your_token
transfermarkt-scraper clubs GB1 -f csv -o premier_league_clubs.csv     # 20 clubs, 1 credit
transfermarkt-scraper squad 281 -f csv -o man_city.csv                 # one squad, 1 credit
transfermarkt-scraper league GB1 -f csv -o premier_league_players.csv  # every player, 21 credits
transfermarkt-scraper player 418560                                    # one profile
```

## Why go through an API

Transfermarkt serves plain server-rendered HTML, so a few `requests.get` calls from your laptop work. Crawling whole leagues, every season, from one server is where scrapers get throttled and their IPs blocked. This package sends each request through [Scrape.do](https://scrape.do/?utm_source=github&utm_medium=readme&utm_campaign=transfermarkt-scraper), which rotates the IP for you: **1 credit per page**, no extra parameters.

## Where the data is

* **Competition** (`/-/startseite/wettbewerb/GB1`, optionally `/saison_id/2025`): a `table.items` with one row per club (crest, name, squad size, average age, foreigners, average and total market value) and a `tfoot` with the league total.
* **Detailed squad** (`/-/kader/verein/281/saison_id/2026/plus/1`): the `plus/1` view adds height, foot, joined date, previous club and contract end. The previous club's link title carries the fee (`"Paris Saint-Germain: Ablöse €30.00M"`), the row's `bg_Torwart|Abwehr|Mittelfeld|Sturm` class carries the position group.
* **Player profile** (`/-/profil/spieler/392757`): the `info-table` label/value pairs and the market value box with its last update date.

Transfermarkt ignores the slug in its URLs, so `-` works everywhere and only the numeric IDs matter.

In a live test the 20 Premier League clubs gave **548 players for 21 credits**, worth **€14.11bn** together (the same total Transfermarkt prints under the league table). 101 of them have a contract that runs out in 2027, worth €1.02bn, and 93 are 21 or younger, worth €2.48bn.

## Python

```python
from transfermarkt_scraper import Transfermarkt

tm = Transfermarkt(token="YOUR_SCRAPEDO_TOKEN")   # or set SCRAPEDO_TOKEN

league = tm.competition("GB1")                    # ES1, L1, IT1, FR1, TR1, NL1, PO1, GB2, MLS1 ...
for club in league.clubs:
    print(club.id, club.name, club.squad_size, club.total_market_value)

for p in tm.squad(281):                           # Manchester City
    print(p.number, p.name, p.position, p.age, p.market_value_eur, p.contract_until)

profile = tm.player(418560)
print(profile.full_name, profile.agent, profile.market_value, profile.market_value_updated)

players = list(tm.league_players("GB1", season=2026))
print(len(players), tm.credits_used)
```

`examples/expiring_contracts.py` writes every player in a league whose contract ends in a given year, most valuable first.

## Fields

**Club:** `id`, `name`, `squad_size`, `average_age`, `foreigners`, `average_market_value`, `average_market_value_eur`, `total_market_value`, `total_market_value_eur`, `season`, `url`, `squad_url`.

**Player:** `id`, `name`, `number`, `position`, `position_group` (Goalkeeper, Defender, Midfield, Attack), `date_of_birth`, `age`, `nationalities`, `height_m`, `foot`, `joined`, `signed_from`, `signed_from_club_id`, `transfer_fee`, `contract_until`, `market_value`, `market_value_eur`, `club_id`, `club_name`, `season`, `url`.

**Player profile:** `id`, `name`, `full_name`, `date_of_birth`, `age`, `place_of_birth`, `height_m`, `citizenship`, `position`, `foot`, `agent`, `current_club`, `current_club_id`, `joined`, `contract_expires`, `market_value`, `market_value_eur`, `market_value_updated`, `url`.

Dates are ISO (`2030-06-30`). Market values are Transfermarkt's estimates, not fees paid.

## Use it responsibly

Transfermarkt's data is the work of its editors and community. Keep request rates reasonable, respect its terms of use, don't republish player photos, and credit Transfermarkt when you publish analysis built on its numbers. Players are people: use the personal fields (date of birth, birthplace) only where you need them. This is not legal advice.

## Tests

```bash
pip install pytest
PYTHONPATH=src pytest
```

The fixtures are fictional ("Example FC", "Jane Doe", example.com).

## License

MIT
