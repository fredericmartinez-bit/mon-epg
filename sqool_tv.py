import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

URL = "https://www.sqooltv.com/grille-des-programmes/"
CHANNEL_ID = "SQOOLTV.fr"

def download(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

page = download(URL)

today = datetime.now()

# Lundi-vendredi = pills-1
# Samedi = pills-2
# Dimanche = pills-3
if today.weekday() <= 4:
    tab_id = "pills-1"
elif today.weekday() == 5:
    tab_id = "pills-2"
else:
    tab_id = "pills-3"

start_marker = f'id="{tab_id}"'
start_pos = page.find(start_marker)

if start_pos == -1:
    raise SystemExit(f"Bloc {tab_id} introuvable")

next_tab = page.find('class="timeline tab-pane', start_pos + 20)
block = page[start_pos:next_tab if next_tab != -1 else None]

tv = ET.Element("tv")

channel = ET.SubElement(tv, "channel", id=CHANNEL_ID)
ET.SubElement(channel, "display-name", lang="fr").text = "SQOOL TV"

pattern = re.compile(
    r'<div class="row timeline-item.*?'
    r'<div class="col-6 h3 schedule">\s*'
    r'(\d{2})H(\d{2})\s*-\s*(\d{2})H(\d{2}).*?'
    r'<div class="col-6 h3 text-end novel">\s*(.*?)\s*</div>.*?'
    r'<h4 class="[^"]*title[^"]*">(.*?)</h4>.*?'
    r'(?:<div class="speaker[^"]*">(.*?)</div>)?.*?'
    r'<img class="img-fluid" src="([^"]+)">.*?'
    r'((?:<span class="badge[^>]*>.*?</span>\s*)+).*?'
    r'<p class="mt-1">\s*(.*?)\s*</p>',
    re.S
)

count = 0

for sh, sm, eh, em, status, title, speaker, image, badges, desc in pattern.findall(block):
    title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
    status = html.unescape(re.sub(r"<[^>]+>", "", status)).strip()
    desc = html.unescape(re.sub(r"<[^>]+>", "", desc)).strip()

    speaker = html.unescape(
        re.sub(r"<br\s*/?>", " ", speaker, flags=re.I)
    )
    speaker = re.sub(r"<[^>]+>", "", speaker).strip()

    categories = [
        html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
        for x in re.findall(r"<span[^>]*>(.*?)</span>", badges, re.S)
    ]

    start = today.replace(
        hour=int(sh),
        minute=int(sm),
        second=0,
        microsecond=0
    )

    stop = today.replace(
        hour=int(eh),
        minute=int(em),
        second=0,
        microsecond=0
    )

    if stop <= start:
        stop += timedelta(days=1)

    programme = ET.SubElement(
        tv,
        "programme",
        start=start.strftime("%Y%m%d%H%M%S") + " +0200",
        stop=stop.strftime("%Y%m%d%H%M%S") + " +0200",
        channel=CHANNEL_ID
    )

    ET.SubElement(programme, "title", lang="fr").text = title

    if desc:
        ET.SubElement(programme, "desc", lang="fr").text = desc

    for category in categories:
        if category:
            ET.SubElement(programme, "category", lang="fr").text = category

    if status:
        ET.SubElement(programme, "category", lang="fr").text = status.title()

    if speaker:
        ET.SubElement(programme, "credits").text = speaker

    if image:
        ET.SubElement(programme, "icon", src=image)

    count += 1

tree = ET.ElementTree(tv)
ET.indent(tree, space="  ")

tree.write(
    "sqool-tv.xml",
    encoding="utf-8",
    xml_declaration=True
)

print("SQOOL TV :", count, "programmes")
print("Grille :", tab_id)
print("Fichier : sqool-tv.xml")
