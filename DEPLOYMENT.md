# Reachy Mini CCTV - Deployment Guide

This guide explains how to deploy the Reachy Mini CCTV system on a Raspberry Pi 5.

## Prerequisites

- Raspberry Pi 5 (4GB or 8GB RAM recommended)
- Raspberry Pi OS (64-bit, Bookworm or later)
- Python 3.11 or later
- Camera (Reachy Mini built-in or USB webcam)
- Internet connection for Telegram notifications

## Installation Steps

### 1. System Preparation

Update your system:
```bash
sudo apt update && sudo apt upgrade -y
```

Install system dependencies:
```bash
sudo apt install -y \
    python3-pip \
    python3-venv \
    libgl1 \
    libglib2.0-0 \
    libsqlite3-0 \
    git
```

### 2. Clone the Repository

```bash
cd ~
git clone https://github.com/yourusername/reachy-mini-cctv.git
cd reachy-mini-cctv
```

### 3. Set Up Python Environment

Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install Python dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If using Reachy Mini SDK:
```bash
pip install reachy-sdk-api
```

### 4. Download ONNX Models

Run the model setup script:
```bash
python scripts/setup_models_from_insightface.py
```

This will download the required face detection and embedding models.

### 5. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and configure:
```bash
nano .env
```

Required settings:
```
# Telegram Bot Configuration (get from @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Camera Configuration
CAMERA_SOURCE=reachy  # or "0" for webcam, or path to video file

# Paths (adjust if needed)
DB_PATH=./data/cctv.db
FAISS_INDEX_PATH=./data/faces.index
PHOTO_DIR=./data/photos/
```

### 6. Initialize the Database

The database will be automatically initialized on first run, but you can test it:
```bash
python -c "from db.database import get_db; db = get_db(); print('Database OK')"
```

### 7. Run a Benchmark

Test the system performance:
```bash
python scripts/benchmark.py
```

Expected results on Raspberry Pi 5:
- Face Detection: 15-25 FPS
- Face Embedding: 40-60 FPS
- Full Pipeline: 10-15 FPS

### 8. Test the System

Run the system manually first:
```bash
python main.py
```

You should see:
- System initialization messages
- Camera connection
- API server starting on http://0.0.0.0:8000

Test the API:
```bash
curl http://localhost:8000/health
```

Test the web dashboard:
- Configure Next.js (see Web Dashboard section below)
- Or use the API directly

Press `Ctrl+C` to stop.

## Systemd Service Setup

For automatic startup on boot:

### 1. Install the Service

```bash
# Copy the service file
sudo cp reachy-mini-cctv.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable the service
sudo systemctl enable reachy-mini-cctv

# Start the service
sudo systemctl start reachy-mini-cctv
```

### 2. Check Service Status

```bash
sudo systemctl status reachy-mini-cctv
```

### 3. View Logs

```bash
# View recent logs
sudo journalctl -u reachy-mini-cctv -n 50

# Follow logs in real-time
sudo journalctl -u reachy-mini-cctv -f
```

### 4. Restart/Stop Service

```bash
# Restart
sudo systemctl restart reachy-mini-cctv

# Stop
sudo systemctl stop reachy-mini-cctv

# Disable auto-start
sudo systemctl disable reachy-mini-cctv
```

## Web Dashboard Setup

The Next.js web dashboard runs separately from the backend.

### Development Mode

```bash
cd web
npm install
npm run dev
```

The dashboard will be available at http://localhost:3000

### Production Build

```bash
cd web
npm run build
npm start
```

### Configure API URL

Edit `web/.env.local`:
```
NEXT_PUBLIC_API_URL=http://your-pi-ip:8000
```

## User Registration

Register users via the web dashboard or using the CLI:

```bash
python scripts/register_face.py --name "John Doe" --image path/to/photo.jpg
```

The script will:
1. Detect the face in the image
2. Extract the embedding
3. Register the user in the database and FAISS index

## Monitoring & Maintenance

### Check System Health

```bash
# API health check
curl http://localhost:8000/health

# Database stats
sqlite3 data/cctv.db "SELECT COUNT(*) FROM users;"
sqlite3 data/cctv.db "SELECT COUNT(*) FROM events;"
```

### Backup Data

```bash
# Backup script
#!/bin/bash
BACKUP_DIR=~/cctv-backups/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

cp data/cctv.db $BACKUP_DIR/
cp data/faces.index $BACKUP_DIR/
cp data/faces_mapping.json $BACKUP_DIR/
cp -r data/photos $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
```

### Clean Up Old Photos

Old unknown visitor photos can accumulate. Clean them periodically:

```python
from datetime import datetime, timedelta
from camera.photo import PhotoStorage

storage = PhotoStorage()
before_date = datetime.now() - timedelta(days=30)  # Keep last 30 days
deleted_count = storage.delete_old_photos(before_date)
print(f"Deleted {deleted_count} old photos")
```

## Troubleshooting

### Camera Issues

**Problem:** Camera not detected
```bash
# Check camera devices
ls -l /dev/video*

# Test with v4l2
v4l2-ctl --list-devices
```

**Solution:** Ensure camera permissions:
```bash
sudo usermod -a -G video $USER
```

### ONNX Model Issues

**Problem:** Model not found errors

**Solution:** Re-run model download:
```bash
python scripts/setup_models_from_insightface.py
```

### Performance Issues

**Problem:** Low FPS on Pi 5

**Solutions:**
1. Reduce input resolution in `core/config.py`:
   ```python
   DETECTION_INPUT_SIZE = (320, 240)  # Lower resolution
   ```

2. Enable frame skipping in pipeline (process every Nth frame)

3. Adjust thread count in detector/embedder:
   ```python
   sess_options.intra_op_num_threads = 2  # Reduce threads
   ```

### Memory Issues

**Problem:** Out of memory errors

**Solution:** Adjust systemd service memory limit:
```ini
MemoryLimit=4G  # Increase limit
```

### Telegram Notifications Not Working

**Problem:** Alerts not being sent

**Check:**
1. Bot token is correct: `echo $TELEGRAM_BOT_TOKEN`
2. Chat ID is correct
3. Test connection:
   ```python
   from notifications.telegram import get_notifier
   notifier = get_notifier()
   notifier.test_connection()
   ```

## Performance Tuning

### For Best Performance on Pi 5:

1. **Use smaller input resolution:** 320x240 or 480x360
2. **Increase confidence thresholds:** Reduce false positives
3. **Frame skipping:** Process every 2nd or 3rd frame
4. **Optimize thread count:** 2-4 threads per model

### Configuration Example:

```python
# core/config.py
DETECTION_INPUT_SIZE = (320, 240)
DETECTION_CONFIDENCE_THRESHOLD = 0.8  # Higher = fewer false positives
CAMERA_FPS = 15  # Lower FPS reduces load
```

## Security Considerations

1. **Protect environment variables:**
   ```bash
   chmod 600 .env
   ```

2. **Secure Telegram bot token:** Never commit to git

3. **API security:** Use firewall rules to restrict access:
   ```bash
   sudo ufw allow from 192.168.1.0/24 to any port 8000
   ```

4. **Photo storage:** Photos contain sensitive biometric data - handle carefully

5. **Database backup:** Regular encrypted backups

## Updating the System

```bash
cd ~/reachy-mini-cctv
git pull
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart reachy-mini-cctv
```

## Additional Resources

- **Reachy Mini SDK:** https://docs.pollen-robotics.com/
- **InsightFace Models:** https://github.com/deepinsight/insightface
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **Next.js Documentation:** https://nextjs.org/docs

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/reachy-mini-cctv/issues
- Documentation: See README.md and ARCHITECTURE.md
