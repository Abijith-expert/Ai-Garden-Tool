# 🌿 Paysagea — AI-Powered Garden Designer

A full-stack garden design application built with **React** + **FastAPI** .

Users upload a garden photo, then either **manually drag & drop** plant cutouts or use **AI auto-design** to generate a beautiful, realistic garden layout using their actual plant dataset of 2800+ cutout images.

---

## Architecture

```
paysagea/
├── backend/                 # FastAPI server
│   ├── main.py              # API routes (plants, upload, generate, export)
│   ├── models.py            # Pydantic schemas
│   ├── ai_engine.py         # Landscape design algorithm + PIL compositing + HF harmonization
│   └── requirements.txt
├── frontend/                # React + Vite
│   ├── src/
│   │   ├── components/      # Navbar, PlantSidebar, DesignCanvas, PropertyPanel, StyleModal
│   │   ├── pages/           # AuthPage, DesignerPage
│   │   ├── utils/           # api.js, store.js (Zustand)
│   │   └── index.css        # Premium botanical theme
│   └── vite.config.js       # Dev proxy to backend
├── plants_dataset/          # 2800+ plant cutout PNGs
├── docker-compose.yml
├── run.sh                   # One-command local dev
└── .env.example
```

## AI Pipeline

The garden design uses a **4-step pipeline** combining algorithmic landscape design, server-side image compositing, and HuggingFace AI harmonization:

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: PHOTO ANALYSIS (PIL ImageStat)                     │
│  - Detects where ground/grass starts in the photo           │
│  - Measures scene brightness for color matching             │
│  - Samples ground color for plant tinting                   │
│  - Identifies obstacle zones (chairs, paths, structures)    │
├─────────────────────────────────────────────────────────────┤
│  Step 2: LANDSCAPE DESIGN ALGORITHM (Python)                │
│  - Thriller-Filler-Spiller planting beds                    │
│  - Drift planting (odd numbers: 3, 5, 7 of same species)   │
│  - Back border → Mid beds → Foreground zones                │
│  - Focal specimen trees at golden ratio positions           │
│  - Obstacle avoidance, variety control (max 5/species)      │
│  - Filters out empty pots/containers automatically          │
├─────────────────────────────────────────────────────────────┤
│  Step 3: PIL COMPOSITING (Pillow)                           │
│  - Opens actual plant cutout PNGs from the dataset          │
│  - Depth-based scaling (back = smaller, front = larger)     │
│  - Feathered edges (alpha erosion + blur, anti-sticker)     │
│  - Scene-aware color grading (brightness, saturation, tint) │
│  - Dark base gradient (rooted-in-soil effect)               │
│  - Elliptical ground contact shadows with blur              │
│  - Back-to-front render order for correct layering          │
├─────────────────────────────────────────────────────────────┤
│  Step 4: HUGGINGFACE HARMONIZATION (FLUX.1-Kontext-Dev)     │
│  - Sends composite to HF Spaces for img2img editing         │
│  - Blends lighting, smooths edges, harmonizes colors        │
│  - Uses FLUX.1-Kontext-Dev (image editing with text prompt) │
│  - Fallback: Photo-Mate-i2i for photo enhancement           │
│  - Result blended 65/35 with original to preserve layout    │
│  - If HF unavailable, raw composite is still returned       │
└─────────────────────────────────────────────────────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| **Auth** | Sign in / sign up (simplified for demo) |
| **Plant Catalog** | Auto-scans `plants_dataset/` folder (2800+ plants), classifies by filename |
| **Drag & Drop** | Drag plants from sidebar onto garden photo |
| **Depth Perspective** | Plants auto-scale by vertical position (higher = smaller = farther) |
| **AI Auto-Design** | Algorithmic landscape design with PIL compositing + HuggingFace harmonization |
| **Two Modes** | **Rendered Image** (server-side composite) or **Interactive Cutouts** (editable CSS placement) |
| **Style Presets** | Natural, Formal, Cottage, Modern, Tropical, Mediterranean |
| **Density Control** | Sparse / Medium / Dense plant count |
| **Smart Photo Analysis** | Auto-detects ground level, obstacles, scene lighting |
| **Anti-Sticker Pipeline** | Feathered edges, color grading, soil gradients, ground shadows |
| **Pot/Container Filtering** | Auto-excludes empty pots, planters, decorations from design |
| **Property Editor** | Scale, rotate, flip selected plants |
| **Export** | Download CSV plant list with quantities and care info |

## Quick Start

### 1. Add your plant images

Copy all your cutout PNG/JPG/WEBP images into `plants_dataset/`:

```bash
cp /path/to/your/cutouts/*.png plants_dataset/
```

The backend auto-classifies plants from filenames. For best results, name files descriptively:
- `alstroemeria_aurantiaca.png` → Flowers
- `buxus_sempervirens.png` → Shrubs
- `acer_palmatum_tree.png` → Trees
- `thymus_ground_cover.png` → Groundcover

### 2. Set environment variables

Create `backend/.env`:
```
HF_TOKEN=hf_...              # HuggingFace token (for AI harmonization)
PLANTS_DIR=C:\path\to\plants_dataset
```

Get your HuggingFace token at https://huggingface.co/settings/tokens (free, Read access).

### 3. Run locally

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

### 4. Or use Docker

```bash
docker-compose up --build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login |
| `POST` | `/api/auth/signup` | Register |
| `GET` | `/api/plants` | List plants (paginated, filter by `?category=` `?search=`) |
| `GET` | `/api/plants/{id}` | Get single plant |
| `POST` | `/api/plants/reload` | Re-scan plants folder |
| `POST` | `/api/garden/upload` | Upload garden photo |
| `POST` | `/api/garden/generate` | AI auto-design (cutout positions) |
| `POST` | `/api/garden/generate-image` | AI rendered image (PIL composite + HF harmonization) |
| `POST` | `/api/garden/export` | Export plant list (CSV) |
| `GET` | `/api/health` | Health check |

Interactive docs at **http://localhost:8000/docs**

## Landscape Design Principles

The algorithm follows real landscape architecture rules:

- **Thriller-Filler-Spiller**: Every planting bed has a tall focal shrub (thriller), mid-height flowers around it (filler), and low groundcover at the front edge (spiller)
- **Drift Planting**: Same species planted in elongated groups of 3, 5, or 7 (always odd numbers, as real gardeners do)
- **Layered Heights**: Back-to-front height gradient — trees and tall shrubs in back, flowers in mid, groundcover in front
- **Focal Points**: 1-2 specimen trees placed at golden ratio positions (~30% and ~70% of width)
- **Rhythm & Repetition**: One flower species echoed across multiple beds for visual unity
- **Negative Space**: Center lawn 30-40% kept open for balance
- **Edge Softening**: Shrubs along walls and fences to soften hard lines
- **Variety Control**: Maximum 5 of any single species to ensure diversity
- **Obstacle Avoidance**: Detects chairs, paths, structures and avoids placing plants on them

## Tech Stack

- **Frontend**: React 18, Vite, Zustand, Lucide Icons, DM Sans + Cormorant Garamond
- **Backend**: FastAPI, Pillow, NumPy, python-dotenv
- **AI/ML**: HuggingFace Spaces (FLUX.1-Kontext-Dev for image harmonization, Photo-Mate-i2i fallback)
- **Libraries**: huggingface_hub, gradio_client, httpx
- **Design**: PIL-based server-side compositing with depth scaling, color grading, shadow generation

## Extending

- **Add more plants**: Drop PNGs into `plants_dataset/` and call `POST /api/plants/reload`
- **Better classification**: Edit `CATEGORY_KEYWORDS` dict in `main.py`
- **Custom metadata**: Create a `plants_metadata.json` to override auto-detected names/categories
- **New styles**: Add style configs in `GardenDesigner._bed()` and cluster definitions in `design()`
- **Improve harmonization**: Add new HuggingFace Spaces to `_try_gradio_spaces()` in `ai_engine.py`

--

