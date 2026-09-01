import subprocess
import xml.etree.ElementTree as ET

URL = "https://xmltvfr.fr/xmltv/xmltv.xml"
TMP = "xmltvfr.xml"
OUT = "motorvision-plus.xml"
CHANNEL_ID = "MotorVisionTV.fr"

subprocess.run([
    "curl", "-L", "-A", "Mozilla/5.0",
    "-o", TMP, URL
], check=True)

root = ET.parse(TMP).getroot()
out = ET.Element("tv")

found = False
count = 0

for ch in root.findall("channel"):
    if ch.get("id") == CHANNEL_ID:
        out.append(ch)
        found = True
        break

for p in root.findall("programme"):
    if p.get("channel") == CHANNEL_ID:
        out.append(p)
        count += 1

if not found:
    raise SystemExit("MotorVisionTV.fr introuvable")

if count == 0:
    raise SystemExit("Aucun programme Motorvision+")

ET.ElementTree(out).write(
    OUT,
    encoding="utf-8",
    xml_declaration=True
)

print("Motorvision+ :", count, "programmes")
print("Fichier :", OUT)
