# 🌿 Paysagea — AI-Powered Garden Designer

A full-stack garden design application built with **React** + **FastAPI** for Paysagea's AI Clinic project at Aivancity.

Users upload a garden photo, then either **manually drag & drop** plant cutouts or use **AI auto-design** to generate a beautiful, realistic garden layout.

---

## Architecture

```
paysagea/
├── backend/                 # FastAPI server
│   ├── main.py              # API routes (plants, upload, generate, export)
│   ├── models.py            # Pydantic schemas
│   ├── ai_engine.py         # Claude Vision AI + algorithmic fallback
│   └── requirements.txt
├── frontend/                # React + Vite
│   ├── src/
│   │   ├── components/      # Navbar, PlantSidebar, DesignCanvas, PropertyPanel, StyleModal
│   │   ├── pages/           # AuthPage, DesignerPage
│   │   ├── utils/           # api.js, store.js (Zustand)
│   │   └── index.css        # Premium botanical theme
│   └── vite.config.js       # Dev proxy to backend
├── plants_dataset/          # Your 2000+ plant cutout PNGs (add here)
├── docker-compose.yml
├── run.sh                   # One-command local dev
└── .env.example
```

## Features

| Feature | Description |
|---------|-------------|
| **Auth** | Sign in / sign up (simplified for demo) |
| **Plant Catalog** | Auto-scans `plants_dataset/` folder, classifies by filename |
| **Drag & Drop** | Drag plants from sidebar onto garden photo |
| **Depth Perspective** | Plants auto-scale by vertical position (higher = smaller = farther) |
| **Realistic Shadows** | CSS `drop-shadow` scales with depth |
| **AI Auto-Design** | Claude Vision analyzes the photo and places 8-25 plants in natural clusters |
| **Style Presets** | Natural, Formal, Cottage, Modern, Tropical, Mediterranean |
| **Density Control** | Sparse / Medium / Dense plant count |
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

```bash
cp .env.example .env
# Edit .env with your keys:
# ANTHROPIC_API_KEY=sk-ant-... (required for AI auto-design)
# HF_TOKEN=hf_...             (optional, for future features)
```

### 3. Run locally

```bash
chmod +x run.sh
./run.sh
```

Or manually:

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
PLANTS_DIR=../plants_dataset uvicorn main:app --reload --port 8000

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
| `GET` | `/api/plants` | List plants (filter by `?category=` `?search=`) |
| `GET` | `/api/plants/{id}` | Get single plant |
| `POST` | `/api/plants/reload` | Re-scan plants folder |
| `POST` | `/api/garden/upload` | Upload garden photo |
| `POST` | `/api/garden/generate` | AI auto-design |
| `POST` | `/api/garden/export` | Export plant list (CSV) |
| `GET` | `/api/health` | Health check |

Interactive docs at **http://localhost:8000/docs**

## How AI Placement Works

1. **Claude Vision** analyzes the uploaded garden photo
2. It identifies zones: sky, ground, structures, planting beds
3. Plants are placed following landscape architecture rules:
   - Trees in background (y: 12-35%)
   - Shrubs in midground (y: 30-60%)
   - Flowers/ornamentals in foreground (y: 45-80%)
   - Groundcover at the front (y: 65-88%)
4. Plants are grouped in **natural clusters** (3-5 groups of 2-5 plants)
5. Each plant gets depth-based scaling, shadows, slight rotation for realism
6. If Claude API is unavailable, an **algorithmic fallback** generates the layout

## Tech Stack

- **Frontend**: React 18, Vite, Zustand, Lucide Icons, Framer Motion
- **Backend**: FastAPI, Pillow, Anthropic SDK
- **AI**: Claude Sonnet (Vision) for photo analysis + intelligent placement
- **Theme**: Custom botanical premium theme (Cormorant Garamond + DM Sans)

## Extending

- **Add more plants**: Drop PNGs into `plants_dataset/` and call `POST /api/plants/reload`
- **Better classification**: Edit `CATEGORY_KEYWORDS` in `main.py`
- **Custom metadata**: Create a `plants_metadata.json` to override auto-detected names/categories
- **HuggingFace integration**: Extend `ai_engine.py` to use Stable Diffusion for inpainting

---

Built for the Paysagea AI Clinic project · Aivancity PGE2
