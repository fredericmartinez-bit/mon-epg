import urllib.request
import urllib.parse
import re
import html
import os
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pypdf import PdfReader

CHANNEL_ID = "MXGPTV.fr"
OUTPUT = "mxgp-tv.xml"
NEWS_URL = "https://www.mxgp.com/news"
BASE_URL = "https://www.mxgp.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

# Noms français pour l'EPG
TRANSLATIONS = {
    "MX2 Free practice": "MX2 - Essais libres",
    "MXGP Free practice": "MXGP - Essais libres",
    "MX2 Time practice": "MX2 - Essais chronométrés",
    "MXGP Time practice": "MXGP - Essais chronométrés",
    "MX2 Qualifying Race": "MX2 - Course qualificative",
    "MXGP Qualifying Race": "MXGP - Course qualificative",
    "MX2 Warm-up": "MX2 - Warm-up",
    "MXGP Warm-up": "MXGP - Warm-up",
    "MX2 Race 1": "MX2 - Course 1",
    "MXGP Race 1": "MXGP - Course 1",
    "MX2 Race 2": "MX2 - Course 2",
    "MXGP Race 2": "MXGP - Course 2",
}


def fetch_bytes(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def fetch_text(url):
    return fetch_bytes(url).decode("utf-8", errors="ignore")


def find_timetable_articles():
    page = fetch_text(NEWS_URL)

    links = re.findall(r'href=["\']([^"\']+)["\']', page, flags=re.I)

    result = []

    for link in links:
        if "timetable-and-entry-list" not in link.lower():
            continue

        url = urllib.parse.urljoin(BASE_URL, html.unescape(link))

        if url not in result:
            result.append(url)

    return result


def find_pdf(article_url):
    page = fetch_text(article_url)

    links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', page, flags=re.I)

    for link in links:
        decoded = html.unescape(link)

        if "_timetable.pdf" in decoded.lower():
            return urllib.parse.urljoin(BASE_URL, decoded)

    return None


def pdf_text(pdf_url):
    data = fetch_bytes(pdf_url)

    fd, path = tempfile.mkstemp(suffix=".pdf")

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)

        reader = PdfReader(path)

        pages = []

        for page in reader.pages:
            pages.append(page.extract_text() or "")

        return "\n".join(pages)

    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def detect_dates(text):
    dates = {}

    pattern = re.compile(
        r"(Saturday|Sunday)\s+(\d{2})\.(\d{2})\.(\d{4})",
        re.I,
    )

    for day, dd, mm, yyyy in pattern.findall(text):
        dates[day.lower()] = datetime(
            int(yyyy),
            int(mm),
            int(dd),
        ).date()

    return dates


def extract_page_programmes(text):
    programmes = []

    pages = re.split(r"(?=Saturday\s+\d{2}\.\d{2}\.\d{4}|Sunday\s+\d{2}\.\d{2}\.\d{4})", text)

    # pypdf place parfois le titre du jour à la fin de la page.
    # On traite donc aussi les blocs à partir des dates détectées globalement.
    dates = detect_dates(text)

    current_day = None

    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()]
    lines = [x for x in lines if x]

    # Dans les PDF MXGP, le titre Saturday/Sunday peut apparaître
    # après les horaires. On détermine les plages grâce aux pages PDF
    # dans parse_pdf().
    return programmes, dates


def parse_schedule_page(text, event_date):
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()]
    lines = [x for x in lines if x]

    programmes = []

    wanted = [
        ("MX2 Free practice", "MX2 Free practice"),
        ("MXGP Free practice", "MXGP Free practice"),
        ("MX2 Time practice", "MX2 Time practice"),
        ("MXGP Time practice", "MXGP Time practice"),
        ("MX2 Qualifying Race", "MX2 Qualifying Race"),
        ("MXGP Qualifying Race", "MXGP Qualifying Race"),
        ("MX2 Warm-up", "MX2 Warm-up"),
        ("MXGP Warm-up", "MXGP Warm-up"),
    ]

    # Lignes qui contiennent directement heure + session
    for line in lines:
        m = re.match(r"^(\d{2}):(\d{2})\s+(.+)$", line)

        if not m:
            continue

        hh = int(m.group(1))
        mm = int(m.group(2))
        label = m.group(3)

        for needle, canonical in wanted:
            if needle.lower() in label.lower():
                start = datetime(
                    event_date.year,
                    event_date.month,
                    event_date.day,
                    hh,
                    mm,
                )

                duration = 30

                dm = re.search(r"(\d+)\s*mins?", label, re.I)
                if dm:
                    duration = int(dm.group(1))

                programmes.append(
                    (start, start + timedelta(minutes=duration), canonical)
                )
                break

    # Les courses sont souvent présentées sur deux lignes :
    # 13:05 MX2
    # 13:15 Race 1 ...
    pending_class = None

    for line in lines:
        m = re.match(r"^(\d{2}):(\d{2})\s+(.+)$", line)

        if not m:
            continue

        hh = int(m.group(1))
        mm = int(m.group(2))
        label = m.group(3).strip()

        if label in ("MX2", "MXGP"):
            pending_class = label
            continue

        race = re.match(
            r"Race\s+([12])\s+(\d+)\s*mins?",
            label,
            re.I,
        )

        qualifying = re.match(
            r"Qualifying Race\s+(\d+)\s*mins?",
            label,
            re.I,
        )

        if race and pending_class:
            race_no = race.group(1)
            duration = int(race.group(2))

            start = datetime(
                event_date.year,
                event_date.month,
                event_date.day,
                hh,
                mm,
            )

            canonical = f"{pending_class} Race {race_no}"

            programmes.append(
                (
                    start,
                    start + timedelta(minutes=duration + 10),
                    canonical,
                )
            )

            pending_class = None

        elif qualifying and pending_class:
            duration = int(qualifying.group(1))

            start = datetime(
                event_date.year,
                event_date.month,
                event_date.day,
                hh,
                mm,
            )

            canonical = f"{pending_class} Qualifying Race"

            programmes.append(
                (
                    start,
                    start + timedelta(minutes=duration + 10),
                    canonical,
                )
            )

            pending_class = None

    return programmes


def parse_pdf(pdf_url):
    data = fetch_bytes(pdf_url)

    fd, path = tempfile.mkstemp(suffix=".pdf")

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)

        reader = PdfReader(path)

        programmes = []

        for page in reader.pages:
            text = page.extract_text() or ""

            date_match = re.search(
                r"(Saturday|Sunday)\s+(\d{2})\.(\d{2})\.(\d{4})",
                text,
                re.I,
            )

            if not date_match:
                continue

            event_date = datetime(
                int(date_match.group(4)),
                int(date_match.group(3)),
                int(date_match.group(2)),
            ).date()

            programmes.extend(
                parse_schedule_page(text, event_date)
            )

        return programmes

    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def xmltv_time(dt):
    # Les horaires du timetable sont les horaires locaux du circuit.
    # Pour la Turquie : UTC+3.
    aware = dt.replace(tzinfo=ZoneInfo("Europe/Istanbul"))
    return aware.strftime("%Y%m%d%H%M%S %z")


def create_xml(programmes):
    tv = ET.Element("tv", {
        "generator-info-name": "MXGP official timetable"
    })

    channel = ET.SubElement(tv, "channel", {"id": CHANNEL_ID})

    ET.SubElement(channel, "display-name", {"lang": "fr"}).text = "MXGP-TV"

    icon = ET.SubElement(channel, "icon")
    icon.set("src", "https://www.mxgp.com/themes/custom/mxgp/favicon.ico")

    programmes = sorted(
        set(programmes),
        key=lambda x: x[0],
    )

    for start, stop, title in programmes:
        p = ET.SubElement(
            tv,
            "programme",
            {
                "start": xmltv_time(start),
                "stop": xmltv_time(stop),
                "channel": CHANNEL_ID,
            },
        )

        french = TRANSLATIONS.get(title, title)

        ET.SubElement(
            p,
            "title",
            {"lang": "fr"},
        ).text = french

        ET.SubElement(
            p,
            "desc",
            {"lang": "fr"},
        ).text = "Programme officiel MXGP."

        ET.SubElement(
            p,
            "category",
            {"lang": "fr"},
        ).text = "Motocross"

    tree = ET.ElementTree(tv)
    ET.indent(tree, space="  ")

    tree.write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True,
    )


def main():
    articles = find_timetable_articles()

    print("Articles timetable trouvés :", len(articles))

    all_programmes = []

    for article in articles[:10]:
        try:
            pdf = find_pdf(article)

            if not pdf:
                continue

            print("PDF :", pdf)

            programmes = parse_pdf(pdf)

            print("Programmes trouvés :", len(programmes))

            all_programmes.extend(programmes)

        except Exception as e:
            print("Erreur :", article, "-", e)

    create_xml(all_programmes)

    print()
    print("Programmes MXGP :", len(set(all_programmes)))
    print("Fichier créé :", OUTPUT)


if __name__ == "__main__":
    main()
