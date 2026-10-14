#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
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

    soup = BeautifulSoup(html, "html.parser")

    tv = ET.Element("tv", {"generator-info-name": "mon-epg"})

    channel = ET.SubElement(tv, "channel", id=CHANNEL_ID)
    ET.SubElement(channel, "display-name").text = "Al Jazeera 2"

    today = datetime.now(MECCA).date()
    count = 0

    for panel in soup.select(".schedule__items"):
        day_name = panel.get("aria-labelledby", "").lower()

        if day_name not in DAYS:
            continue

        target_weekday = DAYS[day_name]
        difference = target_weekday - today.weekday()

        # La page présente généralement les jours autour d'aujourd'hui.
        date = today + timedelta(days=difference)

        programmes = []

        for row in panel.select(".schedule__row"):
            time_element = row.select_one(".schedule__row__timeslot")
            title_element = row.select_one(".schedule__row__showname")

            if not time_element or not title_element:
                continue

            hour = time_element.get_text(strip=True)

            if not re.fullmatch(r"\d{1,2}:\d{2}", hour):
                continue

            title = title_element.get_text(" ", strip=True)

            now_showing = title_element.select_one(
                ".schedule__row__nowshowing"
            )

            if now_showing:
                title = title.replace(
                    now_showing.get_text(" ", strip=True), ""
                ).strip()

            description_element = row.select_one(
                ".schedule__row__description"
            )

            description = (
                description_element.get_text(" ", strip=True)
                if description_element else ""
            )

            start = datetime.strptime(
                f"{date} {hour}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=MECCA)

            programmes.append((start, title, description))

        for index, (start, title, description) in enumerate(programmes):
            if index + 1 < len(programmes):
                stop = programmes[index + 1][0]
            else:
                stop = start + timedelta(minutes=30)

            programme = ET.SubElement(
                tv,
                "programme",
                {
                    "start": xmltv_time(start),
                    "stop": xmltv_time(stop),
                    "channel": CHANNEL_ID,
                },
            )

            ET.SubElement(
                programme, "title", lang="ar"
            ).text = title

            if description:
                ET.SubElement(
                    programme, "desc", lang="ar"
                ).text = description

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

