"""
Generates clean, high-contrast white silhouette line-art SVG figures for all yoga poses,
matching the reference design in the corner of each pose card.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FIGURES_DIR = BASE_DIR / "assets" / "pose_figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# SVG templates: Clean white silhouette lines (#FFFFFF) with smooth round stroke linecaps
FIGURES = {
    "vrikshasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="18" r="6" fill="#FFFFFF" />
  <line x1="50" y1="24" x2="50" y2="54" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms overhead in prayer -->
  <path d="M 50 30 L 36 18 L 50 8 L 64 18 L 50 30" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Standing Leg -->
  <line x1="50" y1="54" x2="50" y2="92" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Bent Tree Leg -->
  <polyline points="50,54 74,68 52,70" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
</svg>""",

    "natarajasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="36" cy="24" r="6" fill="#FFFFFF" />
  <!-- Torso leaning forward -->
  <path d="M 36 30 Q 48 44 58 50" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Standing leg -->
  <line x1="58" y1="50" x2="55" y2="92" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Front extended arm -->
  <line x1="42" y1="36" x2="16" y2="30" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Back leg arched up to hand -->
  <path d="M 58 50 Q 86 38 80 14" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Back arm holding foot -->
  <path d="M 44 34 Q 68 18 80 14" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
</svg>""",

    "trikonasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="35" cy="40" r="6" fill="#FFFFFF" />
  <!-- Lateral Torso -->
  <line x1="38" y1="44" x2="62" y2="58" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Legs in Triangle -->
  <line x1="62" y1="58" x2="26" y2="90" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <line x1="62" y1="58" x2="82" y2="90" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms vertical line (reach down to shin, reach up to sky) -->
  <line x1="30" y1="78" x2="52" y2="12" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
</svg>""",

    "bhujangasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="25" cy="35" r="6" fill="#FFFFFF" />
  <!-- Curved Spine & Legs -->
  <path d="M 28 40 Q 42 62 60 76 L 90 82" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms on floor -->
  <polyline points="38,50 34,68 46,80" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <line x1="15" y1="84" x2="95" y2="84" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round" />
</svg>""",

    "setu_bandhasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="20" cy="74" r="6" fill="#FFFFFF" />
  <!-- Arching Bridge Torso and Pelvis -->
  <path d="M 24 74 Q 50 36 72 44 L 84 80" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Arms resting flat -->
  <line x1="28" y1="76" x2="65" y2="78" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Floor line -->
  <line x1="10" y1="84" x2="90" y2="84" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round" />
</svg>""",

    "dhanurasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="25" cy="38" r="6" fill="#FFFFFF" />
  <!-- Bow Body Arch (belly on ground, chest and thighs lifted) -->
  <path d="M 28 42 Q 50 78 72 44" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Lower legs reaching up -->
  <polyline points="72,44 68,26" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Arms reaching back to ankles -->
  <path d="M 36 50 Q 52 32 68 26" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
</svg>""",

    "balasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="28" cy="68" r="6" fill="#FFFFFF" />
  <!-- Folded Torso over thighs -->
  <path d="M 32 68 Q 50 50 72 58 L 84 76" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Arms extended forward along floor -->
  <line x1="40" y1="68" x2="12" y2="78" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Floor line -->
  <line x1="8" y1="82" x2="92" y2="82" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round" />
</svg>""",

    "sukhasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="22" r="6" fill="#FFFFFF" />
  <!-- Upright Spine -->
  <line x1="50" y1="28" x2="50" y2="64" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Crossed Legs Base -->
  <path d="M 22 78 Q 50 86 78 78 Q 66 68 50 64 Q 34 68 22 78 Z" fill="#FFFFFF" />
  <!-- Arms resting on knees -->
  <polyline points="50,38 30,58 26,74" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <polyline points="50,38 70,58 74,74" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
</svg>""",

    "tadasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="16" r="6" fill="#FFFFFF" />
  <!-- Spine -->
  <line x1="50" y1="22" x2="50" y2="56" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms straight down at sides -->
  <line x1="50" y1="28" x2="38" y2="58" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="50" y1="28" x2="62" y2="58" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Legs together -->
  <line x1="47" y1="56" x2="47" y2="92" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <line x1="53" y1="56" x2="53" y2="92" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
</svg>""",

    "virabhadrasana_ii.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="48" cy="24" r="6" fill="#FFFFFF" />
  <!-- Vertical Torso -->
  <line x1="48" y1="30" x2="48" y2="58" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Outstretched Arms -->
  <line x1="16" y1="36" x2="80" y2="36" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Front Bent Knee (Left) -->
  <polyline points="48,58 24,62 24,90" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Back Straight Leg (Right) -->
  <line x1="48" y1="58" x2="82" y2="90" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
</svg>""",

    "paschimottanasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="34" cy="54" r="6" fill="#FFFFFF" />
  <!-- Legs flat -->
  <line x1="80" y1="76" x2="20" y2="76" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Folded Torso -->
  <path d="M 80 76 Q 60 52 38 56" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms reaching forward to toes -->
  <line x1="46" y1="58" x2="22" y2="72" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
</svg>""",

    "adho_mukha_svanasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="30" cy="58" r="6" fill="#FFFFFF" />
  <!-- Inverted V Peak at Pelvis -->
  <polyline points="18,80 50,28 82,80" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Spine Line -->
  <line x1="50" y1="28" x2="34" y2="54" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
</svg>""",

    "utkatasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="38" cy="22" r="6" fill="#FFFFFF" />
  <!-- Torso hinged -->
  <line x1="42" y1="26" x2="62" y2="52" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms up along ears -->
  <line x1="44" y1="30" x2="24" y2="10" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Squat legs -->
  <polyline points="62,52 38,62 50,90" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
</svg>"""
}

def generate():
    for name, content in FIGURES.items():
        out_file = FIGURES_DIR / name
        out_file.write_text(content.strip(), encoding="utf-8")
        print(f"Generated clean white silhouette: {name}")

if __name__ == "__main__":
    generate()
