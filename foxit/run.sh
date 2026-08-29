#!/bin/bash
# ProofDesk — Foxit Track Run Script
set -e

cd "$(dirname "$0")"

echo "=========================================="
echo "  ProofDesk — Foxit Track"
echo "  'Your Agent Shouldn't Sign That'"
echo "=========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Install deps if needed
if [ ! -d "../../.venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv ../../.venv
    source ../../.venv/bin/activate
    pip install -q httpx numpy scipy scikit-learn matplotlib
else
    source ../../.venv/bin/activate
fi

# Check Foxit API keys
if [ -z "$FOXIT_CLOUD_API_CLIENT_ID" ]; then
    echo ""
    echo "NOTE: No Foxit API keys set. Running in simulated mode."
    echo "To use real APIs:"
    echo "  export FOXIT_CLOUD_API_CLIENT_ID='your_id'"
    echo "  export FOXIT_CLOUD_API_CLIENT_SECRET='your_secret'"
    echo "  export FOXIT_ESIGN_CLIENT_ID='your_esign_id'"
    echo "  export FOXIT_ESIGN_CLIENT_SECRET='your_esign_secret'"
    echo ""
fi

# Run rubric validation
echo ""
echo "--- Rubric Validation ---"
python3 validate_rubrics.py --sponsor foxit

# Run demo
echo ""
echo "--- Running Demo ---"
python3 demo_mvp.py

# Run benchmark (optional)
if [ "$1" = "--benchmark" ]; then
    echo ""
    echo "--- Running Benchmark ---"
    python3 -m src.signing_bench --n 200
fi

echo ""
echo "=========================================="
echo "  Done!"
echo "=========================================="
