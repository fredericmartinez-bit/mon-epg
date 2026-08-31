import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

SERVICE_PLAN = "https://api.oqee.net/api/v6/service_plan"
EPG_URL = "https://api.oqee.net/api/v1/epg/all/{}"
OUTPUT = "guide-free.xml"

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def xmltv_time(ts):
    dt = datetime.fromtimestamp(ts, timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S +0000")

service = fetch_json(SERVICE_PLAN)["result"]["channels"]

now = int(time.time())
now -= now % 3600

epg = fetch_json(EPG_URL.format(now))["result"]["entries"]

tv = ET.Element("tv", {
    "generator-info-name": "OQEE Free EPG"
})

valid_channels = {}

for cid, programmes in epg.items():
    if not programmes:
        continue

    ch = service.get(str(cid), {})
    name = ch.get("name")

    if not name:
        continue

    valid_channels[str(cid)] = name

    channel = ET.SubElement(tv, "channel", {"id": f"OQEE.{cid}"})
    ET.SubElement(channel, "display-name").text = name

    logo = ch.get("logo")
    if isinstance(logo, str) and logo.startswith("http"):
        ET.SubElement(channel, "icon", {"src": logo})

programme_count = 0

for cid, name in valid_channels.items():
    items = epg.get(str(cid), [])

    for entry in items:
        live = entry.get("live") if isinstance(entry, dict) else None

        if not isinstance(live, dict):
            continue

        start = live.get("start")
        end = live.get("end")

        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue

        p = ET.SubElement(tv, "programme", {
            "channel": f"OQEE.{cid}",
            "start": xmltv_time(start),
            "stop": xmltv_time(end),
        })

        title = live.get("title") or live.get("name") or "Programme"
        ET.SubElement(p, "title", {"lang": "fr"}).text = str(title)

        subtitle = live.get("subtitle")
        if subtitle:
            ET.SubElement(p, "sub-title", {"lang": "fr"}).text = str(subtitle)

        desc = live.get("description") or live.get("desc")
        if desc:
            ET.SubElement(p, "desc", {"lang": "fr"}).text = str(desc)

        category = live.get("category")
        if category:
            ET.SubElement(p, "category", {"lang": "fr"}).text = str(category)

        programme_count += 1

tree = ET.ElementTree(tv)
ET.indent(tree, space="  ")

tree.write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True
)

print("Chaînes :", len(valid_channels))
print("Programmes :", programme_count)
print("Fichier :", OUTPUT)
