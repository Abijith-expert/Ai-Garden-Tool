"""
Paysagea AI Garden Design Engine v10
─────────────────────────────────────
PIPELINE:
  1. Landscape algorithm designs the garden (zones, clusters, drifts, layers)
  2. PIL composites actual plant cutout PNGs onto the photo
  3. HuggingFace img2img HARMONIZES the composite (blending, lighting, shadows)
  4. Returns a polished, photorealistic JPEG

DESIGN PHILOSOPHY (real landscape architecture):
  - THRILLER, FILLER, SPILLER: every bed has a tall focal, mid filler, low spiller
  - DRIFT PLANTING: same species in elongated groups of 3-7 (odd numbers)
  - ODD NUMBERS: always plant 3, 5, 7 of same species (never 2, 4, 6)
  - LAYERED HEIGHTS: back-to-front height gradient within each bed
  - RHYTHM & REPETITION: same plant combo repeats across the garden
  - NEGATIVE SPACE: 30-40% of lawn stays open for balance
  - EDGE SOFTENING: plants along borders soften hard lines of walls/fences
  - FOCAL POINTS: 1-2 specimen plants at golden ratio positions
"""

import math
import random
import io
import os
from pathlib import Path
from typing import Optional
from collections import Counter

import httpx
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageStat
from models import PlacedPlant, PlantInfo

PLANTS_DIR = Path(os.getenv("PLANTS_DIR", "plants_dataset"))
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_API_BASE = "https://router.huggingface.co/hf-inference/models"


# ════════════════════════════════════════════════════
#  NEW: PHOTO ANALYSIS (ground detection, obstacles)
# ════════════════════════════════════════════════════

def analyze_photo(img: Image.Image) -> dict:
    """
    Analyze the garden photo to find ground line, brightness, obstacles.
    Returns dict with ground_y, brightness, ground_color, obstacles.
    """
    w, h = img.size
    rgb = img.convert("RGB")

    # Find where green/brown ground starts
    ground_y_pct = 55
    for y_pct in range(35, 75):
        y = int(h * y_pct / 100)
        strip = rgb.crop((0, y, w, min(y + 5, h)))
        stat = ImageStat.Stat(strip)
        r, g, b = stat.mean[:3]
        if (g > r * 0.85 and g > 60) or (r > 80 and g > 60 and b < r * 0.9):
            ground_y_pct = y_pct
            break

    # Scene brightness
    stat = ImageStat.Stat(rgb)
    avg_brightness = sum(stat.mean[:3]) / 3 / 255

    # Ground color sample
    ground_strip = rgb.crop((int(w * 0.2), int(h * 0.7), int(w * 0.8), int(h * 0.85)))
    ground_stat = ImageStat.Stat(ground_strip)
    ground_color = tuple(int(c) for c in ground_stat.mean[:3])

    # Detect obstacle zones (dark structures, furniture, paths)
    obstacles = []
    bw, bh = w // 10, h // 10
    for bx in range(10):
        for by_idx in range(10):
            by_pct = ground_y_pct + (by_idx / 10) * (95 - ground_y_pct)
            by_px = int(h * by_pct / 100)
            if by_px + bh > h:
                continue
            block = rgb.crop((bx * bw, by_px, (bx + 1) * bw, by_px + bh))
            bs = ImageStat.Stat(block)
            r, g, b = bs.mean[:3]
            brightness = (r + g + b) / 3
            is_obstacle = brightness < 80 or (abs(r - g) < 15 and abs(g - b) < 15 and brightness < 120)
            is_obstacle = is_obstacle or (brightness > 200 and abs(r - g) < 20)
            if is_obstacle:
                obstacles.append({"x_pct": bx * 10 + 5, "y_pct": by_pct + 2})

    return {
        "ground_y": ground_y_pct,
        "brightness": avg_brightness,
        "ground_color": ground_color,
        "obstacles": obstacles,
    }


def feather_edges(img: Image.Image, radius: int = 2) -> Image.Image:
    """Soften cutout PNG edges to remove hard sticker borders."""
    if img.mode != "RGBA":
        return img
    r, g, b, a = img.split()

    a_eroded = a.filter(ImageFilter.MinFilter(size=3))
    a_blurred = a_eroded.filter(ImageFilter.GaussianBlur(radius=radius))

    a_np = np.array(a)
    a_blur_np = np.array(a_blurred)

    # Only soften edges, keep interior opaque
    edge = (a_np > 20) & (a_np < 200)
    result = a_np.copy()
    result[edge] = a_blur_np[edge]
    border = (a_np >= 200) & (a_np < 255)
    result[border] = np.clip(a_blur_np[border].astype(int) + 30, 0, 255).astype(np.uint8)

    return Image.merge("RGBA", (r, g, b, Image.fromarray(result, "L")))


# ════════════════════════════════════════════════════
#  1. LANDSCAPE DESIGN ENGINE
# ════════════════════════════════════════════════════
# Zones (y_percent where plant BASE sits on ground):
#   BACKDROP:   62-67%  along wall/fence base
#   MID-BORDER: 68-78%  main planting beds
#   FOREGROUND: 79-93%  low plants near camera

class GardenDesigner:
    """Designs a garden like a real landscape architect."""

    ZONE_BACK = (62, 67)
    ZONE_MID = (68, 78)
    ZONE_FRONT = (79, 93)

    # Height tiers for layering
    TIER_TALL = ["trees", "climbers"]
    TIER_MID = ["shrubs", "hedges", "ornamental"]
    TIER_LOW = ["flowers", "groundcover"]

    # NEW: exclude empty pots/containers/decorations from auto-design
    EXCLUDE_KEYWORDS = {
        "pot", "bac", "jardiniere", "composition", "container", "planter",
        "vasque", "cache", "coupe", "corbeille", "suspension", "contenant",
        "balconniere", "deco", "statue", "bordure", "galet", "gravier",
    }

    def __init__(self, plants: list[PlantInfo], style="natural", density="medium",
                 photo_analysis: dict = None):
        self.plants = plants
        self.style = style
        self.density = density
        self.target = {"sparse": 20, "medium": 32, "dense": 48}.get(density, 32)
        self.result: list[PlacedPlant] = []
        self.positions: list[tuple[float, float]] = []
        self.species_count: Counter = Counter()  # NEW: variety control

        # NEW: photo-aware zones
        pa = photo_analysis or {}
        gy = pa.get("ground_y", 55)
        self.obstacles = pa.get("obstacles", [])
        # Dynamic zones based on actual ground detection
        self.ZONE_BACK = (max(gy + 2, 55), gy + 10)
        self.ZONE_MID = (gy + 10, gy + 22)
        self.ZONE_FRONT = (gy + 22, min(95, gy + 38))

        # Organize by category, FILTERING OUT empty pots/containers
        self.by_cat: dict[str, list[PlantInfo]] = {}
        self.real_plants: list[PlantInfo] = []
        for p in plants:
            if p.category == "potted":
                continue
            name_lower = (p.name + " " + p.filename).lower()
            if any(kw in name_lower for kw in self.EXCLUDE_KEYWORDS):
                continue
            self.by_cat.setdefault(p.category, []).append(p)
            self.real_plants.append(p)

    def pick(self, cat: str, fallbacks=None) -> PlantInfo:
        pool = self.by_cat.get(cat, [])
        if not pool:
            for fb in (fallbacks or []):
                pool = self.by_cat.get(fb, [])
                if pool:
                    break
        if not pool:
            pool = self.real_plants if self.real_plants else self.plants
        # NEW: variety control — max 5 of any single species
        available = [p for p in pool if self.species_count[p.id] < 5]
        if not available:
            available = pool
        choice = random.choice(available)
        self.species_count[choice.id] += 1
        return choice

    def place(self, pid, x, y, scale=1.0, rot=0.0, flip=False):
        x = max(3, min(97, x + random.uniform(-0.8, 0.8)))
        y = max(self.ZONE_BACK[0], min(self.ZONE_FRONT[1], y))
        # NEW: avoid detected obstacles (chairs, paths, structures)
        for ob in self.obstacles:
            if math.hypot(x - ob["x_pct"], y - ob["y_pct"]) < 8:
                x += random.choice([-10, 10])
                x = max(3, min(97, x))
                if math.hypot(x - ob["x_pct"], y - ob["y_pct"]) < 6:
                    return  # skip this position
        # Push away from overlaps
        for ux, uy in self.positions:
            if math.hypot(x - ux, y - uy) < 3.5:
                x += random.choice([-4, 4])
                x = max(3, min(97, x))
        self.result.append(PlacedPlant(
            id=f"p{len(self.result)}", plant_id=pid,
            x_percent=round(x, 1), y_percent=round(y, 1),
            scale=round(scale, 2), rotation=round(rot, 1), flip_h=flip,
        ))
        self.positions.append((x, y))

    def _rflip(self):
        return random.random() > 0.5

    def _rrot(self, max_deg=3):
        return round(random.uniform(-max_deg, max_deg), 1)

    def _drift(self, plant: PlantInfo, cx, cy, count, spread_x=5, spread_y=2, scale_range=(0.7, 1.0)):
        """Plant a DRIFT of same species — elongated natural group."""
        # Drifts are wider than deep (like real garden borders)
        angle_base = random.uniform(0, math.pi)  # random drift direction
        for i in range(count):
            t = (i / max(1, count - 1)) - 0.5  # -0.5 to 0.5
            dx = t * spread_x * 2 + random.uniform(-1.5, 1.5)
            dy = random.uniform(-spread_y, spread_y)
            # Rotate the drift slightly
            rx = dx * math.cos(angle_base) - dy * math.sin(angle_base)
            ry = dx * math.sin(angle_base) + dy * math.cos(angle_base)
            self.place(
                plant.id,
                cx + rx,
                max(self.ZONE_BACK[0], min(self.ZONE_FRONT[1], cy + ry * 0.5)),
                random.uniform(*scale_range),
                self._rrot(2),
                self._rflip(),
            )

    def _bed(self, cx, cy, width=12, depth=6):
        """
        Create a PLANTING BED with thriller-filler-spiller layers.
        Thriller: 1 tall focal at back-center
        Filler:   3-5 mid-height plants around it
        Spiller:  3-5 low plants at the front edge
        """
        if len(self.result) >= self.target - 3:
            return

        # Thriller (back of bed)
        thriller = self.pick("shrubs", ["ornamental", "hedges"])
        self.place(thriller.id, cx, cy - depth * 0.3,
                   random.uniform(1.0, 1.2), self._rrot(), self._rflip())

        # Filler (sides and around thriller) — same species, odd number
        filler = self.pick("flowers", ["ornamental", "potted"])
        filler_count = random.choice([3, 5])
        for i in range(filler_count):
            if len(self.result) >= self.target - 2:
                break
            angle = (i / filler_count) * math.pi + random.uniform(-0.2, 0.2)
            dist = width * 0.3 + random.uniform(0, width * 0.15)
            fx = cx + math.cos(angle) * dist
            fy = cy + math.sin(angle) * (depth * 0.2) + random.uniform(-1, 1)
            fy = max(self.ZONE_BACK[0], min(self.ZONE_FRONT[1], fy))
            self.place(filler.id, fx, fy,
                       random.uniform(0.7, 0.95), self._rrot(), self._rflip())

        # Spiller (front edge of bed)
        spiller = self.pick("groundcover", ["flowers"])
        spiller_count = random.choice([3, 5])
        for i in range(spiller_count):
            if len(self.result) >= self.target - 1:
                break
            sx = cx + (i - spiller_count // 2) * (width * 0.2) + random.uniform(-1.5, 1.5)
            sy = cy + depth * 0.4 + random.uniform(-0.5, 1.5)
            sy = max(self.ZONE_BACK[0], min(self.ZONE_FRONT[1], sy))
            self.place(spiller.id, sx, sy,
                       random.uniform(0.6, 0.85), 0, self._rflip())

    def design(self) -> list[PlacedPlant]:
        """Execute the full garden design."""

        # ─── 1. FOCAL SPECIMEN TREES ───
        # Place at golden ratio positions (1/3 and 2/3 of width)
        focal_positions = [30, 70] if self.style != "formal" else [25, 75]
        for fx in focal_positions[:2]:
            if len(self.result) >= self.target:
                break
            tree = self.pick("trees", ["shrubs"])
            self.place(tree.id, fx + random.uniform(-5, 5),
                       random.uniform(62, 65),
                       random.uniform(1.1, 1.4), self._rrot(2), self._rflip())

        # ─── 2. BACK BORDER ───
        # Continuous planting along wall/fence base to soften hard edges
        # Mix of tall shrubs with accent flowers
        border_shrub = self.pick("shrubs", ["hedges"])
        border_flower = self.pick("flowers", ["ornamental"])

        # Place shrubs every ~12% along the back
        back_xs = list(range(8, 95, 12))
        random.shuffle(back_xs)
        for bx in back_xs[:6]:
            if len(self.result) >= self.target * 0.4:
                break
            # Skip if too close to focal trees
            if any(abs(bx - ux) < 8 for ux, _ in self.positions):
                continue
            self.place(border_shrub.id, bx,
                       random.uniform(63, 67),
                       random.uniform(0.75, 1.05), self._rrot(), self._rflip())

        # Accent flowers in gaps along the border (drifts of 3)
        for gx in [15, 45, 75]:
            if len(self.result) >= self.target * 0.45:
                break
            if any(abs(gx - ux) < 6 for ux, _ in self.positions):
                continue
            self._drift(border_flower, gx, 66, count=3,
                        spread_x=4, spread_y=1.5, scale_range=(0.6, 0.85))

        # ─── 3. MAIN PLANTING BEDS (thriller-filler-spiller) ───
        if self.style == "formal":
            bed_centers = [{"x": 30, "y": 73}, {"x": 70, "y": 73}]
        elif self.style == "modern":
            bed_centers = [{"x": 25, "y": 74}, {"x": 65, "y": 72}]
        elif self.style == "cottage":
            bed_centers = [
                {"x": 20, "y": 72}, {"x": 50, "y": 75},
                {"x": 78, "y": 71}, {"x": 35, "y": 78},
            ]
        else:  # natural, tropical, mediterranean
            bed_centers = [
                {"x": 22, "y": 73}, {"x": 55, "y": 76}, {"x": 82, "y": 71},
            ]

        for bed in bed_centers:
            self._bed(bed["x"], bed["y"],
                      width=10 + random.uniform(-2, 3),
                      depth=5 + random.uniform(-1, 2))

        # ─── 4. FOREGROUND DRIFTS ───
        # Groundcover and low flowers in sweeping drifts near camera
        fg_plant = self.pick("groundcover", ["flowers"])
        drift_positions = random.sample([15, 30, 50, 70, 85], 3)
        for dx in drift_positions:
            if len(self.result) >= self.target - 2:
                break
            self._drift(fg_plant, dx, random.uniform(85, 91),
                        count=random.choice([3, 5]),
                        spread_x=6, spread_y=1.5, scale_range=(0.6, 0.9))

        # ─── 5. SIDE BORDER SOFTENING ───
        # Plants along left and right fences
        side_plant = self.pick("shrubs", ["hedges", "ornamental"])
        # Left edge
        for ey in [65, 73, 81]:
            if len(self.result) >= self.target:
                break
            self.place(side_plant.id,
                       4 + random.uniform(0, 3), ey + random.uniform(-1.5, 1.5),
                       random.uniform(0.65, 0.9), self._rrot(), False)
        # Right edge
        for ey in [64, 72, 80]:
            if len(self.result) >= self.target:
                break
            self.place(side_plant.id,
                       95 + random.uniform(-3, 0), ey + random.uniform(-1.5, 1.5),
                       random.uniform(0.65, 0.9), self._rrot(), True)

        # ─── 6. RHYTHM REPETITION ───
        # Repeat one flower species across different beds for visual rhythm
        if len(self.result) < self.target:
            rhythm_plant = self.pick("flowers", ["ornamental"])
            rhythm_xs = [18, 48, 78]
            for rx in rhythm_xs:
                if len(self.result) >= self.target:
                    break
                self.place(rhythm_plant.id,
                           rx + random.uniform(-3, 3),
                           random.uniform(75, 83),
                           random.uniform(0.65, 0.85), self._rrot(), self._rflip())

        # ─── 7. FILL REMAINING ───
        attempts = 0
        while len(self.result) < self.target and attempts < 50:
            attempts += 1
            p = random.choice(self.plants)
            x = random.uniform(8, 92)
            y = random.uniform(self.ZONE_MID[0], self.ZONE_FRONT[1] - 2)
            # Protect center lawn openness
            if 32 < x < 68 and 71 < y < 82 and random.random() < 0.55:
                continue
            self.place(p.id, x, y,
                       random.uniform(0.6, 0.9), self._rrot(), self._rflip())

        return self.result[:self.target]


def landscape_design(plants, style="natural", density="medium",
                      photo_analysis=None) -> list[PlacedPlant]:
    """Public API for landscape design."""
    if not plants:
        return []
    designer = GardenDesigner(plants, style, density, photo_analysis)
    return designer.design()


# ════════════════════════════════════════════════════
#  2. PIL COMPOSITING ENGINE
# ════════════════════════════════════════════════════

def create_ground_shadow(w: int, h: int, scale: float, depth_t: float) -> Image.Image:
    """Realistic elliptical ground shadow at plant base."""
    sw = int(w * 0.8)
    sh = max(10, int(20 * scale))
    shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    # Multi-layer ellipse for soft falloff
    for i in range(sh):
        t = i / max(1, sh - 1)
        # Center rows are darkest
        dist_from_center = abs(t - 0.4) / 0.6
        alpha = int((0.3 + depth_t * 0.15) * 255 * max(0, 1 - dist_from_center ** 1.5))
        draw.line([(int(sw * 0.1), i), (int(sw * 0.9), i)], fill=(10, 8, 5, alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=int(4 * scale) + 2))
    return shadow


def color_grade(img: Image.Image, depth_t: float,
                scene_brightness: float = 0.5,
                ground_color: tuple = (100, 120, 80)) -> Image.Image:
    """Match plant to scene lighting with atmospheric perspective + color sampling."""
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))

    # NEW: scene-aware brightness
    brightness = 0.78 + scene_brightness * 0.18 + depth_t * 0.08
    saturation = 0.82 + depth_t * 0.13
    rgb = ImageEnhance.Brightness(rgb).enhance(brightness)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
    rgb = ImageEnhance.Color(rgb).enhance(saturation)

    # NEW: tint toward ground color (3%) for scene cohesion
    gr, gg, gb = ground_color
    blend = 0.03
    r2, g2, b2 = rgb.split()
    r2 = r2.point(lambda x: int(x * (1 - blend) + gr * blend + 1))
    g2 = g2.point(lambda x: int(x * (1 - blend) + gg * blend))
    b2 = b2.point(lambda x: max(0, int(x * (1 - blend) + gb * blend - 1)))
    rgb = Image.merge("RGB", (r2, g2, b2))

    return Image.merge("RGBA", (*rgb.split(), a))


def add_soil_gradient(img: Image.Image) -> Image.Image:
    """Dark gradient at plant base — looks rooted, not floating."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    start = int(h * 0.83)
    for y in range(start, h):
        t = ((y - start) / max(1, h - start)) ** 1.5
        draw.line([(0, y), (w, y)], fill=(18, 14, 8, int(70 * t)))
    return Image.alpha_composite(img, overlay)


def composite_garden(
    garden_path: str,
    placements: list[dict],
    plants_dir: Path = PLANTS_DIR,
) -> Optional[bytes]:
    """Composite all plant cutouts onto the garden photo."""
    garden = Image.open(garden_path).convert("RGBA")
    gw, gh = garden.size

    # NEW: analyze photo for smart color matching
    analysis = analyze_photo(garden.convert("RGB"))
    scene_brightness = analysis.get("brightness", 0.5)
    ground_color = analysis.get("ground_color", (100, 120, 80))

    # Sort by y (back-to-front rendering order)
    sorted_pl = sorted(placements, key=lambda p: p["y_pct"])

    for pl in sorted_pl:
        plant_path = plants_dir / pl["filename"]
        if not plant_path.exists():
            continue

        try:
            plant_img = Image.open(plant_path).convert("RGBA")
            y_pct = pl["y_pct"]
            depth_t = max(0, min(1, (y_pct - 50) / 50))
            depth_scale = 0.45 + depth_t * 0.55
            user_scale = pl.get("scale", 1.0)
            final_scale = depth_scale * user_scale

            # Size: ~10% of image width at scale 1.0
            target_w = int(gw * 0.10 * final_scale)
            ow, oh = plant_img.size
            ratio = target_w / max(1, ow)
            target_h = int(oh * ratio)
            target_w = max(50, min(int(gw * 0.30), target_w))
            target_h = max(50, min(int(gh * 0.50), target_h))

            plant_img = plant_img.resize((target_w, target_h), Image.LANCZOS)

            if pl.get("flip_h"):
                plant_img = plant_img.transpose(Image.FLIP_LEFT_RIGHT)
            rot = pl.get("rotation", 0)
            if abs(rot) > 0.5:
                plant_img = plant_img.rotate(-rot, resample=Image.BICUBIC, expand=True)

            # NEW: feather edges to remove hard sticker borders
            plant_img = feather_edges(plant_img, radius=2)

            # Color grade with scene-aware brightness
            plant_img = color_grade(plant_img, depth_t,
                                     scene_brightness=scene_brightness,
                                     ground_color=ground_color)
            plant_img = add_soil_gradient(plant_img)

            # Ground shadow
            shadow = create_ground_shadow(target_w, target_h, final_scale, depth_t)

            # Position
            base_x = int((pl["x_pct"] / 100) * gw)
            base_y = int((y_pct / 100) * gh)
            pw, ph = plant_img.size
            paste_x = base_x - pw // 2
            paste_y = base_y - ph

            # Paste shadow
            sw, sh = shadow.size
            sx = base_x - sw // 2
            sy = base_y - int(sh * 0.3)
            if 0 <= sx < gw and 0 <= sy < gh:
                layer = Image.new("RGBA", garden.size, (0, 0, 0, 0))
                layer.paste(shadow, (sx, sy))
                garden = Image.alpha_composite(garden, layer)

            # Paste plant
            layer = Image.new("RGBA", garden.size, (0, 0, 0, 0))
            layer.paste(plant_img, (paste_x, paste_y))
            garden = Image.alpha_composite(garden, layer)

        except Exception as e:
            print(f"[Composite] Error: {pl['filename']}: {e}")

    result = garden.convert("RGB")
    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=93)
    return buf.getvalue()


# ════════════════════════════════════════════════════
#  3. HUGGINGFACE HARMONIZATION via Spaces + InferenceClient
# ════════════════════════════════════════════════════
# Uses REAL img2img: sends our composite → gets back blended version.
# Two approaches that actually work on free tier:
#   A) huggingface_hub InferenceClient (routes through providers)
#   B) gradio_client calling HF Spaces directly

import tempfile

async def harmonize_with_hf(composite_bytes: bytes) -> Optional[bytes]:
    """
    Send composited image through HF img2img to harmonize lighting,
    smooth edges, and blend plants into the scene.
    """
    if not HF_TOKEN:
        print("[HF Harmonize] No HF_TOKEN set")
        return None

    result = None

    # ── METHOD A: huggingface_hub InferenceClient ──
    # Routes through multiple providers (fal, replicate, together etc.)
    result = await _try_inference_client(composite_bytes)
    if result:
        return result

    # ── METHOD B: gradio_client calling HF Spaces ──
    result = await _try_gradio_spaces(composite_bytes)
    if result:
        return result

    print("[HF Harmonize] All methods failed")
    return None


async def _try_inference_client(composite_bytes: bytes) -> Optional[bytes]:
    """Use huggingface_hub InferenceClient for img2img."""
    try:
        from huggingface_hub import InferenceClient
        import asyncio

        print("[HF Harmonize] Trying InferenceClient img2img...")

        # Save composite to temp file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(composite_bytes)
            temp_path = f.name

        prompt = (
            "A photorealistic garden photograph with plants naturally blended into the scene. "
            "Natural outdoor lighting, realistic shadows on grass, harmonized colors. "
            "Keep the exact same layout and plant positions."
        )
        negative = "stickers, floating, artificial, cartoon, blurry, distorted"

        # Models to try with img2img
        models = [
            "black-forest-labs/FLUX.1-dev",
            "stabilityai/stable-diffusion-3.5-large",
            "black-forest-labs/FLUX.1-schnell",
        ]

        for model in models:
            try:
                print(f"[HF Harmonize] InferenceClient → {model}...")
                client = InferenceClient(token=HF_TOKEN)

                # Run in thread to not block async
                def do_img2img():
                    return client.image_to_image(
                        image=temp_path,
                        prompt=prompt,
                        model=model,
                        strength=0.25,  # Low strength = keep layout, just harmonize
                        guidance_scale=5.0,
                        num_inference_steps=15,
                    )

                result_img = await asyncio.get_event_loop().run_in_executor(None, do_img2img)

                if result_img:
                    # result_img is a PIL Image
                    buf = io.BytesIO()
                    result_img.save(buf, format="JPEG", quality=93)
                    print(f"[HF Harmonize] InferenceClient success with {model}!")

                    # Blend: 70% harmonized + 30% original composite to preserve plant details
                    harmonized = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
                    original = Image.open(io.BytesIO(composite_bytes)).convert("RGB")
                    harmonized = harmonized.resize(original.size, Image.LANCZOS)
                    blended = Image.blend(original, harmonized, 0.65)

                    out = io.BytesIO()
                    blended.save(out, format="JPEG", quality=93)
                    return out.getvalue()

            except Exception as e:
                err_str = str(e)
                # Skip known failures silently
                if "404" in err_str or "not found" in err_str.lower():
                    print(f"[HF Harmonize] {model} not available for img2img")
                elif "503" in err_str:
                    print(f"[HF Harmonize] {model} is loading, skipping")
                else:
                    print(f"[HF Harmonize] {model} error: {err_str[:200]}")

        # Clean up
        try:
            os.unlink(temp_path)
        except:
            pass

    except ImportError:
        print("[HF Harmonize] huggingface_hub not installed, skipping InferenceClient")
    except Exception as e:
        print(f"[HF Harmonize] InferenceClient error: {e}")

    return None


async def _try_gradio_spaces(composite_bytes: bytes) -> Optional[bytes]:
    """Use gradio_client to call HF Spaces with img2img."""
    try:
        from gradio_client import Client as GradioClient, handle_file
        import asyncio

        print("[HF Harmonize] Trying Gradio Spaces...")

        # Save to temp file (gradio_client needs file paths)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(composite_bytes)
            temp_path = f.name

        # Spaces that support img2img editing
        spaces = [
            {
                "name": "multimodalart/cosxl",
                "fn": lambda client, path: client.predict(
                    image=handle_file(path),
                    prompt="Harmonize this garden photograph. Blend plants naturally into the scene with realistic lighting and shadows. Keep the same layout.",
                    negative_prompt="stickers, floating, artificial, cartoon",
                    guidance_scale=7.0,
                    strength=0.3,
                    api_name="/run",
                ),
            },
            {
                "name": "diffusers/img2img",
                "fn": lambda client, path: client.predict(
                    image=handle_file(path),
                    prompt="Photorealistic garden with naturally blended plants, outdoor lighting, realistic shadows on grass",
                    strength=0.25,
                    api_name="/predict",
                ),
            },
        ]

        for space in spaces:
            try:
                print(f"[HF Harmonize] Trying Space: {space['name']}...")

                def call_space():
                    gc = GradioClient(space["name"], hf_token=HF_TOKEN)
                    return space["fn"](gc, temp_path)

                result = await asyncio.get_event_loop().run_in_executor(None, call_space)

                if result:
                    # Result could be a file path or image
                    if isinstance(result, str) and os.path.exists(result):
                        with open(result, "rb") as f:
                            harmonized_bytes = f.read()
                    elif isinstance(result, tuple) and len(result) > 0:
                        # Some spaces return tuples
                        r = result[0]
                        if isinstance(r, str) and os.path.exists(r):
                            with open(r, "rb") as f:
                                harmonized_bytes = f.read()
                        else:
                            continue
                    else:
                        continue

                    # Blend harmonized with original to preserve plant details
                    harmonized = Image.open(io.BytesIO(harmonized_bytes)).convert("RGB")
                    original = Image.open(io.BytesIO(composite_bytes)).convert("RGB")
                    harmonized = harmonized.resize(original.size, Image.LANCZOS)
                    blended = Image.blend(original, harmonized, 0.6)

                    buf = io.BytesIO()
                    blended.save(buf, format="JPEG", quality=93)
                    print(f"[HF Harmonize] Space {space['name']} success!")
                    return buf.getvalue()

            except Exception as e:
                print(f"[HF Harmonize] Space {space['name']} error: {str(e)[:200]}")

        # Clean up
        try:
            os.unlink(temp_path)
        except:
            pass

    except ImportError:
        print("[HF Harmonize] gradio_client not installed. Run: pip install gradio_client")
    except Exception as e:
        print(f"[HF Harmonize] Gradio error: {e}")

    return None


# ════════════════════════════════════════════════════
#  PUBLIC API: Full pipeline
# ════════════════════════════════════════════════════

async def generate_garden_image_hf(
    garden_image_path: str,
    style: str = "natural",
    density: str = "medium",
    plant_names: list[str] = [],
    strength: float = 0.55,
) -> Optional[bytes]:
    """
    Full pipeline:
    1. Design → 2. Composite → 3. Harmonize
    Returns JPEG bytes.
    """
    # This function is kept for backward compat but the main
    # endpoint now calls composite_garden directly.
    # If called, just return None to trigger the cutout fallback.
    return None
