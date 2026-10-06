"""
Generates anatomically accurate, premium, high-contrast white silhouette SVG figures
for all 20 yoga poses in assets/pose_figures/.
Ensures precise joint angles, clean vector curves, and distinct silhouettes matching
the target design benchmark.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FIGURES_DIR = BASE_DIR / "assets" / "pose_figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

PERFECT_SVGS = {
    # 1. Vrikshasana (Tree Pose)
    # Standing on left leg, right foot on inner thigh, hands in prayer above chest/overhead
    "vrikshasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head -->
  <circle cx="50" cy="16" r="5.5" fill="#FFFFFF" />
  <!-- Spine / Torso -->
  <line x1="50" y1="22" x2="50" y2="52" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms in Prayer (Anjali Mudra at chest/overhead) -->
  <polyline points="50,28 34,22 46,10 50,10" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <polyline points="50,28 66,22 54,10 50,10" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Standing Leg (Grounded Straight) -->
  <line x1="50" y1="52" x2="50" y2="92" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Bent Leg (Foot on Inner Thigh) -->
  <polyline points="50,52 74,66 52,68" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
</svg>""",

    # 2. Natarajasana (Dancer Pose)
    # Standing on one leg, torso leaning forward, back leg arched high holding foot, front arm forward
    "natarajasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head -->
  <circle cx="34" cy="24" r="5.5" fill="#FFFFFF" />
  <!-- Torso leaning forward -->
  <path d="M 36 29 Q 46 42 56 48" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Front Reach Arm -->
  <line x1="40" y1="34" x2="14" y2="28" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Standing Leg -->
  <line x1="56" y1="48" x2="54" y2="92" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Back Arched Leg -->
  <path d="M 56 48 Q 88 38 78 14" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Back Hand reaching up & back to foot -->
  <path d="M 44 34 Q 66 18 78 14" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
</svg>""",

    # 3. Trikonasana (Triangle Pose)
    # Wide stance, triangle formation, right hand down to ankle, left hand straight up to sky
    "trikonasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head -->
  <circle cx="34" cy="38" r="5.5" fill="#FFFFFF" />
  <!-- Torso tilted laterally -->
  <line x1="38" y1="42" x2="62" y2="56" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Lead Leg (Front) -->
  <line x1="62" y1="56" x2="26" y2="90" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Back Leg (Straight) -->
  <line x1="62" y1="56" x2="84" y2="90" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms vertical line (Lower to shin, upper to sky) -->
  <line x1="28" y1="80" x2="52" y2="12" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
</svg>""",

    # 4. Bhujangasana (Cobra Pose)
    # Prone, pelvis on mat, chest and head lifted in smooth spinal backward curve, arms supporting
    "bhujangasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head -->
  <circle cx="24" cy="34" r="5.5" fill="#FFFFFF" />
  <!-- Upper Chest & Spine arching down to pelvis and straight legs -->
  <path d="M 28 38 Q 42 62 60 76 L 92 82" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms supporting chest -->
  <polyline points="38,48 34,66 46,82" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Mat line -->
  <line x1="12" y1="86" x2="96" y2="86" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round" />
</svg>""",

    # 5. Setu Bandhasana (Bridge Pose)
    # Supine, feet grounded, knees bent, pelvis/hips elevated into high arch, shoulders on mat
    "setu_bandhasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head on Mat -->
  <circle cx="18" cy="74" r="5.5" fill="#FFFFFF" />
  <!-- Elevated Torso & Bridge Pelvis -->
  <path d="M 22 74 Q 48 34 72 44 L 84 82" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Arms resting flat on mat underneath -->
  <line x1="26" y1="78" x2="68" y2="80" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Mat line -->
  <line x1="10" y1="86" x2="92" y2="86" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round" />
</svg>""",

    # 6. Dhanurasana (Bow Pose)
    # Prone, belly on ground, chest and thighs arched up, hands gripping ankles
    "dhanurasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head lifted -->
  <circle cx="24" cy="36" r="5.5" fill="#FFFFFF" />
  <!-- Bow Body Curve (belly at bottom Q 50,78) -->
  <path d="M 28 40 Q 50 78 72 44" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Lower legs reaching up -->
  <polyline points="72,44 68,24" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Arms reaching back to grip ankles -->
  <path d="M 36 48 Q 52 30 68 24" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
</svg>""",

    # 7. Balasana (Child's Pose)
    # Kneeling, hips back on heels, torso folded completely over thighs, arms reaching forward on mat
    "balasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head resting on mat -->
  <circle cx="28" cy="70" r="5.5" fill="#FFFFFF" />
  <!-- Folded Torso and Pelvis over thighs -->
  <path d="M 32 70 Q 52 50 74 58 L 86 78" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Arms extended forward on floor -->
  <line x1="42" y1="70" x2="12" y2="80" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Floor Mat -->
  <line x1="8" y1="86" x2="94" y2="86" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round" />
</svg>""",

    # 8. Sukhasana (Easy Pose / Seated Lotus Meditation)
    # Seated cross-legged, upright spine, hands resting on knees
    "sukhasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head -->
  <circle cx="50" cy="20" r="5.5" fill="#FFFFFF" />
  <!-- Upright Torso -->
  <line x1="50" y1="26" x2="50" y2="62" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Crossed Legs Base (silhouette lotus) -->
  <path d="M 22 78 Q 50 86 78 78 Q 66 68 50 62 Q 34 68 22 78 Z" fill="#FFFFFF" />
  <!-- Arms resting on knees -->
  <polyline points="50,36 30,56 26,74" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <polyline points="50,36 70,56 74,74" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
</svg>""",

    # 9. Tadasana (Mountain Pose)
    # Tall standing upright, feet grounded, arms by sides
    "tadasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head -->
  <circle cx="50" cy="15" r="5.5" fill="#FFFFFF" />
  <!-- Spine -->
  <line x1="50" y1="21" x2="50" y2="56" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms down along torso -->
  <line x1="50" y1="28" x2="38" y2="58" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="50" y1="28" x2="62" y2="58" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Straight Legs -->
  <line x1="47" y1="56" x2="47" y2="92" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <line x1="53" y1="56" x2="53" y2="92" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
</svg>""",

    # 10. Virabhadrasana II (Warrior II)
    # Deep lunge, front knee 90°, back leg straight, arms extended parallel to floor
    "virabhadrasana_ii.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head -->
  <circle cx="48" cy="22" r="5.5" fill="#FFFFFF" />
  <!-- Torso Centered -->
  <line x1="48" y1="28" x2="48" y2="58" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Outstretched Horizontal Arms -->
  <line x1="16" y1="36" x2="80" y2="36" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Front Bent Knee (Left) -->
  <polyline points="48,58 24,62 24,90" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Back Straight Leg (Right) -->
  <line x1="48" y1="58" x2="82" y2="90" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
</svg>""",

    # 11. Paschimottanasana (Seated Forward Bend)
    # Seated, legs flat forward, torso folded forward reaching toes
    "paschimottanasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head folded down -->
  <circle cx="34" cy="52" r="5.5" fill="#FFFFFF" />
  <!-- Legs straight flat on mat -->
  <line x1="82" y1="76" x2="18" y2="76" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Folded Spine -->
  <path d="M 82 76 Q 62 50 38 54" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms reaching forward to toes -->
  <line x1="46" y1="56" x2="20" y2="72" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
</svg>""",

    # 12. Adho Mukha Svanasana (Downward Dog)
    # Inverted V: hands and feet on ground, hips peaked at apex
    "adho_mukha_svanasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head inside arms -->
  <circle cx="30" cy="58" r="5.5" fill="#FFFFFF" />
  <!-- Inverted V Peak at Pelvis (50, 28) -->
  <polyline points="18,80 50,28 82,80" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Spine Line -->
  <line x1="50" y1="28" x2="34" y2="54" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
</svg>""",

    # 13. Utkatasana (Chair Pose)
    # Deep squat, torso hinged slightly forward, arms extended overhead along ears
    "utkatasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Head -->
  <circle cx="38" cy="20" r="5.5" fill="#FFFFFF" />
  <!-- Torso hinged -->
  <line x1="42" y1="24" x2="62" y2="52" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <!-- Arms extended overhead -->
  <line x1="44" y1="28" x2="24" y2="8" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Squatting Legs (Chair) -->
  <polyline points="62,52 38,62 50,90" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
</svg>""",

    # 14. Pranamasana (Surya Step 1 & 12 - Prayer Pose)
    "pranamasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="16" r="5.5" fill="#FFFFFF" />
  <line x1="50" y1="22" x2="50" y2="56" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <polyline points="50,30 38,40 50,42 62,40 50,30" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <line x1="48" y1="56" x2="48" y2="92" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <line x1="52" y1="56" x2="52" y2="92" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
</svg>""",

    # 15. Hasta Uttanasana (Surya Step 2 & 11 - Raised Arms Backbend)
    "hasta_uttanasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="42" cy="18" r="5.5" fill="#FFFFFF" />
  <path d="M 44 24 Q 48 42 50 56" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <path d="M 46 28 Q 38 12 32 6" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="50" y1="56" x2="50" y2="92" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
</svg>""",

    # 16. Uttanasana / Padahastasana (Surya Step 3 & 10 - Standing Forward Bend)
    "uttanasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="42" cy="62" r="5.5" fill="#FFFFFF" />
  <line x1="50" y1="36" x2="50" y2="92" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <path d="M 50 36 Q 44 48 42 66" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <line x1="44" y1="54" x2="48" y2="88" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
</svg>""",

    # 17. Ashwa Sanchalanasana Left (Surya Step 4 - Equestrian Lunge Left)
    "ashwa_sanchalanasana_l.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="36" cy="32" r="5.5" fill="#FFFFFF" />
  <path d="M 38 38 Q 44 54 52 64" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <polyline points="52,64 28,66 28,86" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <path d="M 52 64 Q 72 68 88 84" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <line x1="42" y1="46" x2="38" y2="86" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
</svg>""",

    # 18. Dandasana / Plank (Surya Step 5 - Stick/Plank Pose)
    "dandasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="24" cy="46" r="5.5" fill="#FFFFFF" />
  <line x1="28" y1="50" x2="88" y2="76" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" />
  <line x1="36" y1="54" x2="36" y2="84" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="12" y1="86" x2="94" y2="86" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round" />
</svg>""",

    # 19. Ashtanga Namaskara (Surya Step 6 - Eight-Limbed Pose)
    "ashtanga_namaskara.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="20" cy="68" r="5.5" fill="#FFFFFF" />
  <!-- Chest down, hips elevated, knees and toes grounded -->
  <path d="M 24 72 Q 40 76 46 64 Q 56 50 68 62 L 78 80 L 90 82" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <polyline points="32,70 30,78 38,82" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <line x1="10" y1="86" x2="96" y2="86" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round" />
</svg>""",

    # 20. Parvatasana (Surya Step 8 - Mountain / Downward Inverted V)
    "parvatasana.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="30" cy="58" r="5.5" fill="#FFFFFF" />
  <polyline points="18,80 50,28 82,80" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <line x1="50" y1="28" x2="34" y2="54" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
</svg>"""
}

# Duplicate Left equestrian to Right equestrian
PERFECT_SVGS["ashwa_sanchalanasana_r.svg"] = PERFECT_SVGS["ashwa_sanchalanasana_l.svg"]

def generate():
    for name, content in PERFECT_SVGS.items():
        out_file = FIGURES_DIR / name
        out_file.write_text(content.strip(), encoding="utf-8")
        print(f"Generated perfect pose figure: {name}")

if __name__ == "__main__":
    generate()
