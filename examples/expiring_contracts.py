"""Every player in a league whose contract runs out next summer, most valuable first.

    SCRAPEDO_TOKEN=... python examples/expiring_contracts.py GB1 2027
"""

import csv
import sys

from transfermarkt_scraper import Transfermarkt

code = sys.argv[1] if len(sys.argv) > 1 else "GB1"
year = sys.argv[2] if len(sys.argv) > 2 else "2027"
tm = Transfermarkt()

expiring = [p for p in tm.league_players(code) if p.contract_until.startswith(year)]
expiring.sort(key=lambda p: -(p.market_value_eur or 0))

with open(f"{code.lower()}_contracts_{year}.csv", "w", newline="", encoding="utf-8") as fh:
    fields = ["name", "club_name", "position", "age", "market_value", "contract_until", "url"]
    writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(p.to_dict() for p in expiring)

total = sum(p.market_value_eur or 0 for p in expiring)
print(f"{len(expiring)} players, €{total / 1e9:.2f}bn of market value, {tm.credits_used} credits", file=sys.stderr)
