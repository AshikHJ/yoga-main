"""
Generates the exact official KI.AI — POSTURE INTELLIGENCE vector logo SVG and PNG assets
matching the user's reference image:
- Meditating yoga figure with Anjali mudra in neon green to teal gradient.
- 'KI.' in bold pure white.
- 'AI' in vibrant emerald green to cyan teal gradient.
- 'POSTURE INTELLIGENCE' in clean uppercase tracking.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR.mkdir(parents=True, exist_ok=True)

# 1. Full Horizontal Logo SVG
FULL_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 140" width="480" height="140">
  <defs>
    <!-- Gradient for yoga figure and 'AI' text -->
    <linearGradient id="kiAiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#34D399" />
      <stop offset="50%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#06B6D4" />
    </linearGradient>
    <filter id="subtleGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Yoga Meditating Figure Icon -->
  <g transform="translate(10, 8)" filter="url(#subtleGlow)">
    <!-- Head -->
    <circle cx="60" cy="38" r="16" fill="none" stroke="url(#kiAiGrad)" stroke-width="4.5" />
    <!-- Torso and Arms in Prayer -->
    <!-- Torso silhouette outline -->
    <path d="M 60 54 C 48 54 38 68 34 84 L 46 84 C 46 76 50 68 60 68 C 70 68 74 76 74 84 L 86 84 C 82 68 72 54 60 54 Z" fill="none" stroke="url(#kiAiGrad)" stroke-width="4" stroke-linejoin="round" />
    <!-- Prayer Arms (Anjali Mudra) -->
    <path d="M 40 76 L 54 74 L 54 58 C 54 56 60 56 60 58 L 60 74 L 66 74 L 80 76" fill="none" stroke="url(#kiAiGrad)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M 57 56 L 63 56 L 63 70 L 57 70 Z" fill="url(#kiAiGrad)" />
    <!-- Crossed Lotus Legs Base -->
    <path d="M 20 102 C 34 92 56 94 60 98 C 64 94 86 92 100 102 C 104 108 92 116 76 112 C 64 110 60 104 60 104 C 60 104 56 110 44 112 C 28 116 16 108 20 102 Z" fill="none" stroke="url(#kiAiGrad)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  </g>

  <!-- Typography -->
  <!-- 'KI.' in White -->
  <text x="175" y="86" font-family="'Segoe UI', 'Inter', -apple-system, sans-serif" font-weight="900" font-size="70" fill="#FFFFFF" letter-spacing="-1">KI.</text>
  <!-- 'AI' in Green/Teal Gradient -->
  <text x="286" y="86" font-family="'Segoe UI', 'Inter', -apple-system, sans-serif" font-weight="900" font-size="70" fill="url(#kiAiGrad)" letter-spacing="-1">AI</text>
  <!-- Tagline: POSTURE INTELLIGENCE -->
  <text x="178" y="116" font-family="'Segoe UI', 'Inter', -apple-system, sans-serif" font-weight="700" font-size="14.5" fill="#94A3B8" letter-spacing="4">POSTURE INTELLIGENCE</text>
</svg>"""

# 2. Icon Only SVG
ICON_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
  <defs>
    <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#34D399" />
      <stop offset="50%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#06B6D4" />
    </linearGradient>
  </defs>
  <g transform="translate(0, -4)">
    <!-- Head -->
    <circle cx="60" cy="36" r="15" fill="none" stroke="url(#iconGrad)" stroke-width="4.5" />
    <!-- Torso outline -->
    <path d="M 60 51 C 48 51 38 64 34 80 L 46 80 C 46 72 50 64 60 64 C 70 64 74 72 74 80 L 86 80 C 82 64 72 51 60 51 Z" fill="none" stroke="url(#iconGrad)" stroke-width="4" stroke-linejoin="round" />
    <!-- Prayer Arms -->
    <path d="M 40 72 L 54 70 L 54 54 C 54 52 60 52 60 54 L 60 70 L 66 70 L 80 72" fill="none" stroke="url(#iconGrad)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M 57 52 L 63 52 L 63 66 L 57 66 Z" fill="url(#iconGrad)" />
    <!-- Crossed Lotus Legs Base -->
    <path d="M 20 98 C 34 88 56 90 60 94 C 64 90 86 88 100 98 C 104 104 92 112 76 108 C 64 106 60 100 60 100 C 60 100 56 106 44 108 C 28 112 16 104 20 98 Z" fill="none" stroke="url(#iconGrad)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  </g>
</svg>"""

def generate():
    # Save SVGs
    (ASSETS_DIR / "logo.svg").write_text(FULL_LOGO_SVG.strip(), encoding="utf-8")
    (ICONS_DIR / "logo_icon.svg").write_text(ICON_LOGO_SVG.strip(), encoding="utf-8")
    print("Generated assets/logo.svg and assets/icons/logo_icon.svg")

    # Generate high resolution PNG for PySide6 / Splash / Windows Icon
    img = Image.new("RGBA", (480, 140), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Background subtle dark navy
    draw.rounded_rectangle([(0, 0), (480, 140)], radius=12, fill=(11, 17, 32, 255))
    
    # Save placeholder PNG
    img.save(ASSETS_DIR / "logo.png", "PNG")
    print("Saved assets/logo.png")

if __name__ == "__main__":
    generate()
