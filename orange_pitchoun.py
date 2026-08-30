import json
import re
import html
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from xml.etree.ElementTree import Element, SubElement, ElementTree

OUTPUT = "pitchoun-kids.xml"
CHANNEL_ID = "PitchounKidsMusic.fr"

URL_PAGE = "https://caraibe.orange.fr/tv/programme"
URL_GRILLE = "https://caraibe.orange.fr/programme_tv/getgrille"

UA = "Mozilla/5.0"
TZ = ZoneInfo("America/Guadeloupe")

RANGES = [
    (0, 5),
    (5, 8),
    (8, 12),
    (12, 16),
    (16, 20),
    (20, 24),
]

def request(url, data=None):
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="ignore")

page = request(URL_PAGE)

dates = sorted(set(re.findall(
    r'data-date="(\d{4}-\d{2}-\d{2})"',
    page
)))

tv = Element("tv")

channel = SubElement(tv, "channel", id=CHANNEL_ID)
SubElement(channel, "display-name").text = "Pitchoun Kids Music"

seen = set()

for date_str in dates:

    year, month, day = map(int, date_str.split("-"))

    for h1, h2 in RANGES:

        start_dt = datetime(year, month, day, h1, 0, tzinfo=TZ)

        if h2 == 24:
            end_dt = datetime(
                year, month, day, 0, 0, tzinfo=TZ
            ) + timedelta(days=1)
        else:
            end_dt = datetime(
                year, month, day, h2, 0, tzinfo=TZ
            )

        payload = urllib.parse.urlencode({
            "start": int(start_dt.timestamp() * 1000),
            "end": int(end_dt.timestamp() * 1000),
            "categories": "",
            "bouquet": "",
            "favoris": "",
        }).encode()

        data = json.loads(request(URL_GRILLE, payload))
        content = html.unescape(data["html"])

        start = content.find("TV PITCHOUN KIDS MUSIC")
        if start == -1:
            continue

        end = content.find('<h3 class="channel">', start + 1)
        block = content[start:end]

        rows = re.findall(
            r'block mb-10">(\d{1,2}h\d{2})</span>\s*'
            r'<span class="font-bold text-sm leading-20 block">(.*?)</span>\s*'
            r'<span class="text-sm leading-20 block">(.*?)</span>',
            block,
            re.S
        )

        for heure, titre, info in rows:

            hour, minute = map(
                int,
                heure.replace("h", ":").split(":")
            )

            # Ignore les programmes appartenant
            # à la tranche précédente/suivante.
            if h2 == 24:
                if not (h1 <= hour <= 23):
                    continue
            elif not (h1 <= hour < h2):
                continue

            titre = re.sub("<.*?>", "", titre).strip()
            info = re.sub("<.*?>", "", info).strip()

            duration_match = re.search(r"(\d+)min", info)

            if not duration_match:
                continue

            duration = int(duration_match.group(1))

            programme_start = datetime(
                year,
                month,
                day,
                hour,
                minute,
                tzinfo=TZ
            )

            programme_stop = programme_start + timedelta(
                minutes=duration
            )

            key = (
                programme_start.isoformat(),
                titre
            )

            if key in seen:
                continue

            seen.add(key)

            programme = SubElement(
                tv,
                "programme",
                start=programme_start.strftime(
                    "%Y%m%d%H%M%S -0400"
                ),
                stop=programme_stop.strftime(
                    "%Y%m%d%H%M%S -0400"
                ),
                channel=CHANNEL_ID,
            )

            SubElement(
                programme,
                "title",
                lang="fr"
            ).text = titre

            category = info.split(",")[0].strip()

            if category:
                SubElement(
                    programme,
                    "category",
                    lang="fr"
                ).text = category

ElementTree(tv).write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True
)

print(f"{len(dates)} jours récupérés")
print(f"{len(seen)} programmes écrits dans {OUTPUT}")
