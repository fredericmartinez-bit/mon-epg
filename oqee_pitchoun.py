import json
import urllib.request
from datetime import datetime, timezone, timedelta
from xml.etree.ElementTree import Element, SubElement, ElementTree

CHANNEL_OQEE = "934"
CHANNEL_XMLTV = "TVPitchoun.fr"
OUTPUT = "tv-pitchoun.xml"
BASE = "https://api.oqee.net/api/v1/epg/all/"

now = datetime.now(timezone.utc)
start = now.replace(minute=0, second=0, microsecond=0)

# 7 jours
hours = 24 * 7

seen = set()
programmes = []

for h in range(hours):
    ts = int((start + timedelta(hours=h)).timestamp())

    with urllib.request.urlopen(BASE + str(ts), timeout=30) as r:
        data = json.loads(r.read().decode())

    entries = data.get("result", {}).get("entries", {})

    for entry in entries.get(CHANNEL_OQEE, []):
        live = entry.get("live")
        if not live:
            continue

        key = (
            live.get("start"),
            live.get("end"),
            live.get("title")
        )

        if key in seen:
            continue

        seen.add(key)
        programmes.append((live, entry.get("pictures", {})))

tv = Element("tv")

channel = SubElement(tv, "channel", id=CHANNEL_XMLTV)
SubElement(channel, "display-name").text = "TV Pitchoun"

for live, pictures in sorted(programmes, key=lambda x: x[0].get("start", 0)):

    start_ts = live.get("start")
    end_ts = live.get("end")

    if not start_ts or not end_ts:
        continue

    start_dt = datetime.fromtimestamp(start_ts, timezone.utc)
    stop_dt = datetime.fromtimestamp(end_ts, timezone.utc)

    p = SubElement(
        tv,
        "programme",
        start=start_dt.strftime("%Y%m%d%H%M%S +0000"),
        stop=stop_dt.strftime("%Y%m%d%H%M%S +0000"),
        channel=CHANNEL_XMLTV,
    )

    title = live.get("title")
    if title:
        SubElement(p, "title", lang="fr").text = title

    subtitle = live.get("sub_title")
    if subtitle:
        SubElement(p, "sub-title", lang="fr").text = subtitle

    desc = live.get("description")
    if desc:
        SubElement(p, "desc", lang="fr").text = desc

    category = live.get("category")
    if category:
        SubElement(p, "category", lang="fr").text = category

    sub_category = live.get("sub_category")
    if sub_category:
        SubElement(p, "category", lang="fr").text = sub_category

    year = live.get("year")
    if year:
        SubElement(p, "date").text = str(year)

    image = pictures.get("main") or pictures.get("preview") or pictures.get("huge")
    if image:
        image = image.replace("%d", "640")
        SubElement(p, "icon", src=image)

ElementTree(tv).write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True
)

print(f"{len(programmes)} programmes écrits dans {OUTPUT}")
