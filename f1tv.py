import urllib.request
import re
import json
import html as htmlmod
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CHANNEL_ID = "F1TV1.fr"
OUTPUT = "f1tv.xml"
YEAR = datetime.now().year

CALENDAR_URL = f"https://www.formula1.com/en/racing/{YEAR}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

TRANSLATIONS = {
    "Practice 1": "F1 - Essais libres 1",
    "Practice 2": "F1 - Essais libres 2",
    "Practice 3": "F1 - Essais libres 3",
    "Qualifying": "F1 - Qualifications",
    "Sprint Qualifying": "F1 - Qualifications Sprint",
    "Sprint": "F1 - Sprint",
    "Race": "F1 - Grand Prix",
}



GP_TRANSLATIONS = {
    "Italian Grand Prix": "Grand Prix d'Italie",
    "Spanish Grand Prix": "Grand Prix d'Espagne",
    "Azerbaijan Grand Prix": "Grand Prix d'Azerbaïdjan",
    "Bahrain Grand Prix": "Grand Prix de Bahreïn",
    "Singapore Grand Prix": "Grand Prix de Singapour",
    "United States Grand Prix": "Grand Prix des États-Unis",
    "Mexico City Grand Prix": "Grand Prix de Mexico",
    "Mexican Grand Prix": "Grand Prix du Mexique",
    "São Paulo Grand Prix": "Grand Prix de São Paulo",
    "Brazilian Grand Prix": "Grand Prix du Brésil",
    "Las Vegas Grand Prix": "Grand Prix de Las Vegas",
    "Qatar Grand Prix": "Grand Prix du Qatar",
    "Abu Dhabi Grand Prix": "Grand Prix d'Abou Dabi",
}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="ignore")


def get_race_links():
    page = fetch(CALENDAR_URL)

    links = re.findall(
        rf'href=["\'](/en/racing/{YEAR}/[^"\'?#]+)',
        page,
        re.I,
    )

    result = []

    for link in links:
        url = "https://www.formula1.com" + htmlmod.unescape(link)

        if url.rstrip("/") == CALENDAR_URL.rstrip("/"):
            continue

        if url not in result:
            result.append(url)

    return result


def extract_jsonld(page):
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>'
        r'(.*?)</script>',
        page,
        re.I | re.S,
    )

    objects = []

    for block in blocks:
        try:
            objects.append(
                json.loads(htmlmod.unescape(block))
            )
        except Exception:
            pass

    return objects


def walk(obj):
    if isinstance(obj, dict):
        yield obj

        for value in obj.values():
            yield from walk(value)

    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def parse_datetime(value):
    if not value:
        return None

    value = value.replace("Z", "+00:00")

    return datetime.fromisoformat(value)


def get_sessions(url):
    page = fetch(url)

    sessions = []

    for data in extract_jsonld(page):
        for obj in walk(data):

            if obj.get("@type") != "SportsEvent":
                continue

            name = obj.get("name", "")
            start = parse_datetime(obj.get("startDate"))
            stop = parse_datetime(obj.get("endDate"))

            if not start or not stop:
                continue

            session = name.split(" - ", 1)[0].strip()

            if session not in TRANSLATIONS:
                continue

            gp = ""

            if " - " in name:
                gp = name.split(" - ", 1)[1].strip()

            sessions.append(
                {
                    "session": session,
                    "gp": gp,
                    "start": start,
                    "stop": stop,
                }
            )

    unique = {}

    for item in sessions:
        key = (
            item["session"],
            item["start"],
            item["stop"],
        )
        unique[key] = item

    return list(unique.values())


def xmltv_time(dt):
    return dt.astimezone(
        ZoneInfo("Europe/Paris")
    ).strftime("%Y%m%d%H%M%S %z")


def create_xml(sessions):
    tv = ET.Element(
        "tv",
        {"generator-info-name": "Formula1.com official schedule"},
    )

    channel = ET.SubElement(
        tv,
        "channel",
        {"id": CHANNEL_ID},
    )

    ET.SubElement(
        channel,
        "display-name",
        {"lang": "fr"},
    ).text = "F1TV 1"

    sessions.sort(key=lambda x: x["start"])

    for item in sessions:
        p = ET.SubElement(
            tv,
            "programme",
            {
                "start": xmltv_time(item["start"]),
                "stop": xmltv_time(item["stop"]),
                "channel": CHANNEL_ID,
            },
        )

        title = TRANSLATIONS[item["session"]]

        ET.SubElement(
            p,
            "title",
            {"lang": "fr"},
        ).text = title

        desc = GP_TRANSLATIONS.get(item["gp"], item["gp"])

        if desc:
            desc = f"{desc} - Programme officiel Formula 1."

        else:
            desc = "Programme officiel Formula 1."

        ET.SubElement(
            p,
            "desc",
            {"lang": "fr"},
        ).text = desc

        ET.SubElement(
            p,
            "category",
            {"lang": "fr"},
        ).text = "Formule 1"

    tree = ET.ElementTree(tv)
    ET.indent(tree, space="  ")

    tree.write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True,
    )


def main():
    links = get_race_links()

    print("Grands Prix trouvés :", len(links))

    all_sessions = []

    now = datetime.now(timezone.utc)

    for url in links:
        try:
            sessions = get_sessions(url)

            if not sessions:
                continue

            # On conserve les week-ends récents et futurs.
            if max(x["stop"] for x in sessions) < now:
                continue

            print(
                url,
                ":",
                len(sessions),
                "séance(s)",
            )

            all_sessions.extend(sessions)

        except Exception as e:
            print("Erreur :", url, "-", e)

    create_xml(all_sessions)

    print()
    print("Séances F1 :", len(all_sessions))
    print("Fichier créé :", OUTPUT)


if __name__ == "__main__":
    main()
