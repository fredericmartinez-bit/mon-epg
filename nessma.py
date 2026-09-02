import xml.etree.ElementTree as ET

SOURCE = "guide-free.xml"
OUTPUT = "nessma.xml"
SOURCE_ID = "OQEE.808"
TARGET_ID = "Nessma.tn"

tree = ET.parse(SOURCE)
root = tree.getroot()

out = ET.Element("tv")

channel = ET.SubElement(out, "channel", id=TARGET_ID)
ET.SubElement(channel, "display-name", lang="fr").text = "Nessma"

count = 0

for p in root.findall("programme"):
    if p.get("channel") != SOURCE_ID:
        continue

    new_p = ET.SubElement(
        out,
        "programme",
        start=p.get("start"),
        stop=p.get("stop"),
        channel=TARGET_ID,
    )

    for child in p:
        new_p.append(ET.fromstring(ET.tostring(child, encoding="unicode")))

    count += 1

ET.indent(out, space="  ")
ET.ElementTree(out).write(OUTPUT, encoding="utf-8", xml_declaration=True)

print(f"Nessma : {count} programmes")
print(f"Fichier : {OUTPUT}")
