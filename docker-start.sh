#!/bin/bash
# Quick start script for Docker deployment

set -e

echo "======================================================================"
echo "Reachy Mini CCTV - Docker Quick Start"
echo "======================================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  Please edit .env and configure:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - TELEGRAM_CHAT_ID"
    echo "   - CAMERA_SOURCE"
    echo ""
    read -p "Press Enter after configuring .env to continue..."
fi

# Check if models exist
if [ ! -d core/models ] || [ -z "$(ls -A core/models/*.onnx 2>/dev/null)" ]; then
    echo "⚠️  ONNX models not found in core/models/"
    echo "Please download models first:"
    echo "  python scripts/setup_models_from_insightface.py"
    echo ""
    read -p "Press Enter after downloading models to continue..."
fi

echo "Starting Docker Compose..."
echo ""

# Build and start services
docker compose up --build -d

echo ""
echo "======================================================================"
echo "✓ Services started!"
echo "======================================================================"
echo ""
echo "Backend API:    http://localhost:8000"
echo "Web Dashboard:  http://localhost:3000"
echo "API Docs:       http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "  docker compose ps              # Check service status"
echo "  docker compose logs -f         # Follow logs"
echo "  docker compose logs backend    # Backend logs"
echo "  docker compose logs web        # Web logs"
echo "  docker compose stop            # Stop services"
echo "  docker compose down            # Stop and remove containers"
echo "  docker compose down -v         # Stop and remove all data"
echo ""
echo "======================================================================"
