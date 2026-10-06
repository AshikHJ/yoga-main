"""
Generates clean, precise, professional SVG pose figures for KI.AI.
Each figure represents the exact anatomical geometry of that specific yoga pose.
"""

from pathlib import Path

OUT_DIR = Path("assets/pose_figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# SVG templates for distinct yoga postures
FIGURES = {
    # 1. Tadasana (Mountain Pose - tall upright, arms at sides)
    "tadasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="16" r="6" fill="#10B981" />
  <line x1="50" y1="22" x2="50" y2="52" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Arms at sides -->
  <line x1="50" y1="28" x2="38" y2="44" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="38" y1="44" x2="36" y2="56" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="50" y1="28" x2="62" y2="44" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="62" y1="44" x2="64" y2="56" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Straight legs -->
  <line x1="50" y1="52" x2="44" y2="72" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="44" y1="72" x2="44" y2="92" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="50" y1="52" x2="56" y2="72" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="56" y1="72" x2="56" y2="92" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Joints -->
  <circle cx="44" cy="72" r="2.5" fill="#34D399" />
  <circle cx="56" cy="72" r="2.5" fill="#34D399" />
</svg>""",

    # 2. Virabhadrasana II (Warrior II - deep bent front knee, straight back leg, arms horizontal)
    "virabhadrasana_ii": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="45" cy="20" r="6" fill="#10B981" />
  <line x1="45" y1="26" x2="46" y2="52" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Arms horizontal -->
  <line x1="16" y1="34" x2="45" y2="32" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <line x1="45" y1="32" x2="82" y2="34" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <!-- Front bent knee (90 deg) -->
  <line x1="46" y1="52" x2="70" y2="55" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="70" y1="55" x2="70" y2="88" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Back straight leg -->
  <line x1="46" y1="52" x2="28" y2="70" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="28" y1="70" x2="16" y2="88" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Highlights -->
  <circle cx="70" cy="55" r="3" fill="#34D399" />
</svg>""",

    # 3. Vrikshasana (Tree Pose - one leg standing, one foot on inner thigh, prayer hands)
    "vrikshasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="18" r="6" fill="#10B981" />
  <line x1="50" y1="24" x2="50" y2="52" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Arms raised overhead in prayer -->
  <line x1="50" y1="28" x2="38" y2="16" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="38" y1="16" x2="50" y2="8" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="50" y1="28" x2="62" y2="16" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="62" y1="16" x2="50" y2="8" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Standing leg (straight) -->
  <line x1="50" y1="52" x2="50" y2="72" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="50" y1="72" x2="50" y2="92" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Bent leg (tree foot on inner knee) -->
  <line x1="50" y1="52" x2="72" y2="64" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <line x1="72" y1="64" x2="52" y2="68" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <circle cx="72" cy="64" r="3" fill="#34D399" />
</svg>""",

    # 4. Trikonasana (Triangle Pose - wide legs, sideways reach, one arm down, one straight up)
    "trikonasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="40" cy="38" r="6" fill="#10B981" />
  <!-- Spine angled down -->
  <line x1="40" y1="44" x2="56" y2="52" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Vertical arm line -->
  <line x1="32" y1="12" x2="42" y2="40" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="42" y1="40" x2="50" y2="82" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Wide triangle legs -->
  <line x1="56" y1="52" x2="52" y2="86" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="56" y1="52" x2="80" y2="86" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <circle cx="32" cy="12" r="2.5" fill="#34D399" />
</svg>""",

    # 5. Utkatasana (Chair Pose - deep knee bend squat, torso angled, arms up)
    "utkatasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="42" cy="20" r="6" fill="#10B981" />
  <!-- Angled torso -->
  <line x1="42" y1="26" x2="52" y2="48" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Arms reaching forward-up -->
  <line x1="42" y1="30" x2="26" y2="14" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="26" y1="14" x2="20" y2="8" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Chair bent legs -->
  <line x1="52" y1="48" x2="34" y2="64" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="34" y1="64" x2="48" y2="88" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <circle cx="34" cy="64" r="3" fill="#34D399" />
</svg>""",

    # 6. Bhujangasana (Cobra Pose - prone on floor, chest arched backward)
    "bhujangasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="28" cy="28" r="6" fill="#10B981" />
  <!-- Arched spine -->
  <path d="M 28 34 Q 38 52 64 68" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Supporting arms -->
  <line x1="34" y1="42" x2="32" y2="70" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Legs flat on floor -->
  <line x1="64" y1="68" x2="88" y2="72" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Floor base line -->
  <line x1="18" y1="74" x2="94" y2="74" stroke="#334155" stroke-width="2" stroke-dasharray="2 2" />
</svg>""",

    # 7. Balasana (Child's Pose - kneeling resting, torso on thighs, arms forward)
    "balasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="30" cy="58" r="6" fill="#10B981" />
  <!-- Folded spine -->
  <path d="M 30 62 Q 50 48 70 60" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Folded knees -->
  <line x1="70" y1="60" x2="52" y2="72" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="52" y1="72" x2="74" y2="74" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Extended forward arms -->
  <line x1="36" y1="60" x2="16" y2="70" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Floor line -->
  <line x1="10" y1="76" x2="90" y2="76" stroke="#334155" stroke-width="2" stroke-dasharray="2 2" />
</svg>""",

    # 8. Adho Mukha Svanasana (Downward-Facing Dog - inverted V shape)
    "adho_mukha_svanasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="28" cy="64" r="5.5" fill="#10B981" />
  <!-- Arms & Back slope up to hips (Peak) -->
  <line x1="20" y1="76" x2="30" y2="60" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <line x1="30" y1="60" x2="52" y2="28" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Legs slope down to heels -->
  <line x1="52" y1="28" x2="68" y2="52" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="68" y1="52" x2="82" y2="76" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Hip peak highlight -->
  <circle cx="52" cy="28" r="3.5" fill="#34D399" />
  <line x1="12" y1="78" x2="90" y2="78" stroke="#334155" stroke-width="2" stroke-dasharray="2 2" />
</svg>""",

    # 9. Setu Bandhasana (Bridge Pose - supine, knees bent, pelvis arched up)
    "setu_bandhasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="24" cy="68" r="6" fill="#10B981" />
  <!-- Arched bridge spine -->
  <path d="M 28 68 Q 50 38 68 50" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Thighs and calves -->
  <line x1="68" y1="50" x2="80" y2="52" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="80" y1="52" x2="80" y2="74" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Arms on floor -->
  <line x1="30" y1="68" x2="54" y2="72" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <circle cx="56" cy="42" r="3" fill="#34D399" />
  <line x1="16" y1="76" x2="92" y2="76" stroke="#334155" stroke-width="2" stroke-dasharray="2 2" />
</svg>""",

    # 10. Dhanurasana (Bow Pose - belly on floor, back arched backward holding ankles)
    "dhanurasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="28" cy="34" r="6" fill="#10B981" />
  <!-- Bow arched body -->
  <path d="M 30 40 Q 50 72 74 38" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Arms holding ankles behind back -->
  <line x1="34" y1="44" x2="68" y2="34" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Feet lifted high -->
  <circle cx="72" cy="36" r="3" fill="#34D399" />
  <line x1="20" y1="72" x2="88" y2="72" stroke="#334155" stroke-width="2" stroke-dasharray="2 2" />
</svg>""",

    # 11. Natarajasana (Dancer Pose - standing on one leg, back leg arched up holding foot, forward arm)
    "natarajasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="48" cy="24" r="6" fill="#10B981" />
  <line x1="48" y1="30" x2="44" y2="52" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Front extended arm -->
  <line x1="48" y1="34" x2="22" y2="30" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <!-- Standing leg -->
  <line x1="44" y1="52" x2="44" y2="72" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="44" y1="72" x2="44" y2="92" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Back leg bent high backward -->
  <line x1="44" y1="52" x2="64" y2="40" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <line x1="64" y1="40" x2="68" y2="20" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <!-- Back arm holding high foot -->
  <line x1="48" y1="34" x2="66" y2="20" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" />
  <circle cx="68" cy="20" r="3" fill="#34D399" />
</svg>""",

    # 12. Sukhasana (Easy Pose - cross-legged seated meditation, straight spine)
    "sukhasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="24" r="6" fill="#10B981" />
  <line x1="50" y1="30" x2="50" y2="60" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Crossed knees / legs on floor -->
  <path d="M 28 78 Q 50 62 72 78" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <line x1="30" y1="76" x2="70" y2="76" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Arms resting on knees (Gyan Mudra) -->
  <line x1="50" y1="38" x2="34" y2="58" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="34" y1="58" x2="30" y2="72" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="50" y1="38" x2="66" y2="58" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="66" y1="58" x2="70" y2="72" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <circle cx="30" cy="72" r="2.5" fill="#34D399" />
  <circle cx="70" cy="72" r="2.5" fill="#34D399" />
</svg>""",

    # 13. Pranamasana (Surya Step 1 - Prayer Stance)
    "pranamasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="18" r="6" fill="#10B981" />
  <line x1="50" y1="24" x2="50" y2="54" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Palms pressed at heart center -->
  <line x1="50" y1="30" x2="42" y2="40" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="42" y1="40" x2="50" y2="38" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="50" y1="30" x2="58" y2="40" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="58" y1="40" x2="50" y2="38" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Straight legs -->
  <line x1="50" y1="54" x2="46" y2="92" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="50" y1="54" x2="54" y2="92" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <circle cx="50" cy="38" r="3" fill="#34D399" />
</svg>""",

    # 14. Hasta Uttanasana (Surya Step 2 - Raised Arms backbend)
    "hasta_uttanasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="42" cy="18" r="6" fill="#10B981" />
  <!-- Arched back upright -->
  <path d="M 44 24 Q 40 40 50 54" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Arms reaching up and slightly backward -->
  <line x1="44" y1="28" x2="34" y2="12" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <line x1="34" y1="12" x2="28" y2="4" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Straight legs -->
  <line x1="50" y1="54" x2="50" y2="92" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
</svg>""",

    # 15. Uttanasana (Surya Step 3 - Standing Forward Fold)
    "uttanasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="44" cy="66" r="6" fill="#10B981" />
  <!-- Fully folded spine down against legs -->
  <line x1="54" y1="40" x2="46" y2="60" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Arms hanging to ankles/floor -->
  <line x1="46" y1="58" x2="46" y2="86" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Straight standing legs -->
  <line x1="54" y1="40" x2="54" y2="90" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <circle cx="54" cy="40" r="3" fill="#34D399" />
</svg>""",

    # 16. Ashwa Sanchalanasana Right Leg Back (Surya Step 4 - Equestrian Lunge Right Back)
    "ashwa_sanchalanasana_r": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="34" cy="30" r="6" fill="#10B981" />
  <!-- Torso upright lunge -->
  <line x1="34" y1="36" x2="42" y2="60" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Front bent knee (Left Forward) -->
  <line x1="42" y1="60" x2="30" y2="64" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="30" y1="64" x2="30" y2="86" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Right leg extended straight back -->
  <line x1="42" y1="60" x2="68" y2="74" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <line x1="68" y1="74" x2="88" y2="86" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <!-- Hands on floor -->
  <line x1="36" y1="46" x2="28" y2="86" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" />
  <!-- Label badge for R-back -->
  <text x="74" y="24" font-family="Segoe UI, sans-serif" font-size="10" font-weight="bold" fill="#34D399">R ➔</text>
</svg>""",

    # 17. Ashwa Sanchalanasana Right Leg Forward / Left Back (Surya Step 9)
    "ashwa_sanchalanasana_l": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="66" cy="30" r="6" fill="#10B981" />
  <!-- Torso upright lunge facing right -->
  <line x1="66" y1="36" x2="58" y2="60" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Front bent knee (Right Forward) -->
  <line x1="58" y1="60" x2="70" y2="64" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <line x1="70" y1="64" x2="70" y2="86" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <!-- Left leg extended straight back -->
  <line x1="58" y1="60" x2="32" y2="74" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <line x1="32" y1="74" x2="12" y2="86" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <!-- Hands on floor -->
  <line x1="64" y1="46" x2="72" y2="86" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" />
  <!-- Label badge for R-forward -->
  <text x="14" y="24" font-family="Segoe UI, sans-serif" font-size="10" font-weight="bold" fill="#34D399">➔ R</text>
</svg>""",

    # 18. Dandasana / Plank (Surya Step 5 - Straight Plank on hands and toes)
    "dandasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="24" cy="40" r="5.5" fill="#10B981" />
  <!-- Straight diagonal plank line -->
  <line x1="28" y1="46" x2="84" y2="68" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Vertical supporting arms -->
  <line x1="36" y1="48" x2="36" y2="76" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <!-- Toes ground point -->
  <circle cx="84" cy="68" r="3" fill="#34D399" />
  <line x1="16" y1="78" x2="92" y2="78" stroke="#334155" stroke-width="2" stroke-dasharray="2 2" />
</svg>""",

    # 19. Ashtanga Namaskara (Surya Step 6 - Eight-Limbed Salute)
    "ashtanga_namaskara": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="22" cy="58" r="5.5" fill="#10B981" />
  <!-- Chest down, hips arched up, knees on ground -->
  <path d="M 26 62 Q 44 68 56 46 Q 66 44 72 70" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Bent arms supporting chest -->
  <line x1="32" y1="62" x2="30" y2="74" stroke="#10B981" stroke-width="3" stroke-linecap="round" />
  <!-- Knees and toes touching floor -->
  <circle cx="72" cy="70" r="3" fill="#34D399" />
  <line x1="72" y1="70" x2="88" y2="72" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" />
  <line x1="12" y1="76" x2="94" y2="76" stroke="#334155" stroke-width="2" stroke-dasharray="2 2" />
</svg>""",

    # 20. Parvatasana / Downward Dog (Surya Step 8 - Mountain Pose)
    "parvatasana": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="32" cy="62" r="5.5" fill="#10B981" />
  <!-- Back/arms slope up to hip peak -->
  <line x1="22" y1="74" x2="32" y2="60" stroke="#10B981" stroke-width="3.5" stroke-linecap="round" />
  <line x1="32" y1="60" x2="52" y2="28" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" />
  <!-- Legs slope down to heels -->
  <line x1="52" y1="28" x2="78" y2="74" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" />
  <circle cx="52" cy="28" r="3.5" fill="#34D399" />
  <line x1="14" y1="76" x2="90" y2="76" stroke="#334155" stroke-width="2" stroke-dasharray="2 2" />
</svg>"""
}

def main():
    print(f"Writing {len(FIGURES)} SVG pose figures to {OUT_DIR}...")
    for name, svg_content in FIGURES.items():
        file_path = OUT_DIR / f"{name}.svg"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(svg_content.strip())
        print(f"  * {file_path.name}")
    print("All SVG figures generated successfully!")

if __name__ == "__main__":
    main()
