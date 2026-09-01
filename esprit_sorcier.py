import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

INDEX_URL = "https://caraibe.orange.fr/tv/programme"
BASE_URL = "https://caraibe.orange.fr"
ORANGE_CHANNEL_ID = "13561"
CHANNEL_ID = "LEspritSorcierTV.fr"
OUTPUT = "esprit-sorcier.xml"
OFFICIAL_URL = "https://lespritsorcier.tv/programmes.php"

def download(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

index = download(INDEX_URL)

pos = index.find(f'data-channel="{ORANGE_CHANNEL_ID}"')
if pos == -1:
    raise SystemExit("L'ESPRIT SORCIER TV introuvable")

end = index.find('data-channel="', pos + 20)
block = index[pos:end if end != -1 else None]

m = re.search(r'href="(/tv/programme/[^"]+)"', block)
if not m:
    raise SystemExit("Aucun programme L'ESPRIT SORCIER TV trouvé")

url = BASE_URL + html.unescape(m.group(1))
print("Page Esprit Sorcier :", url)

page = download(url)

tv = ET.Element("tv")

channel = ET.SubElement(tv, "channel", id=CHANNEL_ID)
ET.SubElement(channel, "display-name").text = "L'ESPRIT SORCIER TV"
ET.SubElement(
    channel,
    "icon",
    src="https://orange-caraibe.twic.pics/medias/logo_tvchaine/13561_rect.png"
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
programmes = []

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

    dm = re.search(r'(\d+)\s*m(?:n|in)', info, re.I)
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

    programmes.append(
        (start, stop, title, info, html.unescape(image))
    )

programmes.sort(key=lambda x: x[0])

# Fallback officiel si Orange ne fournit plus de grille actuelle.
now = datetime.now()

latest_stop = max((x[1] for x in programmes), default=None)

if latest_stop is None or latest_stop < now:
    official = download(OFFICIAL_URL)

    if (
        "17h30" in official
        and ("19h00" in official or "19h" in official)
        and "21h10" in official
    ):
        print("Orange périmé : fallback officiel activé")

        programmes = []
        seen = set()
        fallback_official = True

        # Créneaux annoncés officiellement par L'Esprit Sorcier TV.
        slots = [
            (7, 0, 8, 0, "Jeunesse"),
            (17, 30, 18, 30, "Jeunesse"),
            (19, 0, 20, 0, "Le Live"),
            (21, 10, 23, 59, "Soirée thématique"),
        ]

        for offset in range(7):
            day = now + timedelta(days=offset)

            for sh, sm, eh, em, title in slots:
                start = datetime(
                    day.year, day.month, day.day, sh, sm
                )
                stop = datetime(
                    day.year, day.month, day.day, eh, em
                )

                programmes.append(
                    (
                        start,
                        stop,
                        title,
                        "Programme officiel L'Esprit Sorcier TV",
                        ""
                    )
                )

        programmes.sort(key=lambda x: x[0])


for start, stop, title, info, image in programmes:
    programme = ET.SubElement(
        tv,
        "programme",
        start=start.strftime("%Y%m%d%H%M%S") + (" +0200" if globals().get("fallback_official") else " -0400"),
        stop=stop.strftime("%Y%m%d%H%M%S") + (" +0200" if globals().get("fallback_official") else " -0400"),
        channel=CHANNEL_ID
    )

    ET.SubElement(programme, "title", lang="fr").text = title

    category = info.split(",")[0].strip()
    if category and not re.fullmatch(r"\d+\s*m(?:n|in)", category, re.I):
        ET.SubElement(programme, "category", lang="fr").text = category

    if image:
        ET.SubElement(programme, "icon", src=image)

tree = ET.ElementTree(tv)
ET.indent(tree, space="  ")
tree.write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True
)

print("L'ESPRIT SORCIER TV :", len(programmes), "programmes")

if programmes:
    print("Premier :", programmes[0][0].strftime("%H:%M"), "-", programmes[0][2])
    print("Dernier :", programmes[-1][0].strftime("%H:%M"), "-", programmes[-1][2])

print("Fichier :", OUTPUT)
