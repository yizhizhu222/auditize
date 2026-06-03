#!/usr/bin/env bash
# Production deployment setup script for Nexus AI Platform
set -e

echo "=== Nexus AI Platform — Production Deployment ==="

# ── 1. Build frontend ──────────────────────────────────────────────────────────
echo "[1/6] Building frontend..."
cd "$(dirname "$0")/../Nexus AI"
npm ci
npm run build
echo "  → dist/ ready"

# ── 2. Install backend deps ───────────────────────────────────────────────────
echo "[2/6] Installing backend dependencies..."
cd ../platform-backend
pip install -r requirements.txt --no-cache-dir

# ── 3. Build C++ engine ───────────────────────────────────────────────────────
echo "[3/6] Building C++ engine..."
cd core
mkdir -p build && cd build
cmake .. && cmake --build .
echo "  → engine_core_exe built"

# ── 4. Seed admin user if not exists ──────────────────────────────────────────
echo "[4/6] Seeding default user..."
cd ../..
python scripts/seed_users.py --username admin --email admin@nexus.local 2>/dev/null || true

# ── 5. Configure Nginx ────────────────────────────────────────────────────────
echo "[5/6] Deploying Nginx config..."
if command -v nginx &>/dev/null; then
    sudo cp ../deploy/nginx.conf /etc/nginx/sites-available/nexus
    sudo ln -sf /etc/nginx/sites-available/nexus /etc/nginx/sites-enabled/ 2>/dev/null || true
    sudo nginx -t && sudo systemctl reload nginx
    echo "  → Nginx configured"
else
    echo "  ⚠ Nginx not found, skipping"
fi

# ── 6. Print summary ──────────────────────────────────────────────────────────
echo "[6/6] Done!"
echo ""
echo "  Start backend:  cd platform-backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "  Serve frontend: nginx (serve /Nexus AI/dist)"
echo "  WebSocket:      built into backend at /ws/{session_id}"
echo "  API docs:       http://localhost:8000/docs"
echo "  Login bypass:   000000 (when DEBUG=true)"
echo ""