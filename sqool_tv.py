import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

INDEX_URL = "https://caraibe.orange.fr/tv/programme"
BASE_URL = "https://caraibe.orange.fr"
CHANNEL_ID = "SQOOLTV.fr"

def download(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

index = download(INDEX_URL)

pos = index.find('data-channel="3767"')
if pos == -1:
    raise SystemExit("SQOOL TV (3767) introuvable")

# On reste uniquement dans le bloc SQOOL.
end = index.find('data-channel="', pos + 20)
block = index[pos:end if end != -1 else None]

m = re.search(r'href="(/tv/programme/[^"]+)"', block)
if not m:
    raise SystemExit("Aucun programme SQOOL TV trouvé")

url = BASE_URL + html.unescape(m.group(1))
print("Page SQOOL :", url)

page = download(url)

tv = ET.Element("tv")

channel = ET.SubElement(tv, "channel", id=CHANNEL_ID)
ET.SubElement(channel, "display-name").text = "SQOOL TV"
ET.SubElement(
    channel,
    "icon",
    src="https://orange-caraibe.twic.pics/medias/logo_tvchaine/3767_rect.png"
)

pattern = re.compile(
    r'<button[^>]+data-id="(\d+)"[^>]*>.*?'
    r'<img[^>]+src="([^"]+)"[^>]+alt="([^"]*)".*?'
    r'<p class="font-bold">([^<]+)</p>\s*'
    r'<p>([^<]+)</p>',
    re.S
)

months = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12
}

seen = set()
count = 0

for pid, image, title, date_text, info in pattern.findall(page):
    title = html.unescape(title).strip()
    date_text = html.unescape(date_text).strip()
    info = html.unescape(info).strip()

    m = re.search(
        r'\w+\s+(\d{1,2})\s+([^\s]+)\s+(\d{4})\s+(\d{2})h(\d{2})',
        date_text
    )
    if not m:
        continue

    day, month_name, year, hour, minute = m.groups()
    month = months.get(month_name.lower())
    if not month:
        continue

    dm = re.search(r'(\d+)\s*mn', info)
    if not dm:
        continue

    duration = int(dm.group(1))

    start = datetime(
        int(year), month, int(day),
        int(hour), int(minute)
    )
    stop = start + timedelta(minutes=duration)

    key = (start, stop, title)
    if key in seen:
        continue
    seen.add(key)

    programme = ET.SubElement(
        tv,
        "programme",
        start=start.strftime("%Y%m%d%H%M%S") + " -0400",
        stop=stop.strftime("%Y%m%d%H%M%S") + " -0400",
        channel=CHANNEL_ID
    )

    ET.SubElement(programme, "title", lang="fr").text = title

    category = info.split(",")[0].strip()
    if category:
        ET.SubElement(programme, "category", lang="fr").text = category

    if image:
        ET.SubElement(programme, "icon", src=html.unescape(image))

    count += 1

tree = ET.ElementTree(tv)
ET.indent(tree, space="  ")
tree.write(
    "sqool-tv.xml",
    encoding="utf-8",
    xml_declaration=True
)

print("SQOOL TV :", count, "programmes")
print("Fichier : sqool-tv.xml")
