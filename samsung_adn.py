import urllib.request
import xml.etree.ElementTree as ET

URL = "https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/SamsungTVPlus/fr.xml"
SOURCE_ID = "FRBD5100001ZA"
TARGET_ID = "ADN.fr"

data = urllib.request.urlopen(URL, timeout=30).read()
root = ET.fromstring(data)

out = ET.Element("tv")

for ch in root.findall("channel"):
    if ch.get("id") == SOURCE_ID:
        ch.set("id", TARGET_ID)
        out.append(ch)
        break

count = 0
for p in root.findall("programme"):
    if p.get("channel") == SOURCE_ID:
        p.set("channel", TARGET_ID)
        out.append(p)
        count += 1

ET.ElementTree(out).write(
    "adn.xml",
    encoding="utf-8",
    xml_declaration=True
)

print("ADN programmes :", count)
print("Fichier : adn.xml")
