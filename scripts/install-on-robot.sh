#!/usr/bin/env bash
#
# Run this script ON THE ROBOT (after ssh pollen@reachy-mini.local)
# Sets up venv, installs dependencies, downloads models.
#
# Usage:
#   ssh pollen@reachy-mini.local
#   cd ~/reachy-mini-cctv
#   bash scripts/install-on-robot.sh
#

set -e

PROJECT_DIR="${1:-$HOME/reachy-mini-cctv}"
cd "$PROJECT_DIR"

echo "=== Installing Reachy Mini CCTV in $PROJECT_DIR ==="

# Create venv
if [[ ! -d venv ]]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install "reachy-mini[gstreamer]"

# Download ONNX models (skip if already present)
if [[ -f core/models/face_detection.onnx ]] && [[ -f core/models/edgeface_xs_gamma_06.onnx ]]; then
  echo "Models already present, skipping download."
else
  echo "Downloading face recognition models..."
  python scripts/setup_models_from_insightface.py || true
fi

# Create .env if missing
if [[ ! -f .env ]]; then
  echo "Creating .env from example..."
  cp .env.example .env
  echo ""
  echo "⚠️  Edit .env and set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CAMERA_SOURCE=reachy"
  echo "   nano .env"
fi

echo ""
echo "=== Install complete ==="
echo "Run: source venv/bin/activate && python main.py --camera reachy"
echo "Or from your PC: ./scripts/run-on-robot.sh"
