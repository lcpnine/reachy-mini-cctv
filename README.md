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
git clone https://github.com/lcpnine/reachy-mini-cctv.git
cd reachy-mini-cctv

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
- **API**: http://localhost:8501
- **API Docs**: http://localhost:8501/docs

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

Node.js 24.x required. On Debian/Ubuntu/Raspberry Pi OS, use NodeSource if apt's version is too old:
```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
```

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

# Reachy Mini Wireless (when CAMERA_SOURCE=reachy)
# REACHY_MEDIA_BACKEND=gstreamer   # when running on robot (SSH)
# REACHY_MEDIA_BACKEND=webrtc      # when running from your computer (remote)

# Thresholds
DETECTION_THRESHOLD=0.7
RECOGNITION_THRESHOLD=0.45
COOLDOWN_SECONDS=30

# API
API_HOST=0.0.0.0
API_PORT=8501
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
curl http://localhost:8501/api/events?limit=10

# Get event statistics
curl http://localhost:8501/api/events/stats

# Get registered users
curl http://localhost:8501/api/users
```

### Viewing Photos

Unknown visitor photos are stored in `data/photos/` and accessible via:
- Web dashboard Photos page
- API endpoint: `http://localhost:8501/api/photos/{filename}`

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
reachy-mini-cctv/
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
sudo cp reachy-mini-cctv.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable reachy-mini-cctv
sudo systemctl start reachy-mini-cctv

# Check status
sudo systemctl status reachy-mini-cctv

# View logs
sudo journalctl -u reachy-mini-cctv -f
```

## API Documentation

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8501/docs
- **ReDoc**: http://localhost:8501/redoc

Key endpoints:
- `POST /api/users` - Register a new user
- `GET /api/users` - List registered users
- `DELETE /api/users/{user_id}` - Delete a user
- `GET /api/events` - Get events with pagination
- `GET /api/events/stream/sse` - Real-time event stream
- `GET /api/photos/{filename}` - Get photo
- `GET /health` - Health check

## Troubleshooting

### Web Dashboard "This site can't be reached" (Reachy Mini)

When running on the robot with `run-on-robot.sh`, if `http://reachy-mini.local:3000` doesn't load from your computer:

1. **Same network**: PC and robot must be on the same Wi‑Fi. Test: `ping reachy-mini.local`
2. **Use robot IP** if mDNS fails: `ssh pollen@reachy-mini.local "hostname -I"` → then open `http://<IP>:3000`
3. **Verify servers are running**:
   ```bash
   ssh pollen@reachy-mini.local -t tmux attach -t reachy-mini-cctv  # Check web window for errors
   ssh pollen@reachy-mini.local "ss -tlnp | grep -E '3000|8501'"  # Ports listening?
   ```
4. **Firewall** (on robot): `sudo ufw status` → if active, allow: `sudo ufw allow 3000/tcp && sudo ufw allow 8501/tcp`

Reachy Mini does **not** require explicitly opening ports in normal setups; the web server binds to `0.0.0.0` by default.

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

## Deploying on Reachy Mini Wireless

To run this CCTV app on **Reachy Mini Wireless** (robot with battery + Wi‑Fi), you can either run the app **on the robot** (SSH) or **remotely** from your computer.

### Option A: Run on the robot (SSH) — recommended for testing

Lower latency and no dependency on your PC once deployed.

1. **Connect via SSH**
   ```bash
   ssh pollen@reachy-mini.local
   # Password: root
   ```
   (Robot and computer must be on the same network; hostname is often `reachy-mini` or `reachy-mini.local`.)

2. **On the robot, set up the project**
   ```bash
   # Optional: use the pre-installed venv or create your own
   source /venvs/apps_venv/bin/activate   # if available
   # Or: python3 -m venv venv && source venv/bin/activate

   git clone https://github.com/lcpnine/reachy-mini-cctv.git
   cd reachy-mini-cctv
   pip install -r requirements.txt
   pip install "reachy-mini[gstreamer]"   # Required on robot for camera (gi/PyGObject)
   python scripts/setup_models_from_insightface.py
   cp .env.example .env && nano .env   # Set TELEGRAM_*, CAMERA_SOURCE=reachy
   ```

   **Node.js 24.x** (for web dashboard, if using `run-on-robot.sh`):
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
   sudo apt-get install -y nodejs
   ```

3. **Run the app**
   ```bash
   python main.py --camera reachy
   ```
   The daemon is already running when the robot is powered on. Use `ReachyMini(media_backend="gstreamer")` when running on the robot (this project’s camera layer can be configured for that).

### Option B: Run remotely (from your computer)

Your Python code runs on your machine; the robot sends camera over the network (WebRTC).

1. **Same network**: Ensure the robot and your computer are on the same Wi‑Fi.
2. **Install on your computer**
   ```bash
   pip install reachy-mini
   ```
3. **Point the app at the robot**: Use `ReachyMini(connection_mode="network")` and `media_backend="webrtc"` so camera comes from the robot. The REST daemon on the robot is at `http://reachy-mini.local:8000` (or the robot’s IP).

**Note:** This codebase’s Reachy camera layer supports both the legacy `reachy_sdk_api` and the official `reachy_mini` SDK. For Wireless, the `reachy_mini` SDK with the appropriate `media_backend` (`gstreamer` on device, `webrtc` when remote) is used.

### Run/stop from your computer (scripts)

From your machine you can start or stop the app on the robot without opening an SSH shell:

```bash
# Start on robot (runs in tmux; keeps running after you disconnect)
./scripts/run-on-robot.sh

# Attach to the running session to see logs
./scripts/run-on-robot.sh --attach

# Run in foreground (exits when SSH disconnects)
./scripts/run-on-robot.sh --foreground

# Stop the app on the robot
./scripts/stop-on-robot.sh
```

Configure robot host/user with environment variables if needed:

```bash
export ROBOT_USER=pollen
export ROBOT_HOST=reachy-mini.local
export ROBOT_PROJECT=reachy-mini-cctv
./scripts/run-on-robot.sh
```

The robot must have the project and venv set up, **Node.js 24.x** (see above), and `tmux` installed (`sudo apt install tmux`).

### Where to run the Dashboard

The **backend (API + camera)** runs on the robot. The **Dashboard (Next.js)** is just a web page: it can run on the robot or on your computer. In both cases you view it **from your computer’s browser**.

| Where Dashboard runs | How you view it | API URL setting |
|----------------------|-----------------|-----------------|
| **On the robot**     | Open **http://\<robot-IP\>:3000** in your browser (e.g. `http://reachy-mini.local:3000`). The page is served by the robot but displayed on your PC. | Build/serve the web app with `NEXT_PUBLIC_API_URL=http://reachy-mini.local:8501` (or the robot’s IP) so the browser calls the API on the robot. |
| **On your computer** | Open **http://localhost:3000** in your browser. | Set `NEXT_PUBLIC_API_URL=http://reachy-mini.local:8501` (or robot IP) in `web/.env.local` so the dashboard talks to the robot’s API. |

So: **라즈베리파이에서 Dashboard 서버를 실행해도**, 브라우저는 **내 컴퓨터**에서 `http://로봇IP:3000`으로 접속하면 됩니다. 서버가 라즈베리파이에 있어도 같은 네트워크라면 PC에서 해당 주소로 접속해 대시보드를 볼 수 있습니다.

### References

- [Reachy Mini Quickstart (run on robot via SSH)](https://huggingface.co/docs/reachy_mini/SDK/quickstart)
- [Reachy Mini Python SDK (camera, media backends)](https://huggingface.co/docs/reachy_mini/SDK/python-sdk)
- Media backends: `default` (Lite), `gstreamer` (Lite or Wireless on device), `webrtc` (Wireless, remote)

### Troubleshooting: `ModuleNotFoundError: No module named 'gi'`

When running on the robot with `--camera reachy`, you may see:

```
ImportError: The 'gi' module is required for GStreamerCamera but could not be imported.
Please install the GStreamer backend: pip install .[gstreamer]
```

**Fix:** Install reachy-mini with the GStreamer extra on the robot:

```bash
ssh pollen@reachy-mini.local
cd ~/reachy-mini-cctv
source venv/bin/activate
pip install "reachy-mini[gstreamer]"
```

Then run the app again.

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

- **GitHub Issues**: https://github.com/lcpnine/reachy-mini-cctv/issues
- **Documentation**: See docs in this repository
- **Reachy Mini**: https://docs.pollen-robotics.com/

---

Built by [lcpnine](https://github.com/lcpnine)
- **GitHub**: https://github.com/lcpnine
- **Email**: [lcpnine@gmail.com](mailto:lcpnine@gmail.com)
- **LinkedIn**: [Yu Taek Lee](https://www.linkedin.com/in/yutaek/)