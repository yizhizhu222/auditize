#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/platform-backend"
FRONTEND_DIR="$SCRIPT_DIR/Nexus AI"
ENV_FILE="$SCRIPT_DIR/.env"
PORT=8001
ADMIN_PORT=8002
TUNNEL_LOG="/tmp/truffle-tunnel.log"

cleanup() {
    echo -e "\n${CYAN}Shutting down...${NC}"
    kill $BACKEND_PID $ADMIN_PID $TUNNEL_PID 2>/dev/null
    # Also kill leftover cloudflared in case PID tracking failed
    pkill -f "cloudflared tunnel.*$(grep TUNNEL_TOKEN "$ENV_FILE" 2>/dev/null | cut -d= -f2- | head -c 20)" 2>/dev/null || true
    wait 2>/dev/null
    echo -e "${GREEN}All services stopped.${NC}"
}
trap cleanup EXIT INT TERM

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🚀  Truffle — Starting...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ── Kill anything left on our ports ────────────────────────────
echo -e "${YELLOW}[Cleanup]${NC} Freeing ports $PORT, $ADMIN_PORT..."
fuser -k "${PORT}/tcp" 2>/dev/null || true
fuser -k "${ADMIN_PORT}/tcp" 2>/dev/null || true
# Kill any leftover cloudflared tunnel processes
pkill -f "cloudflared tunnel run" 2>/dev/null || true
sleep 1

# ── Build frontend if dist/ missing ─────────────────────────────
if [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
    echo -e "${YELLOW}[Frontend]${NC} dist/ not found, building..."
    cd "$FRONTEND_DIR"
    npm run build 2>/dev/null || npx vite build
    echo -e "${GREEN}[Frontend]${NC} Build complete"
fi

# ── Start backend ───────────────────────────────────────────────
echo -e "${GREEN}[Backend]${NC} Starting uvicorn on :$PORT..."
cd "$BACKEND_DIR"
if [ -d ".venv" ]; then
    .venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" > server.log 2>&1 &
else
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" > server.log 2>&1 &
fi
BACKEND_PID=$!

# Wait for backend to be ready
for i in $(seq 1 10); do
    if curl -s http://localhost:$PORT/api/v1/health >/dev/null 2>&1; then
        echo -e "${GREEN}[Backend]${NC} Ready on :$PORT"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}[Backend]${NC} Failed to start, check logs: $BACKEND_DIR/server.log"
        exit 1
    fi
    sleep 1
done

# ── Start admin server (127.0.0.1 only, not exposed to internet) ──
echo -e "${GREEN}[Admin]${NC} Starting admin server on 127.0.0.1:$ADMIN_PORT..."
cd "$BACKEND_DIR"
if [ -d ".venv" ]; then
    .venv/bin/python3 -m uvicorn app.admin_app:app --host 127.0.0.1 --port "$ADMIN_PORT" > admin_server.log 2>&1 &
else
    python3 -m uvicorn app.admin_app:app --host 127.0.0.1 --port "$ADMIN_PORT" > admin_server.log 2>&1 &
fi
ADMIN_PID=$!
sleep 2
if curl -s http://127.0.0.1:$ADMIN_PORT/docs >/dev/null 2>&1; then
    echo -e "${GREEN}[Admin]${NC} Ready on 127.0.0.1:$ADMIN_PORT"
else
    echo -e "${YELLOW}[Admin]${NC} Admin server might not be ready yet, check admin_server.log"
fi

# ── Start Cloudflare Tunnel ─────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    TUNNEL_TOKEN=$(grep TUNNEL_TOKEN "$ENV_FILE" | cut -d= -f2-)
    if [ -n "$TUNNEL_TOKEN" ]; then
        echo -e "${GREEN}[Tunnel]${NC} Connecting Cloudflare Tunnel..."
        > "$TUNNEL_LOG"
        cloudflared tunnel run --token "$TUNNEL_TOKEN" > "$TUNNEL_LOG" 2>&1 &
        TUNNEL_PID=$!

        # Wait for tunnel to register at least one connection
        for i in $(seq 1 15); do
            if grep -q "Registered tunnel connection" "$TUNNEL_LOG" 2>/dev/null; then
                echo -e "${GREEN}[Tunnel]${NC} Connected to Cloudflare edge!"
                break
            fi
            if grep -q "error" "$TUNNEL_LOG" 2>/dev/null; then
                echo -e "${YELLOW}[Tunnel]${NC} Warning: tunnel reported errors, check $TUNNEL_LOG"
                break
            fi
            sleep 1
        done

        # Final status check
        if grep -q "Registered tunnel connection" "$TUNNEL_LOG" 2>/dev/null; then
            :  # all good
        else
            echo -e "${YELLOW}[Tunnel]${NC} Tunnel may not be connected yet, check: $TUNNEL_LOG"
        fi
    else
        echo -e "${YELLOW}[Tunnel]${NC} TUNNEL_TOKEN is empty in $ENV_FILE, skipping"
    fi
else
    echo -e "${YELLOW}[Tunnel]${NC} $ENV_FILE not found, skipping tunnel"
fi

# ── Done ─────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}  Local    :${NC} http://localhost:$PORT"
echo -e "${CYAN}  Website  :${NC} https://trufflekit.com"
echo -e "${CYAN}  Admin    :${NC} http://127.0.0.1:$ADMIN_PORT (local only)"
echo -e ""
echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}"
echo ""

# Wait
wait
