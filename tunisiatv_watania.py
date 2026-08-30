#!/usr/bin/env python3

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Africa/Tunis")

CHANNELS = {
    "Watania1.tn": {
        "name": "Watania 1",
        "id": "69c58aac8d6cac7a55cd2e09",
        "slug": "%D8%A7%D9%84%D9%88%D8%B7%D9%86%D9%8A%D8%A9%201",
    },
    "Watania2.tn": {
        "name": "Watania 2",
        "id": "69c593d18d6cac7a55cd575c",
        "slug": "%D8%A7%D9%84%D9%88%D8%B7%D9%86%D9%8A%D8%A9%202",
    },
}


class ScheduleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.programs = []
        self.in_card = False
        self.card_depth = 0
        self.capture = None
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "div":
            classes = attrs.get("class", "").split()

            if not self.in_card and "card" in classes and "card-md-list" in classes:
                self.in_card = True
                self.card_depth = 1
                self.current = {
                    "time": "",
                    "title": "",
                    "desc": "",
                    "image": "",
                }
                return

            if self.in_card:
                self.card_depth += 1

        if not self.in_card:
            return

        if tag == "time":
            self.capture = "time"

        elif tag == "h3":
            self.capture = "title"

        elif tag == "p":
            self.capture = "desc"

        elif tag == "img":
            src = attrs.get("src", "")
            if src.startswith("https://api.wataniaplus.tunisiatv.tn/"):
                self.current["image"] = src

    def handle_endtag(self, tag):
        if not self.in_card:
            return

        if tag in ("time", "h3", "p"):
            self.capture = None

        if tag == "div":
            self.card_depth -= 1

            if self.card_depth == 0:
                if self.current["time"] and self.current["title"]:
                    for key in ("time", "title", "desc"):
                        self.current[key] = " ".join(
                            html.unescape(self.current[key]).split()
                        )
                    self.programs.append(self.current)

                self.current = None
                self.in_card = False

    def handle_data(self, data):
        if self.in_card and self.capture and self.current is not None:
            self.current[self.capture] += data


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "ar,en;q=0.8",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def xmltv_time(dt):
    return dt.strftime("%Y%m%d%H%M%S %z")


def parse_time_range(value, base_date):
    match = re.match(r"(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})", value)

    if not match:
        return None, None

    sh, sm, eh, em = map(int, match.groups())

    start = datetime(
        base_date.year,
        base_date.month,
        base_date.day,
        sh,
        sm,
        tzinfo=TZ,
    )

    stop = datetime(
        base_date.year,
        base_date.month,
        base_date.day,
        eh,
        em,
        tzinfo=TZ,
    )

    # Le site indique généralement la dernière minute incluse.
    stop += timedelta(minutes=1)

    if stop <= start:
        stop += timedelta(days=1)

    return start, stop


today = datetime.now(TZ)

# 1=lundi ... 7=dimanche
day_number = today.isoweekday()

tv = ET.Element("tv", {
    "generator-info-name": "tunisiatv.tn official EPG"
})

total = 0

for channel_id, info in CHANNELS.items():
    channel = ET.SubElement(tv, "channel", {"id": channel_id})
    ET.SubElement(channel, "display-name", {"lang": "fr"}).text = info["name"]

    url = (
        f"https://www.tunisiatv.tn/ar/programme/"
        f"{day_number}/{info['id']}/{info['slug']}"
    )

    print(f"\n{info['name']}")
    print(url)

    page = fetch(url)

    parser = ScheduleParser()
    parser.feed(page)

    seen = set()
    count = 0

    for item in parser.programs:
        start, stop = parse_time_range(item["time"], today)

        if not start or not stop:
            continue

        key = (
            start.isoformat(),
            stop.isoformat(),
            item["title"],
        )

        if key in seen:
            continue

        seen.add(key)

        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start": xmltv_time(start),
                "stop": xmltv_time(stop),
                "channel": channel_id,
            },
        )

        ET.SubElement(programme, "title", {"lang": "ar"}).text = item["title"]

        if item["desc"]:
            ET.SubElement(programme, "desc", {"lang": "ar"}).text = item["desc"]

        if item["image"]:
            ET.SubElement(programme, "icon", {"src": item["image"]})

        count += 1

    total += count
    print("Programmes :", count)

ET.indent(tv, space="  ")

ET.ElementTree(tv).write(
    "watania-officiel.xml",
    encoding="utf-8",
    xml_declaration=True,
)

print("\nTOTAL :", total)
print("Fichier : watania-officiel.xml")
