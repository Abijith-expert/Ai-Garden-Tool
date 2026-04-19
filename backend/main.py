"""
Paysagea Garden Designer — FastAPI Backend
"""
from dotenv import load_dotenv
load_dotenv()
import os
import re
import uuid
import json
import csv
import io
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from PIL import Image

from models import (
    PlantInfo, PlantCategory, PlacedPlant,
    GenerateRequest, GenerateResponse,
    UserLogin, UserResponse, ExportRequest,
)
from ai_engine import landscape_design

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
PLANTS_DIR = Path(os.getenv("PLANTS_DIR", BASE_DIR / "plants_dataset"))
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Paysagea Garden Designer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploads as static
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# ──────────────────────────────────────────────
# Serve plant images with cache headers
# (Don't use StaticFiles for 2000+ files — use a direct route with caching)
# ──────────────────────────────────────────────

@app.get("/static/plants/{filename}")
async def serve_plant_image(filename: str):
    filepath = PLANTS_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(
        filepath,
        headers={
            "Cache-Control": "public, max-age=86400, immutable",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ──────────────────────────────────────────────
# Plant catalog
# ──────────────────────────────────────────────

PLANT_CATALOG: list[PlantInfo] = []

CATEGORY_KEYWORDS = {
    "tree": PlantCategory.trees,
    "arbre": PlantCategory.trees,
    "palm": PlantCategory.trees,
    "pine": PlantCategory.trees,
    "oak": PlantCategory.trees,
    "maple": PlantCategory.trees,
    "cedar": PlantCategory.trees,
    "acer": PlantCategory.trees,
    "betula": PlantCategory.trees,
    "prunus": PlantCategory.trees,
    "shrub": PlantCategory.shrubs,
    "bush": PlantCategory.shrubs,
    "arbuste": PlantCategory.shrubs,
    "buxus": PlantCategory.shrubs,
    "boxwood": PlantCategory.shrubs,
    "hydrangea": PlantCategory.shrubs,
    "azalea": PlantCategory.shrubs,
    "rhododendron": PlantCategory.shrubs,
    "abelia": PlantCategory.shrubs,
    "viburnum": PlantCategory.shrubs,
    "hedge": PlantCategory.hedges,
    "haie": PlantCategory.hedges,
    "grass": PlantCategory.ornamental,
    "bamboo": PlantCategory.ornamental,
    "fougere": PlantCategory.ornamental,
    "miscanthus": PlantCategory.ornamental,
    "ground": PlantCategory.groundcover,
    "cover": PlantCategory.groundcover,
    "thyme": PlantCategory.groundcover,
    "moss": PlantCategory.groundcover,
    "ivy": PlantCategory.climbers,
    "climber": PlantCategory.climbers,
    "jasmine": PlantCategory.climbers,
    "wisteria": PlantCategory.climbers,
    "pot": PlantCategory.potted,
    "container": PlantCategory.potted,
    "planter": PlantCategory.potted,
    "composition": PlantCategory.potted,
}

HEIGHT_ESTIMATES = {
    PlantCategory.trees: 300,
    PlantCategory.hedges: 150,
    PlantCategory.shrubs: 120,
    PlantCategory.climbers: 200,
    PlantCategory.ornamental: 100,
    PlantCategory.flowers: 60,
    PlantCategory.potted: 50,
    PlantCategory.groundcover: 15,
}

SPREAD_ESTIMATES = {
    PlantCategory.trees: 250,
    PlantCategory.hedges: 80,
    PlantCategory.shrubs: 100,
    PlantCategory.climbers: 60,
    PlantCategory.ornamental: 70,
    PlantCategory.flowers: 40,
    PlantCategory.potted: 35,
    PlantCategory.groundcover: 50,
}


def classify_plant_from_filename(filename: str) -> PlantCategory:
    name_lower = filename.lower()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in name_lower:
            return category
    return PlantCategory.flowers


def humanize_name(filename: str) -> str:
    name = Path(filename).stem
    name = re.sub(r'^(plant_?\d*_?\d*_?)', '', name, flags=re.IGNORECASE)
    name = name.strip('_- ')
    name = re.sub(r'[_\-]+', ' ', name)
    name = name.title()
    return name if name else Path(filename).stem.replace('_', ' ').title()


def scan_plant_catalog():
    global PLANT_CATALOG
    PLANT_CATALOG = []

    if not PLANTS_DIR.exists():
        print(f"[Catalog] Plants directory not found: {PLANTS_DIR}")
        return

    valid_ext = {'.png', '.jpg', '.jpeg', '.webp'}
    files = sorted([
        f for f in PLANTS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in valid_ext
    ])

    for i, filepath in enumerate(files):
        filename = filepath.name
        category = classify_plant_from_filename(filename)
        name = humanize_name(filename)
        plant = PlantInfo(
            id=f"plant_{i:04d}",
            filename=filename,
            name=name,
            category=category,
            height_cm=HEIGHT_ESTIMATES.get(category, 60),
            spread_cm=SPREAD_ESTIMATES.get(category, 40),
            sun="Full Sun",
            water="Moderate",
            image_url=f"/static/plants/{filename}",
        )
        PLANT_CATALOG.append(plant)

    print(f"[Catalog] Loaded {len(PLANT_CATALOG)} plants from {PLANTS_DIR}")


@app.on_event("startup")
async def startup():
    scan_plant_catalog()


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────

@app.post("/api/auth/login", response_model=UserResponse)
async def login(data: UserLogin):
    return UserResponse(email=data.email, token=str(uuid.uuid4()))

@app.post("/api/auth/signup", response_model=UserResponse)
async def signup(data: UserLogin):
    return UserResponse(email=data.email, token=str(uuid.uuid4()))


# ──────────────────────────────────────────────
# Plants API — WITH PAGINATION
# ──────────────────────────────────────────────

@app.get("/api/plants")
async def get_plants(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(40, ge=1, le=100),
):
    """Returns paginated plants. Default 40 per page."""
    result = PLANT_CATALOG

    if category and category != "all":
        result = [p for p in result if p.category == category]
    if search:
        q = search.lower()
        result = [p for p in result if q in p.name.lower()]

    total = len(result)
    start = (page - 1) * limit
    end = start + limit
    page_items = result[start:end]

    return {
        "plants": [p.model_dump() for p in page_items],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@app.get("/api/plants/{plant_id}", response_model=PlantInfo)
async def get_plant(plant_id: str):
    for p in PLANT_CATALOG:
        if p.id == plant_id:
            return p
    raise HTTPException(404, "Plant not found")


@app.post("/api/plants/reload")
async def reload_plants():
    scan_plant_catalog()
    return {"count": len(PLANT_CATALOG)}


# ──────────────────────────────────────────────
# Garden Upload
# ──────────────────────────────────────────────

@app.post("/api/garden/upload")
async def upload_garden_image(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in {'.jpg', '.jpeg', '.png', '.webp'}:
        raise HTTPException(400, "Only JPG, PNG, WEBP supported")

    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    filepath = UPLOADS_DIR / filename

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    img = Image.open(filepath)
    w, h = img.size

    return {"id": file_id, "filename": filename, "url": f"/static/uploads/{filename}", "width": w, "height": h}


# ──────────────────────────────────────────────
# AI Generation
# ──────────────────────────────────────────────

@app.post("/api/garden/generate", response_model=GenerateResponse)
async def generate_design(req: GenerateRequest):
    """Cutout placement mode — returns positions for PNG cutouts."""
    garden_file = None
    for f in UPLOADS_DIR.iterdir():
        if f.stem == req.garden_image_id:
            garden_file = f
            break

    if not garden_file:
        raise HTTPException(404, "Garden image not found")

    plants = [p for p in PLANT_CATALOG if p.id in req.plant_ids] if req.plant_ids else PLANT_CATALOG
    if not plants:
        raise HTTPException(400, "No plants available")

    placements = landscape_design(plants, req.style, req.density)
    return GenerateResponse(
        placements=placements,
        description=f"Generated {len(placements)} plants in {req.style} style",
    )


@app.post("/api/garden/generate-image")
async def generate_garden_image(req: GenerateRequest):
    """
    Full pipeline:
    1. Landscape algorithm designs plant placement
    2. PIL composites actual plant cutout PNGs onto the photo
    3. HuggingFace harmonizes the result (lighting, blending)
    """
    garden_file = None
    for f in UPLOADS_DIR.iterdir():
        if f.stem == req.garden_image_id:
            garden_file = f
            break

    if not garden_file:
        raise HTTPException(404, "Garden image not found")

    plants_pool = [p for p in PLANT_CATALOG if p.id in req.plant_ids] if req.plant_ids else PLANT_CATALOG
    if not plants_pool:
        raise HTTPException(400, "No plants available")

    # Step 1: Landscape design algorithm
    print(f"[Pipeline] Step 1: Designing {req.style}/{req.density} garden...")
    placements = landscape_design(plants_pool, req.style, req.density)

    # Step 2: Build placement dicts with filenames
    placement_dicts = []
    for pl in placements:
        plant_info = next((p for p in PLANT_CATALOG if p.id == pl.plant_id), None)
        if plant_info:
            placement_dicts.append({
                "plant_id": pl.plant_id,
                "filename": plant_info.filename,
                "x_pct": pl.x_percent,
                "y_pct": pl.y_percent,
                "scale": pl.scale,
                "rotation": pl.rotation,
                "flip_h": pl.flip_h,
            })

    # Step 3: PIL composite
    print(f"[Pipeline] Step 2: Compositing {len(placement_dicts)} plants onto photo...")
    from ai_engine import composite_garden, harmonize_with_hf
    result_bytes = composite_garden(str(garden_file), placement_dicts, PLANTS_DIR)

    if result_bytes is None:
        raise HTTPException(500, "Compositing failed")

    # Step 4: HuggingFace harmonization (optional, improves realism)
    print("[Pipeline] Step 3: HuggingFace harmonization...")
    harmonized = await harmonize_with_hf(result_bytes)
    if harmonized:
        print("[Pipeline] Harmonization applied!")
        result_bytes = harmonized
    else:
        print("[Pipeline] Harmonization skipped (unavailable), using raw composite")

    # Save the final image
    gen_id = str(uuid.uuid4())
    gen_filename = f"rendered_{gen_id}.jpg"
    gen_path = UPLOADS_DIR / gen_filename

    with open(gen_path, "wb") as f:
        f.write(result_bytes)

    rendered = Image.open(gen_path)

    return {
        "id": gen_id,
        "url": f"/static/uploads/{gen_filename}",
        "width": rendered.size[0],
        "height": rendered.size[1],
        "style": req.style,
        "density": req.density,
        "plants_placed": len(placement_dicts),
    }


# ──────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────

@app.post("/api/garden/export")
async def export_plant_list(req: ExportRequest):
    counts: dict[str, int] = {}
    for pl in req.placements:
        counts[pl.plant_id] = counts.get(pl.plant_id, 0) + 1

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Plant Name", "Quantity", "Category", "Height (cm)", "Spread (cm)", "Sun", "Water"])
    for pid, qty in sorted(counts.items()):
        plant = next((p for p in PLANT_CATALOG if p.id == pid), None)
        if plant:
            writer.writerow([plant.name, qty, plant.category.value, plant.height_cm, plant.spread_cm, plant.sun, plant.water])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=paysagea-garden-plan.csv"})


@app.get("/api/health")
async def health():
    return {"status": "ok", "plants_loaded": len(PLANT_CATALOG)}
