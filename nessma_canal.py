from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

EPG_DIR = Path("epg-source")
CHANNELS_FILE = EPG_DIR / "nessma-canal.channels.xml"
TEMP_OUTPUT = EPG_DIR / "nessma-canal-7days.xml"
OUTPUT = "nessma.xml"
TARGET_ID = "Nessma.tn"

CHANNELS_FILE.write_text(
    """<?xml version="1.0" encoding="UTF-8"?>
<channels>
  <channel site="canalplus.com" site_id="#1189" lang="fr" xmltv_id="NessmaCanal.tn">NESSMA TV</channel>
</channels>
""",
    encoding="utf-8",
)

subprocess.run(
    [
        "npm",
        "run",
        "grab",
        "--",
        "--channels",
        "nessma-canal.channels.xml",
        "--days",
        "4",
        "--output",
        "nessma-canal-7days.xml",
    ],
    cwd=EPG_DIR,
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
