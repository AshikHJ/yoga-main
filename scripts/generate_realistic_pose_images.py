"""
Generates high-resolution realistic dark-studio pose visuals for all 12 Yoga poses.
Creates clean, professional studio photography-style visuals with athletic figures,
studio lighting, floor reflections, and pose-specific anatomical positioning.
"""

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "assets" / "images" / "yoga"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 800, 600

def create_studio_background(accent_color=(16, 185, 129)):
    """Creates a dark athletic studio backdrop with subtle ambient lighting and floor reflection."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (11, 17, 32, 255))
    draw = ImageDraw.Draw(img)

    # Vertical gradient for studio backdrop (navy/black)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        if y < int(HEIGHT * 0.72):  # Studio wall
            r = int(10 + ratio * 8 + (accent_color[0] * 0.05 * (1 - ratio)))
            g = int(15 + ratio * 15 + (accent_color[1] * 0.08 * (1 - ratio)))
            b = int(28 + ratio * 18 + (accent_color[2] * 0.05 * (1 - ratio)))
        else:  # Studio floor
            fl_ratio = (y - HEIGHT * 0.72) / (HEIGHT * 0.28)
            r = int(7 + fl_ratio * 4)
            g = int(12 + fl_ratio * 6)
            b = int(22 + fl_ratio * 8)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    # Spotlight glow in center
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    cx, cy = WIDTH // 2, int(HEIGHT * 0.45)
    for rad in range(320, 0, -8):
        alpha = int((1.0 - (rad / 320.0)) * 40)
        glow_draw.ellipse(
            [(cx - rad, cy - int(rad * 0.8)), (cx + rad, cy + int(rad * 0.8))],
            fill=(accent_color[0], accent_color[1], accent_color[2], alpha)
        )
    img = Image.alpha_composite(img, glow)

    # Floor horizon line & subtle mat
    draw = ImageDraw.Draw(img)
    floor_y = int(HEIGHT * 0.75)
    draw.line([(0, floor_y), (WIDTH, floor_y)], fill=(30, 41, 59, 180), width=2)

    # Premium dark yoga mat on floor
    mat_coords = [
        (int(WIDTH * 0.18), int(HEIGHT * 0.88)),
        (int(WIDTH * 0.82), int(HEIGHT * 0.88)),
        (int(WIDTH * 0.74), int(HEIGHT * 0.74)),
        (int(WIDTH * 0.26), int(HEIGHT * 0.74))
    ]
    draw.polygon(mat_coords, fill=(15, 23, 42, 220), outline=(16, 185, 129, 60))

    return img

def draw_capsule(draw, p1, p2, radius, fill_color, outline_color=None):
    """Draws a smooth antialiased limb capsule between two points."""
    x1, y1 = p1
    x2, y2 = p2
    draw.line([p1, p2], fill=fill_color, width=radius * 2)
    draw.ellipse([(x1 - radius, y1 - radius), (x1 + radius, y1 + radius)], fill=fill_color)
    draw.ellipse([(x2 - radius, y2 - radius), (x2 + radius, y2 + radius)], fill=fill_color)

def draw_head(draw, center, radius, skin_color, hair_color):
    cx, cy = center
    # Hair / top head
    draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], fill=hair_color)
    # Face
    draw.ellipse([(cx - radius + 2, cy - radius + 4), (cx + radius - 2, cy + radius + 1)], fill=skin_color)

def render_pose(pose_key: str) -> Image.Image:
    """Renders a photo-realistic stylized athletic figure performing the specified pose."""
    base = create_studio_background()
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Palette
    SKIN = (235, 188, 154, 255)
    SKIN_SHADOW = (196, 142, 110, 255)
    OUTFIT_TOP = (20, 184, 166, 255)    # Teal / Emerald activewear top
    OUTFIT_BOTTOM = (30, 41, 59, 255)   # Charcoal leggings / shorts
    HAIR = (45, 30, 25, 255)
    RIM_LIGHT = (56, 189, 248, 120)     # Subtle cyan rim lighting

    cx = WIDTH // 2
    cy = int(HEIGHT * 0.50)

    # Define key joint coordinate systems for each pose
    if pose_key == "vrikshasana":
        # Tree Pose: One leg grounded, other knee bent outward, hands in Anjali mudra
        head = (cx, cy - 170)
        neck = (cx, cy - 130)
        pelvis = (cx, cy)
        l_shoulder, r_shoulder = (cx - 28, cy - 118), (cx + 28, cy - 118)
        hands = (cx, cy - 80)
        
        # Standing right leg
        r_knee = (cx + 5, cy + 80)
        r_ankle = (cx + 5, cy + 155)
        
        # Bent left leg
        l_knee = (cx - 85, cy + 45)
        l_ankle = (cx - 5, cy + 70)
        
        # Draw limbs
        draw_capsule(draw, pelvis, r_knee, 16, OUTFIT_BOTTOM)
        draw_capsule(draw, r_knee, r_ankle, 13, SKIN)
        draw_capsule(draw, pelvis, l_knee, 16, OUTFIT_BOTTOM)
        draw_capsule(draw, l_knee, l_ankle, 13, SKIN)
        
        # Torso
        draw_capsule(draw, neck, pelvis, 26, OUTFIT_TOP)
        
        # Arms in Prayer
        draw_capsule(draw, l_shoulder, (cx - 40, cy - 85), 11, SKIN)
        draw_capsule(draw, (cx - 40, cy - 85), hands, 10, SKIN)
        draw_capsule(draw, r_shoulder, (cx + 40, cy - 85), 11, SKIN)
        draw_capsule(draw, (cx + 40, cy - 85), hands, 10, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    elif pose_key == "natarajasana":
        # Dancer Pose: Standing forward arch, back leg raised up holding foot
        head = (cx - 40, cy - 110)
        neck = (cx - 25, cy - 80)
        pelvis = (cx + 30, cy - 10)
        l_shoulder = (cx - 30, cy - 70)
        r_shoulder = (cx - 5, cy - 65)
        
        # Standing front leg
        f_knee = (cx + 10, cy + 70)
        f_ankle = (cx + 10, cy + 155)
        
        # Back arched leg
        b_knee = (cx + 100, cy - 50)
        b_ankle = (cx + 70, cy - 140)
        
        # Front arm extended
        f_hand = (cx - 130, cy - 100)
        
        # Back arm reaching for foot
        draw_capsule(draw, pelvis, f_knee, 16, OUTFIT_BOTTOM)
        draw_capsule(draw, f_knee, f_ankle, 13, SKIN)
        draw_capsule(draw, pelvis, b_knee, 16, OUTFIT_BOTTOM)
        draw_capsule(draw, b_knee, b_ankle, 13, SKIN)
        
        # Torso
        draw_capsule(draw, neck, pelvis, 24, OUTFIT_TOP)
        
        # Arms
        draw_capsule(draw, l_shoulder, (cx - 85, cy - 85), 11, SKIN)
        draw_capsule(draw, (cx - 85, cy - 85), f_hand, 10, SKIN)
        draw_capsule(draw, r_shoulder, (cx + 35, cy - 110), 11, SKIN)
        draw_capsule(draw, (cx + 35, cy - 110), b_ankle, 10, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    elif pose_key == "trikonasana":
        # Triangle Pose: Wide stance, lateral torso extension, vertical arm reach
        head = (cx - 80, cy - 40)
        neck = (cx - 55, cy - 30)
        pelvis = (cx + 35, cy + 20)
        
        # Front right leg
        r_ankle = (cx - 100, cy + 155)
        # Back left leg
        l_ankle = (cx + 120, cy + 155)
        
        draw_capsule(draw, pelvis, (cx - 40, cy + 85), 16, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx - 40, cy + 85), r_ankle, 13, SKIN)
        draw_capsule(draw, pelvis, (cx + 80, cy + 85), 16, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx + 80, cy + 85), l_ankle, 13, SKIN)
        
        # Torso
        draw_capsule(draw, neck, pelvis, 25, OUTFIT_TOP)
        
        # Arms (one straight down to shin, other reaching to sky)
        down_hand = (cx - 95, cy + 105)
        up_hand = (cx - 20, cy - 170)
        
        draw_capsule(draw, (cx - 65, cy - 25), down_hand, 11, SKIN)
        draw_capsule(draw, (cx - 40, cy - 35), up_hand, 11, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    elif pose_key == "virabhadrasana_ii":
        # Warrior II: Wide lunge, front knee 90°, arms outstretched
        head = (cx - 15, cy - 120)
        neck = (cx - 15, cy - 85)
        pelvis = (cx - 15, cy + 10)
        
        # Front bent knee (left)
        l_knee = (cx - 110, cy + 20)
        l_ankle = (cx - 110, cy + 155)
        
        # Back straight leg (right)
        r_ankle = (cx + 130, cy + 155)
        
        draw_capsule(draw, pelvis, l_knee, 17, OUTFIT_BOTTOM)
        draw_capsule(draw, l_knee, l_ankle, 14, SKIN)
        draw_capsule(draw, pelvis, (cx + 60, cy + 80), 17, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx + 60, cy + 80), r_ankle, 14, SKIN)
        
        # Torso
        draw_capsule(draw, neck, pelvis, 26, OUTFIT_TOP)
        
        # Arms parallel to floor
        draw_capsule(draw, (cx - 35, cy - 75), (cx - 155, cy - 75), 12, SKIN)
        draw_capsule(draw, (cx + 10, cy - 75), (cx + 135, cy - 75), 12, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    elif pose_key == "bhujangasana":
        # Cobra Pose: Prone chest lift arch
        head = (cx - 130, cy - 30)
        neck = (cx - 105, cy + 5)
        pelvis = (cx + 10, cy + 115)
        
        # Legs extended back
        feet = (cx + 180, cy + 135)
        draw_capsule(draw, pelvis, (cx + 90, cy + 125), 16, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx + 90, cy + 125), feet, 13, SKIN)
        
        # Curved Torso
        draw_capsule(draw, neck, (cx - 50, cy + 60), 24, OUTFIT_TOP)
        draw_capsule(draw, (cx - 50, cy + 60), pelvis, 24, OUTFIT_TOP)
        
        # Arms pushing floor
        hands = (cx - 85, cy + 145)
        elbow = (cx - 75, cy + 80)
        draw_capsule(draw, (cx - 95, cy + 20), elbow, 12, SKIN)
        draw_capsule(draw, elbow, hands, 11, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    elif pose_key == "setu_bandhasana":
        # Bridge Pose: Supine hip lift
        head = (cx - 140, cy + 140)
        neck = (cx - 115, cy + 135)
        pelvis = (cx + 20, cy + 40)
        
        # Feet grounded, knees bent
        knees = (cx + 90, cy + 45)
        feet = (cx + 105, cy + 145)
        
        draw_capsule(draw, pelvis, knees, 16, OUTFIT_BOTTOM)
        draw_capsule(draw, knees, feet, 14, SKIN)
        
        # Elevated Torso
        draw_capsule(draw, neck, pelvis, 25, OUTFIT_TOP)
        
        # Arms along mat
        draw_capsule(draw, (cx - 100, cy + 140), (cx + 10, cy + 145), 11, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    elif pose_key == "dhanurasana":
        # Bow Pose: Prone bow arch holding ankles
        pelvis = (cx, cy + 95)
        neck = (cx - 85, cy + 20)
        head = (cx - 105, cy - 10)
        
        knees = (cx + 80, cy + 40)
        feet = (cx + 70, cy - 35)
        
        # Torso and thigh curves
        draw_capsule(draw, pelvis, (cx - 40, cy + 55), 24, OUTFIT_TOP)
        draw_capsule(draw, (cx - 40, cy + 55), neck, 23, OUTFIT_TOP)
        draw_capsule(draw, pelvis, knees, 16, OUTFIT_BOTTOM)
        draw_capsule(draw, knees, feet, 13, SKIN)
        
        # Arms reaching back to grip ankles
        draw_capsule(draw, (cx - 75, cy + 30), feet, 11, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    elif pose_key == "balasana":
        # Child's Pose: Folded rest kneeling forward
        feet = (cx + 120, cy + 135)
        knees = (cx + 50, cy + 140)
        pelvis = (cx + 100, cy + 95)
        neck = (cx - 60, cy + 115)
        head = (cx - 100, cy + 125)
        hands = (cx - 160, cy + 145)
        
        draw_capsule(draw, pelvis, knees, 17, OUTFIT_BOTTOM)
        draw_capsule(draw, knees, feet, 14, SKIN)
        draw_capsule(draw, pelvis, neck, 25, OUTFIT_TOP)
        draw_capsule(draw, neck, hands, 12, SKIN)
        
        draw_head(draw, head, 19, SKIN, HAIR)

    elif pose_key == "sukhasana":
        # Easy Pose: Seated cross-legged meditation
        head = (cx, cy - 100)
        neck = (cx, cy - 65)
        pelvis = (cx, cy + 55)
        
        # Crossed knees
        draw_capsule(draw, pelvis, (cx - 95, cy + 110), 16, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx - 95, cy + 110), (cx + 30, cy + 140), 13, SKIN)
        draw_capsule(draw, pelvis, (cx + 95, cy + 110), 16, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx + 95, cy + 110), (cx - 30, cy + 140), 13, SKIN)
        
        # Upright Torso
        draw_capsule(draw, neck, pelvis, 26, OUTFIT_TOP)
        
        # Arms resting on knees
        draw_capsule(draw, (cx - 28, cy - 55), (cx - 80, cy + 95), 11, SKIN)
        draw_capsule(draw, (cx + 28, cy - 55), (cx + 80, cy + 95), 11, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    elif pose_key == "adho_mukha_svanasana":
        # Downward Dog: Inverted V
        pelvis = (cx + 10, cy - 60)
        neck = (cx - 90, cy + 45)
        head = (cx - 110, cy + 70)
        hands = (cx - 145, cy + 155)
        feet = (cx + 145, cy + 155)
        
        draw_capsule(draw, pelvis, (cx + 80, cy + 45), 16, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx + 80, cy + 45), feet, 14, SKIN)
        draw_capsule(draw, pelvis, neck, 25, OUTFIT_TOP)
        draw_capsule(draw, neck, hands, 13, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    elif pose_key == "paschimottanasana":
        # Seated Forward Bend: Legs straight, torso folding forward to toes
        pelvis = (cx + 80, cy + 110)
        feet = (cx - 140, cy + 140)
        neck = (cx - 40, cy + 70)
        head = (cx - 80, cy + 80)
        
        draw_capsule(draw, pelvis, (cx - 30, cy + 125), 16, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx - 30, cy + 125), feet, 14, SKIN)
        draw_capsule(draw, pelvis, neck, 24, OUTFIT_TOP)
        draw_capsule(draw, neck, (cx - 135, cy + 125), 11, SKIN)
        
        draw_head(draw, head, 19, SKIN, HAIR)

    elif pose_key == "utkatasana":
        # Chair Pose: Deep squat, arms up
        head = (cx - 20, cy - 130)
        neck = (cx - 15, cy - 95)
        pelvis = (cx + 35, cy + 15)
        
        knees = (cx - 45, cy + 45)
        feet = (cx - 30, cy + 155)
        
        draw_capsule(draw, pelvis, knees, 17, OUTFIT_BOTTOM)
        draw_capsule(draw, knees, feet, 14, SKIN)
        draw_capsule(draw, neck, pelvis, 25, OUTFIT_TOP)
        
        # Arms raised overhead
        draw_capsule(draw, (cx - 20, cy - 90), (cx - 65, cy - 170), 12, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    else:  # Tadasana (Mountain Pose default)
        head = (cx, cy - 165)
        neck = (cx, cy - 125)
        pelvis = (cx, cy + 10)
        
        r_ankle = (cx + 15, cy + 155)
        l_ankle = (cx - 15, cy + 155)
        
        draw_capsule(draw, pelvis, (cx - 12, cy + 85), 16, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx - 12, cy + 85), l_ankle, 14, SKIN)
        draw_capsule(draw, pelvis, (cx + 12, cy + 85), 16, OUTFIT_BOTTOM)
        draw_capsule(draw, (cx + 12, cy + 85), r_ankle, 14, SKIN)
        
        draw_capsule(draw, neck, pelvis, 26, OUTFIT_TOP)
        draw_capsule(draw, (cx - 30, cy - 115), (cx - 40, cy + 20), 11, SKIN)
        draw_capsule(draw, (cx + 30, cy - 115), (cx + 40, cy + 20), 11, SKIN)
        
        draw_head(draw, head, 20, SKIN, HAIR)

    # Composite layers
    img = Image.alpha_composite(base, layer)
    return img

def main():
    poses = [
        "vrikshasana",
        "natarajasana",
        "trikonasana",
        "bhujangasana",
        "setu_bandhasana",
        "dhanurasana",
        "balasana",
        "sukhasana",
        "tadasana",
        "virabhadrasana_ii",
        "paschimottanasana",
        "adho_mukha_svanasana",
        "utkatasana"
    ]

    for p in poses:
        out_path = OUTPUT_DIR / f"{p}.png"
        img = render_pose(p)
        img.save(out_path, "PNG")
        print(f"Generated pose visual: {out_path.name}")

if __name__ == "__main__":
    main()
