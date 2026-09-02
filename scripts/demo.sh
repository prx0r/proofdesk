#!/usr/bin/env bash
set -euo pipefail

echo "ProofDesk Hackathon Demo"
echo "========================"
echo ""

# 1. Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# 2. Check venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Install deps
echo "Installing dependencies..."
pip install -r requirements.txt -q

# 4. Check .env
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || true
fi

# 5. Check Nutrient key
if [ -z "${NUTRIENT_API_KEY:-}" ]; then
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs) 2>/dev/null || true
    fi
fi

# 6. Print status
echo ""
if [ -n "${NUTRIENT_API_KEY:-}" ]; then
    echo "Nutrient DWS:    LIVE"
else
    echo "Nutrient DWS:    STUB (deterministic replay)"
fi
echo "Demo fixtures:   READY"
echo "Audit store:     READY"
echo ""

# 7. Start server
PORT="${PORT:-8080}"
echo "Server: http://localhost:${PORT}"
echo "Demo:   http://localhost:${PORT}/demo"
echo "API:    http://localhost:${PORT}/v1/providers/status"
echo ""
echo "Press Ctrl+C to stop."
echo ""

exec uvicorn src.api.app:app --host 0.0.0.0 --port "$PORT"
