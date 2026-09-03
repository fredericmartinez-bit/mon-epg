import subprocess
import xml.etree.ElementTree as ET

CHANNELS_FILE = "epg-source/nessma-canal.channels.xml"
TEMP_OUTPUT = "epg-source/nessma-canal-7days.xml"
OUTPUT = "nessma.xml"
TARGET_ID = "Nessma.tn"

subprocess.run(
    [
        "npm",
        "run",
        "grab",
        "--",
        "--channels",
        "nessma-canal.channels.xml",
        "--days",
        "7",
        "--output",
        "nessma-canal-7days.xml",
    ],
    cwd="epg-source",
    check=True,
)

tree = ET.parse(TEMP_OUTPUT)
root = tree.getroot()

for ch in root.findall("channel"):
    ch.set("id", TARGET_ID)

for p in root.findall("programme"):
    p.set("channel", TARGET_ID)

ET.indent(root, space="  ")
tree.write(OUTPUT, encoding="utf-8", xml_declaration=True)

print("Nessma CANAL+ généré :", len(root.findall("programme")), "programmes")
