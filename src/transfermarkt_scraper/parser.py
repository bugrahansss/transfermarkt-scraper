"""Parsers for Transfermarkt's server-rendered pages.

* Competition page (``/-/startseite/wettbewerb/GB1``): every club with squad size, average age,
  foreigners, average and total market value.
* Detailed squad (``/-/kader/verein/281/saison_id/2026/plus/1``): every player with shirt number,
  position, date of birth, nationalities, height, foot, joined date, previous club and fee,
  contract end and market value.
* Player profile (``/-/profil/spieler/392757``): the info table plus current market value.

Transfermarkt accepts any slug in its URLs, so ``-`` works everywhere and only the numeric IDs matter.
"""

from __future__ import annotations

import html as htmllib
import re
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

BASE = "https://www.transfermarkt.com"


# ---- helpers -------------------------------------------------------------------

def text(fragment: str) -> str:
    fragment = re.sub(r"<!--.*?-->", "", fragment or "", flags=re.S)
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", htmllib.unescape(fragment).replace("\xa0", " ")).strip()


def money(value: str) -> Optional[int]:
    """'€1.50B' -> 1500000000, '€45.00M' -> 45000000, '€300.0K' -> 300000, '-' -> None."""
    v = (value or "").replace("\xa0", " ").replace(" ", "")
    m = re.search(r"([\d.,]+)(bn|B|m|M|Th\.|k|K)?", v)
    if not m or not re.search(r"\d", m.group(1)):
        return None
    number = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    factor = {"bn": 1e9, "b": 1e9, "m": 1e6, "th.": 1e3, "k": 1e3}.get(unit, 1)
    return int(round(number * factor))


def date_iso(value: str) -> str:
    """'25/02/1999' or 'Feb 25, 1999' -> '1999-02-25'. Anything else is returned as-is."""
    v = (value or "").strip()
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", v)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", v)
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    if m and m.group(1) in months:
        return f"{m.group(3)}-{months.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}"
    return "" if v in ("-", "") else v


def to_int(value: str) -> Optional[int]:
    m = re.search(r"-?\d+", value or "")
    return int(m.group(0)) if m else None


def to_float(value: str) -> Optional[float]:
    m = re.search(r"\d+(?:[.,]\d+)?", value or "")
    return float(m.group(0).replace(",", ".")) if m else None


def competition_url(code: str, season: Optional[int] = None) -> str:
    url = f"{BASE}/-/startseite/wettbewerb/{code.upper()}"
    return f"{url}/saison_id/{season}" if season else url


def squad_url(club_id: int, season: Optional[int] = None) -> str:
    url = f"{BASE}/-/kader/verein/{int(club_id)}"
    return f"{url}/saison_id/{season}/plus/1" if season else f"{url}/plus/1"


def player_url(player_id: int) -> str:
    return f"{BASE}/-/profil/spieler/{int(player_id)}"


def _id(href: str, kind: str) -> Optional[int]:
    m = re.search(rf"/{kind}/(\d+)", href or "")
    return int(m.group(1)) if m else None


def _items_body(html: str) -> str:
    i = html.find('<table class="items">')
    if i < 0:
        return ""
    j = html.find("<tbody>", i)
    k = html.find("</tbody>", j)
    return html[j:k] if j >= 0 and k >= 0 else ""


def _rows(body: str) -> List[str]:
    """Top-level <tr class="odd|even"> rows; nested inline tables stay inside their row."""
    return re.split(r'<tr class="(?:odd|even)">', body)[1:]


def _season(html: str) -> Optional[int]:
    m = re.search(r"saison_id/(\d{4})", html or "")
    return int(m.group(1)) if m else None


# ---- data ----------------------------------------------------------------------

@dataclass
class Club:
    id: int
    name: str
    squad_size: Optional[int]
    average_age: Optional[float]
    foreigners: Optional[int]
    average_market_value: str
    average_market_value_eur: Optional[int]
    total_market_value: str
    total_market_value_eur: Optional[int]
    season: Optional[int]
    url: str
    squad_url: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Competition:
    code: str
    name: str
    season: Optional[int]
    clubs: List[Club] = field(default_factory=list)
    total_market_value: str = ""
    total_market_value_eur: Optional[int] = None


@dataclass
class Player:
    id: int
    name: str
    number: Optional[int]
    position: str
    position_group: str
    date_of_birth: str
    age: Optional[int]
    nationalities: List[str]
    height_m: Optional[float]
    foot: str
    joined: str
    signed_from: str
    signed_from_club_id: Optional[int]
    transfer_fee: str
    contract_until: str
    market_value: str
    market_value_eur: Optional[int]
    club_id: Optional[int]
    club_name: str
    season: Optional[int]
    url: str

    def to_dict(self) -> Dict:
        row = asdict(self)
        row["nationalities"] = ", ".join(self.nationalities)
        return row


@dataclass
class PlayerProfile:
    id: int
    name: str
    full_name: str
    date_of_birth: str
    age: Optional[int]
    place_of_birth: str
    height_m: Optional[float]
    citizenship: List[str]
    position: str
    foot: str
    agent: str
    current_club: str
    current_club_id: Optional[int]
    joined: str
    contract_expires: str
    market_value: str
    market_value_eur: Optional[int]
    market_value_updated: str
    url: str

    def to_dict(self) -> Dict:
        row = asdict(self)
        row["citizenship"] = ", ".join(self.citizenship)
        return row


CLUB_FIELDS = list(Club.__dataclass_fields__)
PLAYER_FIELDS = list(Player.__dataclass_fields__)
PROFILE_FIELDS = list(PlayerProfile.__dataclass_fields__)


# ---- competition -----------------------------------------------------------------

def parse_competition(html: str, code: str = "") -> Competition:
    title = re.search(r'<h1[^>]*class="data-header__headline-wrapper[^"]*"[^>]*>(.*?)</h1>', html, re.S)
    name = text(title.group(1)) if title else ""
    if not name:
        t = re.search(r"<title>(.*?)\|", html, re.S)
        name = re.sub(r"\s+\d{2}/\d{2}\s*$", "", text(t.group(1))) if t else ""
    if not code:
        m = re.search(r"/wettbewerb/([A-Z0-9]+)", html)
        code = m.group(1) if m else ""
    clubs: List[Club] = []
    season = None
    for row in _rows(_items_body(html)):
        link = re.search(r'<td class="hauptlink[^"]*"[^>]*>\s*<a title="([^"]*)" href="([^"]+)"', row)
        if not link:
            continue
        href = link.group(2)
        club_id = _id(href, "verein")
        if club_id is None:
            continue
        season = season or _season(href)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        # cells: crest, name, squad, avg age, foreigners, avg value, total value
        values = [text(c) for c in cells[2:7]] + [""] * 5
        squad_link = re.search(r'href="([^"]*/kader/verein/\d+[^"]*)"', row)
        clubs.append(Club(
            id=club_id,
            name=htmllib.unescape(link.group(1)),
            squad_size=to_int(values[0]),
            average_age=to_float(values[1]),
            foreigners=to_int(values[2]),
            average_market_value=values[3],
            average_market_value_eur=money(values[3]),
            total_market_value=values[4],
            total_market_value_eur=money(values[4]),
            season=_season(href),
            url=BASE + href,
            squad_url=squad_url(club_id, _season(href)) if squad_link else squad_url(club_id),
        ))
    foot = re.search(r"<tfoot>(.*?)</tfoot>", html, re.S)
    total = ""
    if foot:
        cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", foot.group(1), re.S)]
        total = cells[-1] if cells else ""
    return Competition(code=code, name=name, season=season, clubs=clubs,
                       total_market_value=total, total_market_value_eur=money(total))


# ---- squad -----------------------------------------------------------------------

POSITION_GROUPS = {"Torwart": "Goalkeeper", "Abwehr": "Defender", "Mittelfeld": "Midfield", "Sturm": "Attack"}


def parse_squad(html: str, club_id: Optional[int] = None) -> List[Player]:
    if club_id is None:
        m = re.search(r"/kader/verein/(\d+)", html)
        club_id = int(m.group(1)) if m else None
    club = re.search(r'<h1 class="data-header__headline-wrapper[^"]*"[^>]*>(.*?)</h1>', html, re.S)
    club_name = text(club.group(1)) if club else ""
    if not club_name:
        t = re.search(r"<title>(.*?) - ", html, re.S)
        club_name = text(t.group(1)) if t else ""
    season = None
    sm = re.search(r"/kader/verein/\d+/saison_id/(\d{4})", html)
    if sm:
        season = int(sm.group(1))
    players: List[Player] = []
    seen = set()
    for row in _rows(_items_body(html)):
        link = re.search(r'<td class="hauptlink">\s*<a href="([^"]*/profil/spieler/(\d+))"[^>]*>(.*?)</a>', row, re.S)
        if not link:
            continue
        pid = int(link.group(2))
        if pid in seen:
            continue
        seen.add(pid)
        number = re.search(r"rn_nummer>([^<]*)<", row)
        group = re.search(r"rueckennummer bg_(\w+)", row)
        inline = row.split("</table>", 1)
        position = ""
        if inline:
            pos_rows = re.findall(r"<tr>\s*<td>(.*?)</td>\s*</tr>", inline[0], re.S)
            position = text(pos_rows[-1]) if pos_rows else ""
        rest = inline[1] if len(inline) > 1 else ""
        cells = re.findall(r'<td class="(?:zentriert|rechts)[^"]*">(.*?)</td>', rest, re.S)
        # cells: birth/age, nat, height, foot, joined, signed from, contract, market value
        cells += [""] * 8
        dob_age = text(cells[0])
        age = re.search(r"\((\d+)\)", dob_age)
        nats = re.findall(r'<img[^>]*title="([^"]+)"[^>]*class="flaggenrahmen"', cells[1])
        signed = re.search(r'<a title="([^"]*)" href="([^"]*)"', cells[5])
        signed_from, fee, from_id = "", "", None
        if signed:
            label = htmllib.unescape(signed.group(1))
            name_part, _, fee_part = label.partition(": Ablöse ")
            signed_from = name_part.strip()
            fee = fee_part.strip()
            from_id = _id(signed.group(2), "verein")
            if not signed_from:
                alt = re.search(r'alt="([^"]*)"', cells[5])
                signed_from = htmllib.unescape(alt.group(1)) if alt else ""
        mv = text(cells[7])
        players.append(Player(
            id=pid,
            name=text(link.group(3)),
            number=to_int(text(number.group(1))) if number else None,
            position=position,
            position_group=POSITION_GROUPS.get(group.group(1), group.group(1)) if group else "",
            date_of_birth=date_iso(dob_age),
            age=int(age.group(1)) if age else None,
            nationalities=[htmllib.unescape(n) for n in nats],
            height_m=to_float(text(cells[2])),
            foot=text(cells[3]) if text(cells[3]) != "-" else "",
            joined=date_iso(text(cells[4])),
            signed_from=signed_from,
            signed_from_club_id=from_id,
            transfer_fee=fee,
            contract_until=date_iso(text(cells[6])),
            market_value=mv if mv != "-" else "",
            market_value_eur=money(mv),
            club_id=club_id,
            club_name=club_name,
            season=season,
            url=player_url(pid),
        ))
    return players


# ---- player profile ----------------------------------------------------------------

def _info(html: str) -> Dict[str, str]:
    i = html.find("info-table")
    if i < 0:
        return {}
    block = html[i:html.find("</div>\n</div>", i) if html.find("</div>\n</div>", i) > 0 else i + 15000]
    out: Dict[str, str] = {}
    pairs = re.findall(r'<span class="info-table__content info-table__content--regular">(.*?)</span>\s*'
                       r'<span class="info-table__content info-table__content--bold[^"]*">(.*?)</span>', block, re.S)
    for label, value in pairs:
        key = text(label).rstrip(":").strip()
        out[key] = value
    return out


def parse_player(html: str, player_id: Optional[int] = None) -> Optional[PlayerProfile]:
    if player_id is None:
        m = (re.search(r'player-id="(\d+)"', html) or re.search(r"/marktwertverlauf/spieler/(\d+)", html)
             or re.search(r"/profil/spieler/(\d+)", html))
        player_id = int(m.group(1)) if m else None
    head = re.search(r'<h1 class="data-header__headline-wrapper[^"]*"[^>]*>(.*?)</h1>', html, re.S)
    if not head or player_id is None:
        return None
    name = re.sub(r"^#\d+\s*", "", text(head.group(1)))
    info = _info(html)
    dob = text(info.get("Date of birth/Age", ""))
    age = re.search(r"\((\d+)\)", dob)
    club_html = info.get("Current club", "")
    club_link = re.search(r'href="([^"]*/verein/\d+[^"]*)"', club_html)
    mv_block = re.search(r'<a[^>]*class="data-header__market-value-wrapper"[^>]*>(.*?)</a>', html, re.S)
    mv_text, mv_date = "", ""
    if mv_block:
        raw = mv_block.group(1)
        updated = re.search(r"Last update:\s*([^<]+)", raw)
        mv_date = date_iso(text(updated.group(1))) if updated else ""
        mv_text = text(re.sub(r'<p class="data-header__last-update">.*?</p>', "", raw, flags=re.S))
        mv_text = mv_text.split("Last update")[0].replace(" ", "")
    return PlayerProfile(
        id=player_id,
        name=name,
        full_name=text(info.get("Name in home country", "")) or text(info.get("Full name", "")) or name,
        date_of_birth=date_iso(dob),
        age=int(age.group(1)) if age else None,
        place_of_birth=text(info.get("Place of birth", "")),
        height_m=to_float(text(info.get("Height", ""))),
        citizenship=[htmllib.unescape(t) for t in re.findall(r'<img[^>]*title="([^"]+)"', info.get("Citizenship", ""))]
        or [c for c in re.split(r"\s{2,}", text(info.get("Citizenship", ""))) if c],
        position=text(info.get("Position", "")),
        foot=text(info.get("Foot", "")),
        agent=text(info.get("Player agent", "")),
        current_club=text(club_html),
        current_club_id=_id(club_link.group(1), "verein") if club_link else None,
        joined=date_iso(text(info.get("Joined", ""))),
        contract_expires=date_iso(text(info.get("Contract expires", ""))),
        market_value=mv_text,
        market_value_eur=money(mv_text),
        market_value_updated=mv_date,
        url=player_url(player_id),
    )
