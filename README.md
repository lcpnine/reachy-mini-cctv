# Reachy Mini CCTV - Face Recognition System

A real-time face recognition and monitoring system designed for the Reachy Mini robot, running on Raspberry Pi 5. Features live face detection, user recognition, unknown visitor alerts via Telegram, and a modern web dashboard.

## Features

- **Real-time Face Recognition**: Detect and recognize faces at 10-15 FPS on Raspberry Pi 5
- **User Management**: Register users with face photos via web interface or CLI
- **Unknown Visitor Alerts**: Automatic Telegram notifications with photos when unknown persons are detected
- **Exponential Backoff**: Smart notification throttling to prevent alert spam
- **Web Dashboard**: Modern Next.js dashboard with live event feed (SSE)
- **Event Logging**: SQLite database with full event history
- **Photo Gallery**: Archive of unknown visitor photos
- **REST API**: Complete FastAPI backend with Swagger documentation
- **Docker Support**: Containerized deployment with Docker Compose

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Face Detection | MediaPipe BlazeFace / SCRFD-500M (ONNX) |
| Face Embedding | EdgeFace-XS (ONNX) |
| Vector Search | FAISS IndexFlatIP |
| Database | SQLite (WAL mode) |
| Backend API | FastAPI (Python) |
| Frontend | Next.js 16 (React 19, TypeScript) |
| Notifications | Telegram Bot API |
| Camera | Reachy Mini SDK / OpenCV |
| Runtime | ONNX Runtime (ARM64) |
| Deployment | Docker + Docker Compose |

## Quick Start (Docker)

The fastest way to get started:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/reachy-cctv.git
cd reachy-cctv

# 2. Download ONNX models
python scripts/setup_models_from_insightface.py

# 3. Configure environment
cp .env.example .env
nano .env  # Edit with your Telegram credentials

# 4. Start with Docker
./docker-start.sh
```

Access the application:
- **Web Dashboard**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Installation (Manual)

For development or non-Docker deployment:

### Prerequisites

- Raspberry Pi 5 (or any ARM64/x64 Linux system)
- Python 3.11+
- Node.js 24.13.1+
- Camera (Reachy Mini or USB webcam)

### Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download ONNX models
python scripts/setup_models_from_insightface.py

# Configure environment
cp .env.example .env
nano .env

# Run the backend
python main.py
```

### Web Dashboard Setup

```bash
cd web
npm install

# Development
npm run dev

# Production
npm run build
npm start
```

## Configuration

Edit `.env` to configure the system:

```bash
# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Camera
CAMERA_SOURCE=0  # or "reachy" for Reachy Mini

# Database & Storage
DB_PATH=./data/cctv.db
FAISS_INDEX_PATH=./data/faces.index
PHOTO_DIR=./data/photos/

# Thresholds
DETECTION_THRESHOLD=0.7
RECOGNITION_THRESHOLD=0.45
COOLDOWN_SECONDS=30

# API
API_HOST=0.0.0.0
API_PORT=8000
```

## Usage

### Registering Users

**Via Web Dashboard:**
1. Navigate to the Users page
2. Click "Add User"
3. Enter name and upload a clear face photo
4. Click "Register"

**Via CLI:**
```bash
python scripts/register_face.py --name "John Doe" --image path/to/photo.jpg
```

### Monitoring Events

**Live Feed:**
- Open http://localhost:3000
- View real-time detections as they occur
- Filter by known/unknown visitors

**API:**
```bash
# Get recent events
curl http://localhost:8000/api/events?limit=10

# Get event statistics
curl http://localhost:8000/api/events/stats

# Get registered users
curl http://localhost:8000/api/users
```

### Viewing Photos

Unknown visitor photos are stored in `data/photos/` and accessible via:
- Web dashboard Photos page
- API endpoint: `http://localhost:8000/api/photos/{filename}`

## Docker Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Rebuild after code changes
docker compose up --build -d

# Clean slate (removes all data)
docker compose down -v
```

## Development

### Project Structure

```
reachy-cctv/
├── core/              # Face detection & recognition
├── db/                # Database layer (SQLite)
├── camera/            # Camera capture & pipeline
├── notifications/     # Telegram notifications
├── api/               # FastAPI backend
├── web/               # Next.js dashboard
├── scripts/           # Utilities (registration, benchmark)
├── docker/            # Dockerfiles
├── main.py            # Main entry point
└── requirements.txt   # Python dependencies
```

### Running Tests

```bash
# Unit tests
pytest tests/

# Benchmark performance
python scripts/benchmark.py

# API tests
pytest tests/test_api.py -v
```

### Benchmark Results (Raspberry Pi 5)

Expected performance:
- Face Detection: ~20 FPS
- Face Embedding: ~50 FPS
- Full Pipeline: ~12 FPS

## Systemd Service (Linux)

For automatic startup on boot:

```bash
# Install service
sudo cp reachy-cctv.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable reachy-cctv
sudo systemctl start reachy-cctv

# Check status
sudo systemctl status reachy-cctv

# View logs
sudo journalctl -u reachy-cctv -f
```

## API Documentation

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Key endpoints:
- `POST /api/users` - Register a new user
- `GET /api/users` - List registered users
- `DELETE /api/users/{user_id}` - Delete a user
- `GET /api/events` - Get events with pagination
- `GET /api/events/stream/sse` - Real-time event stream
- `GET /api/photos/{filename}` - Get photo
- `GET /health` - Health check

## Troubleshooting

### Camera not detected
```bash
# Check camera devices
ls -l /dev/video*

# Test with OpenCV
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Failed')"
```

### Low FPS
Adjust in `core/config.py`:
```python
DETECTION_INPUT_SIZE = (320, 240)  # Lower resolution
```

### Telegram not working
```bash
# Test bot connection
python -c "from notifications.telegram import get_notifier; get_notifier().test_connection()"
```

### Models not found
```bash
# Re-download models
python scripts/setup_models_from_insightface.py
```

## Performance Optimization

For best performance on Raspberry Pi 5:

1. **Lower input resolution**: Use 320x240 or 480x360
2. **Increase thresholds**: Reduce false positives
3. **Enable frame skipping**: Process every 2nd or 3rd frame
4. **Optimize threading**: Adjust `intra_op_num_threads` in models

See `DEPLOYMENT.md` for detailed tuning guide.

## Security

- **Protect .env file**: Never commit to git
- **Secure API**: Use firewall rules to restrict access
- **Photo privacy**: Photos contain biometric data - handle carefully
- **Regular backups**: Backup `data/` directory regularly

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design
- **[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)** - Development roadmap
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Detailed deployment guide

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- **InsightFace** - Face detection and recognition models
- **FAISS** - Vector similarity search
- **FastAPI** - Backend API framework
- **Next.js** - Frontend framework
- **Pollen Robotics** - Reachy Mini robot

## Support

- **GitHub Issues**: https://github.com/yourusername/reachy-cctv/issues
- **Documentation**: See docs in this repository
- **Reachy Mini**: https://docs.pollen-robotics.com/

---

Built with ❤️ for the Reachy Mini robot community
