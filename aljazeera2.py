#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import base64
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

URL = "https://www.aljazeera.net/schedule-aj2"
CHANNEL_ID = "AlJazeera2"
OUTPUT = "aljazeera2.xml"

MECCA = ZoneInfo("Asia/Riyadh")

DAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

def xmltv_time(dt):
    return dt.strftime("%Y%m%d%H%M%S %z")

def main():
    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")

    match = re.search(r'window\.__APOLLO_STATE__="([^"]+)"', html)
    if not match:
        raise RuntimeError("Données intégrées introuvables.")
    data = json.loads(base64.b64decode(match.group(1)))
    items = next(
        v["schedule"] for v in data.values()
        if isinstance(v, dict) and isinstance(v.get("schedule"), list)
    )

    tv = ET.Element("tv", {"generator-info-name": "mon-epg"})

    channel = ET.SubElement(tv, "channel", id=CHANNEL_ID)
    ET.SubElement(channel, "display-name").text = "Al Jazeera 2"

    today = datetime.now(MECCA).date()
    count = 0

    seen = set()
    for item in items:
        date = datetime.fromtimestamp(
            int(item["startDate"]), ZoneInfo("UTC")
        ).date()
        hour = item.get("showTimeslot", "")
        title = item.get("showName", "").strip()
        if not title or not re.fullmatch(r"\d{1,2}:\d{2}", hour):
            continue
        start = datetime.strptime(
            f"{date} {hour}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=MECCA)
        key = (start.isoformat(), title)
        if key in seen:
            continue
        seen.add(key)
        try:
            h, m, s = map(int, item.get("duration", "").split(":"))
            seconds = h * 3600 + m * 60 + s
        except (ValueError, AttributeError):
            seconds = 0
        # Les durées excessives ne décrivent pas une émission détaillée.
        if not 0 < seconds <= 3 * 3600:
            seconds = 1800
        stop = start + timedelta(seconds=seconds)
        programme = ET.SubElement(tv, "programme", {
            "start": xmltv_time(start),
            "stop": xmltv_time(stop),
            "channel": CHANNEL_ID,
        })
        ET.SubElement(programme, "title", lang="ar").text = title
        description = item.get("showDescription", "").strip()
        if description:
            ET.SubElement(programme, "desc", lang="ar").text = description
        count += 1

    if count == 0:
        raise RuntimeError("Aucun programme trouvé sur le site.")

    ET.indent(tv, space="  ")
    ET.ElementTree(tv).write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"EPG créé : {OUTPUT}")
    print(f"Nombre de programmes : {count}")

if __name__ == "__main__":
    main()

