#!/usr/bin/env bash
set -e

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ── Config ─────────────────────────────────────────────────────────────────────
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_DIR="$(dirname "$0")/platform-backend"
FRONTEND_DIR="$(dirname "$0")/Nexus AI"

# ── Checks ──────────────────────────────────────────────────────────────────────
if [ ! -d "$BACKEND_DIR/.venv" ] && [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
    echo -e "${RED}Error: platform-backend directory not found at $BACKEND_DIR${NC}"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not installed. Running npm install...${NC}"
    (cd "$FRONTEND_DIR" && npm install)
fi

# ── Ensure git user config ──────────────────────────────────────────────────────
if ! git config user.name >/dev/null 2>&1; then
    git config user.name "Nexus AI Developer"
    echo -e "${GREEN}[Git]${NC} Set default user.name"
fi
if ! git config user.email >/dev/null 2>&1; then
    git config user.email "dev@nexus.local"
    echo -e "${GREEN}[Git]${NC} Set default user.email"
fi

# ── Cleanup ─────────────────────────────────────────────────────────────────────
cleanup() {
    echo -e "\n${CYAN}Shutting down...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait 2>/dev/null
    echo -e "${GREEN}All services stopped.${NC}"
}
trap cleanup EXIT INT TERM

# ── Start backend ───────────────────────────────────────────────────────────────
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Starting Nexus AI Platform...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${GREEN}[Backend]${NC} Starting uvicorn on :${BACKEND_PORT}..."
cd "$BACKEND_DIR"
if [ -d ".venv" ]; then
    .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
else
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
fi
BACKEND_PID=$!

# ── Start frontend ──────────────────────────────────────────────────────────────
echo -e "${GREEN}[Frontend]${NC} Starting Vite dev server on :${FRONTEND_PORT}..."
cd "$FRONTEND_DIR"
npx vite --host 0.0.0.0 --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

# ── Print status ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}  Backend   :${NC} http://localhost:${BACKEND_PORT}"
echo -e "${CYAN}  API docs  :${NC} http://localhost:${BACKEND_PORT}/docs"
echo -e "${CYAN}  Frontend  :${NC} http://localhost:${FRONTEND_PORT}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}"
echo ""

wait