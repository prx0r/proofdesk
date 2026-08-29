#!/usr/bin/env bash
# ProofDesk — launch the web app
# Usage: ./run.sh [--port 8000]
set -e

PORT=${1:-8000}
if [ "$1" = "--port" ]; then PORT=${2:-8000}; fi

cd "$(dirname "$0")"
echo "Starting ProofDesk on http://localhost:${PORT}"
echo "  API docs: http://localhost:${PORT}/docs"
echo "  Web UI:   http://localhost:${PORT}/"
echo ""
python3 -m uvicorn src.api.app:app --host 0.0.0.0 --port "$PORT" --reload
