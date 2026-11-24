"""Command line: transfermarkt-scraper clubs GB1 | squad 281 | league GB1 | player 392757"""

from __future__ import annotations

import argparse
import csv
import json
import sys

from .client import Transfermarkt
from .parser import CLUB_FIELDS, PLAYER_FIELDS, PROFILE_FIELDS


def write(rows, fields, fmt, out):
    if fmt == "csv":
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    else:
        json.dump(rows, out, ensure_ascii=False, indent=2)
        out.write("\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="transfermarkt-scraper",
                                description="Scrape Transfermarkt through the Scrape.do API (token in SCRAPEDO_TOKEN).")
    p.add_argument("command", choices=["clubs", "squad", "league", "player"],
                   help="clubs: a competition's clubs; squad: a club's players; league: every player of a "
                        "competition; player: a player profile")
    p.add_argument("ids", nargs="+", help="Competition codes (GB1, ES1, L1, IT1, FR1, TR1...), club IDs or player IDs")
    p.add_argument("--season", type=int, help="Season start year, e.g. 2026 for 26/27 (default: current)")
    p.add_argument("--clubs", type=int, default=0, help="league: stop after N clubs (0 = all)")
    p.add_argument("-f", "--format", choices=["json", "csv"], default="json")
    p.add_argument("-o", "--output", help="Output file (default: stdout)")
    p.add_argument("--token", help="Scrape.do token (default: SCRAPEDO_TOKEN)")
    args = p.parse_args(argv)

    tm = Transfermarkt(token=args.token)
    rows, fields = [], PLAYER_FIELDS
    for value in args.ids:
        if args.command == "clubs":
            fields = ["competition"] + CLUB_FIELDS
            league = tm.competition(value, args.season)
            rows += [dict(competition=league.code, **c.to_dict()) for c in league.clubs]
        elif args.command == "squad":
            rows += [pl.to_dict() for pl in tm.squad(int(value), args.season)]
        elif args.command == "league":
            rows += [pl.to_dict() for pl in tm.league_players(value, args.season, args.clubs)]
        else:
            fields = PROFILE_FIELDS
            rows.append(tm.player(int(value)).to_dict())
        print(f"{value}: {len(rows)} rows so far", file=sys.stderr)

    out = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        write(rows, fields, args.format, out)
    finally:
        if args.output:
            out.close()
    print(f"{len(rows)} rows, {tm.credits_used} Scrape.do credits", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
