#!/bin/bash
# ─── Paysagea Garden Designer — Local Dev ───
# Run both backend and frontend in parallel

set -e

# Load .env if present
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

echo "╔══════════════════════════════════════════╗"
echo "║   🌿 Paysagea Garden Designer            ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check plants
PLANT_COUNT=$(find "${PLANTS_DIR:-./plants_dataset}" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.webp" \) 2>/dev/null | wc -l)
echo "📦 Found $PLANT_COUNT plant images in ${PLANTS_DIR:-./plants_dataset}"
echo ""

# Install backend deps
echo "📌 Installing backend dependencies..."
cd backend
pip install -r requirements.txt -q
cd ..

# Install frontend deps
echo "📌 Installing frontend dependencies..."
cd frontend
npm install --silent
cd ..

echo ""
echo "🚀 Starting servers..."
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   API docs: http://localhost:8000/docs"
echo ""

# Run both
cd backend && PLANTS_DIR="${PLANTS_DIR:-../plants_dataset}" uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

cd ../frontend && npm run dev &
FRONTEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

wait
