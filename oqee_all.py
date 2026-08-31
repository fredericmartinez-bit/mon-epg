import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

SERVICE_PLAN = "https://api.oqee.net/api/v6/service_plan"
EPG_URL = "https://api.oqee.net/api/v1/epg/all/{}"
OUTPUT = "guide-free.xml"

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def xmltv_time(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y%m%d%H%M%S +0000")

service = fetch_json(SERVICE_PLAN)["result"]["channels"]

now = int(time.time())
now -= now % 3600

all_entries = {}

for hour in range(25):
    ts = now + hour * 3600
    print(f"Récupération +{hour}h...")

    data = fetch_json(EPG_URL.format(ts))["result"]["entries"]

    for cid, entries in data.items():
        if entries:
            all_entries.setdefault(str(cid), []).extend(entries)

tv = ET.Element("tv", {"generator-info-name": "OQEE Free EPG"})

valid_channels = {}

for cid, entries in all_entries.items():
    ch = service.get(str(cid), {})
    name = ch.get("name")
    if not name:
        continue

    valid_channels[cid] = name

    channel = ET.SubElement(tv, "channel", {"id": f"OQEE.{cid}"})
    ET.SubElement(channel, "display-name").text = name

programme_count = 0
seen = set()

for cid in valid_channels:
    for entry in all_entries.get(cid, []):
        live = entry.get("live") if isinstance(entry, dict) else None
        if not isinstance(live, dict):
            continue

        start = live.get("start")
        end = live.get("end")
        title = live.get("title") or live.get("name")

        if not start or not end or not title:
            continue

        key = (cid, start, end, title)
        if key in seen:
            continue

        seen.add(key)

        p = ET.SubElement(tv, "programme", {
            "channel": f"OQEE.{cid}",
            "start": xmltv_time(start),
            "stop": xmltv_time(end),
        })

        ET.SubElement(p, "title", {"lang": "fr"}).text = str(title)

        subtitle = live.get("subtitle")
        if subtitle:
            ET.SubElement(p, "sub-title", {"lang": "fr"}).text = str(subtitle)

        desc = live.get("description") or live.get("desc")
        if desc:
            ET.SubElement(p, "desc", {"lang": "fr"}).text = str(desc)

        programme_count += 1

tree = ET.ElementTree(tv)
ET.indent(tree, space="  ")
tree.write(OUTPUT, encoding="utf-8", xml_declaration=True)

print()
print("Chaînes :", len(valid_channels))
print("Programmes :", programme_count)
print("Fichier :", OUTPUT)
