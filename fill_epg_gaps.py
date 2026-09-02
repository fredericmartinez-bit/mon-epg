import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

GUIDE = "guide.xml"

CHANNELS = {
    "F1TV1.fr": "F1TV 1",
    "MXGPTV.fr": "MXGP-TV",
    "LEspritSorcierTV.fr": "L'Esprit Sorcier TV",
    "Nessma.tn": "Nessma",
}

PARIS = ZoneInfo("Europe/Paris")

tree = ET.parse(GUIDE)
root = tree.getroot()

window_start = datetime.now(PARIS).replace(minute=0, second=0, microsecond=0)
window_end = window_start + timedelta(days=7)

def parse_time(value):
    return datetime.strptime(value, "%Y%m%d%H%M%S %z").astimezone(PARIS)

def xmltv_time(value):
    return value.strftime("%Y%m%d%H%M%S %z")

added = 0

for channel_id, title in CHANNELS.items():
    slots = []

    for programme in root.findall("programme"):
        if programme.get("channel") != channel_id:
            continue

        try:
            start = parse_time(programme.get("start"))
            stop = parse_time(programme.get("stop"))
        except Exception:
            continue

        if stop > window_start and start < window_end:
            slots.append((start, stop))

    slots.sort()
    cursor = window_start

    for start, stop in slots:
        if stop <= cursor:
            continue

        if start > cursor:
            filler = ET.Element(
                "programme",
                start=xmltv_time(cursor),
                stop=xmltv_time(min(start, window_end)),
                channel=channel_id,
            )
            ET.SubElement(filler, "title", lang="fr").text = title
            root.append(filler)
            added += 1

        cursor = max(cursor, stop)

        if cursor >= window_end:
            break

    if cursor < window_end:
        filler = ET.Element(
            "programme",
            start=xmltv_time(cursor),
            stop=xmltv_time(window_end),
            channel=channel_id,
        )
        ET.SubElement(filler, "title", lang="fr").text = title
        root.append(filler)
        added += 1

ET.indent(tree, space="  ")
tree.write(GUIDE, encoding="utf-8", xml_declaration=True)

print(f"Programmes de remplissage ajoutés : {added}")

