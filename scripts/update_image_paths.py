"""
Updates image_path in data/poses.json and database/yoga_assistant.db
to point to the new high-resolution realistic studio visuals.
"""

import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POSES_JSON = BASE_DIR / "data" / "poses.json"
DB_PATH = BASE_DIR / "database" / "yoga_assistant.db"

IMAGE_MAP = {
    "Tadasana": "assets/images/yoga/tadasana.png",
    "Virabhadrasana II": "assets/images/yoga/virabhadrasana_ii.png",
    "Vrikshasana": "assets/images/yoga/vrikshasana.png",
    "Trikonasana": "assets/images/yoga/trikonasana.png",
    "Utkatasana": "assets/images/yoga/utkatasana.png",
    "Bhujangasana": "assets/images/yoga/bhujangasana.png",
    "Balasana": "assets/images/yoga/balasana.png",
    "Adho Mukha Svanasana": "assets/images/yoga/adho_mukha_svanasana.png",
    "Setu Bandhasana": "assets/images/yoga/setu_bandhasana.png",
    "Dhanurasana": "assets/images/yoga/dhanurasana.png",
    "Natarajasana": "assets/images/yoga/natarajasana.png",
    "Sukhasana": "assets/images/yoga/sukhasana.png",
    "Paschimottanasana": "assets/images/yoga/paschimottanasana.png"
}

def update():
    with open(POSES_JSON, "r", encoding="utf-8") as f:
        poses = json.load(f)

    for p in poses:
        name = p.get("name", "")
        if name in IMAGE_MAP:
            p["image_path"] = IMAGE_MAP[name]

    with open(POSES_JSON, "w", encoding="utf-8") as f:
        json.dump(poses, f, indent=2)
    print("Updated data/poses.json with realistic image paths.")

    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for name, img_path in IMAGE_MAP.items():
            cursor.execute("UPDATE poses SET image_path = ? WHERE name = ?", (img_path, name))
        conn.commit()
        conn.close()
        print("Updated database/yoga_assistant.db with realistic image paths.")

if __name__ == "__main__":
    update()
