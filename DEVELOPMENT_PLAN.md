# Reachy Mini CCTV — Development Plan

This document is written with the assumption that tasks will be delegated to AI agents. Each Phase is an independently runnable unit, and each Task within a Phase is designed to be completable within a single prompt session. Every Task specifies explicit Done Criteria and test methods.

---

## Tech Stack Summary

| Layer | Choice |
|---|---|
| Face Detection | MediaPipe BlazeFace (Short Range) / SCRFD-500M fallback |
| Face Embedding | EdgeFace-xs (edgeface_xs_gamma_06) via ONNX |
| Inference Runtime | ONNX Runtime (ARM64) |
| Vector Search | FAISS IndexFlatIP |
| Metadata DB | SQLite (WAL mode) |
| Backend API | FastAPI (Python) |
| Frontend | Next.js (Node 24.13.1) |
| Notifications | Telegram Bot API |
| Camera Interface | Reachy Mini SDK |
| Device | Raspberry Pi 5 (ARM64, no GPU) |
| Containerization | Docker + Docker Compose |

---

## Project Structure (Target)

```
reachy-mini-cctv/
├── core/                    # Phase 1–2: Detection & Recognition engine
│   ├── detector.py          #   Face detection (BlazeFace / SCRFD)
│   ├── embedder.py          #   Face embedding (EdgeFace)
│   ├── recognizer.py        #   FAISS search + threshold logic
│   ├── models/              #   ONNX model files
│   └── config.py            #   Thresholds, paths, constants
├── db/                      # Phase 3: Data layer
│   ├── database.py          #   SQLite connection + WAL setup
│   ├── schema.sql           #   Table definitions
│   ├── user_repo.py         #   User CRUD operations
│   └── event_repo.py        #   Event logging operations
├── camera/                  # Phase 4: Camera pipeline
│   ├── capture.py           #   Reachy Mini SDK frame capture
│   ├── pipeline.py          #   Main loop: capture → detect → recognize → act
│   └── photo.py             #   Best-frame selection + storage
├── notifications/           # Phase 5: Alerts
│   ├── telegram.py          #   Telegram Bot send logic
│   └── backoff.py           #   Per-visitor exponential backoff tracker
├── api/                     # Phase 6: Backend API
│   ├── main.py              #   FastAPI app entry
│   ├── routes/
│   │   ├── events.py        #   GET events, SSE live stream
│   │   ├── users.py         #   User CRUD endpoints
│   │   └── photos.py        #   Photo serving
│   ├── deps.py              #   Shared dependencies (DB, FAISS index)
│   └── schemas.py           #   Pydantic models
├── web/                     # Phase 7: Next.js dashboard
│   ├── app/                 #   App Router (page.tsx, users/, photos/)
│   └── ...
├── scripts/                 # Utilities
│   ├── register_face.py     #   CLI: register a user from image
│   └── benchmark.py         #   CLI: measure pipeline FPS on device
├── tests/                   # Mirrors source structure
│   ├── test_detector.py
│   ├── test_embedder.py
│   ├── test_recognizer.py
│   ├── test_database.py
│   ├── test_pipeline.py
│   ├── test_telegram.py
│   └── test_api.py
├── docker/                  # Phase 9: Docker configuration
│   ├── backend.Dockerfile   #   Backend (FastAPI + pipeline) image
│   └── frontend.Dockerfile  #   web (Next.js) image
├── docker-compose.yml       #   Full-stack orchestration
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md
└── README.md
```

---

## Phase 1 — Face Detection Module

**Goal:** Build a standalone module that takes an image as input and returns face bounding box coordinates.

### Task 1.1: ONNX Model Preparation

**Work:**
- Download the MediaPipe BlazeFace Short Range TFLite model
- Convert to ONNX format using `tf2onnx` or manual conversion
- If conversion proves difficult, use the SCRFD-500M ONNX model (provided by InsightFace) as fallback
- Place model files in `core/models/`

**Done Criteria:**
- An `.onnx` file exists in `core/models/`
- Loading the model with ONNX Runtime creates a session without errors

**Test:**
```python
import onnxruntime as ort
session = ort.InferenceSession("core/models/face_detection.onnx")
assert session.get_inputs()[0].shape is not None
```

### Task 1.2: Detector Class Implementation

**Work:**
- Implement `FaceDetector` class in `core/detector.py`
- Input: OpenCV BGR image (numpy array)
- Output: `List[BBox]` — each BBox is `(x1, y1, x2, y2, confidence)`
- Include preprocessing (resize, normalization) and postprocessing (NMS, confidence threshold)
- Manage confidence threshold in `core/config.py` (default: 0.7)

**Done Criteria:**
- Returns 1+ BBoxes for a test image containing faces
- Returns an empty list for images without faces
- Detections below the confidence threshold are filtered out

**Test:**
```python
# tests/test_detector.py
def test_detect_single_face():
    img = cv2.imread("tests/fixtures/single_face.jpg")
    detector = FaceDetector()
    boxes = detector.detect(img)
    assert len(boxes) == 1
    assert boxes[0].confidence > 0.7

def test_detect_no_face():
    img = cv2.imread("tests/fixtures/no_face.jpg")
    boxes = FaceDetector().detect(img)
    assert len(boxes) == 0

def test_detect_multiple_faces():
    img = cv2.imread("tests/fixtures/group.jpg")
    boxes = FaceDetector().detect(img)
    assert len(boxes) >= 2
```

---

## Phase 2 — Face Embedding & Recognition

**Goal:** Extract a 512-dimensional embedding from detected faces and match them against registered users using a FAISS index.

**Dependency:** Phase 1 complete

### Task 2.1: Embedder Class Implementation

**Work:**
- Download the EdgeFace ONNX model to `core/models/` (available from GitHub/HuggingFace)
- Implement `FaceEmbedder` class in `core/embedder.py`
- Input: cropped face image (cropped based on BBox)
- Internal processing: 112×112 resize → normalize → ONNX inference
- Output: L2-normalized 512-dim numpy array

**Done Criteria:**
- Cosine similarity > 0.5 between embeddings of two photos of the same person
- Cosine similarity < 0.3 between embeddings of two different people
- L2 norm of output vector ≈ 1.0

**Test:**
```python
# tests/test_embedder.py
def test_embedding_shape():
    emb = FaceEmbedder().embed(cropped_face)
    assert emb.shape == (512,)

def test_embedding_normalized():
    emb = FaceEmbedder().embed(cropped_face)
    assert abs(np.linalg.norm(emb) - 1.0) < 1e-5

def test_same_person_similarity():
    emb1 = embedder.embed(person_a_photo_1)
    emb2 = embedder.embed(person_a_photo_2)
    assert np.dot(emb1, emb2) > 0.5

def test_different_person_dissimilarity():
    emb_a = embedder.embed(person_a)
    emb_b = embedder.embed(person_b)
    assert np.dot(emb_a, emb_b) < 0.3
```

### Task 2.2: Recognizer Class Implementation (FAISS)

**Work:**
- Implement `FaceRecognizer` class in `core/recognizer.py`
- Use FAISS `IndexFlatIP` to store registered embeddings
- Key methods:
  - `register(user_id: int, embedding: np.ndarray)` — add to index
  - `remove(user_id: int)` — remove from index
  - `recognize(embedding: np.ndarray) -> (user_id | None, confidence)` — search
- Manage matching threshold in `config.py` (default: 0.45)
- Return `(None, confidence)` if below threshold (unknown)
- Internally manage the mapping between FAISS index positions and user IDs
- Include index save/load functionality (`faiss.write_index` / `faiss.read_index`)

**Done Criteria:**
- Searching with a registered user's embedding returns the correct user_id
- Searching with an unregistered user's embedding returns None
- Loading a saved index produces identical search results
- After removal, the user_id is no longer matched

**Test:**
```python
# tests/test_recognizer.py
def test_register_and_recognize():
    rec = FaceRecognizer()
    rec.register(1, embedding_a)
    user_id, conf = rec.recognize(embedding_a_variant)
    assert user_id == 1

def test_unknown_person():
    rec = FaceRecognizer()
    rec.register(1, embedding_a)
    user_id, conf = rec.recognize(embedding_stranger)
    assert user_id is None

def test_persistence():
    rec = FaceRecognizer()
    rec.register(1, embedding_a)
    rec.save("test_index.faiss")
    rec2 = FaceRecognizer.load("test_index.faiss")
    user_id, _ = rec2.recognize(embedding_a_variant)
    assert user_id == 1

def test_remove():
    rec = FaceRecognizer()
    rec.register(1, embedding_a)
    rec.remove(1)
    user_id, _ = rec.recognize(embedding_a_variant)
    assert user_id is None
```

---

## Phase 3 — Database Layer

**Goal:** Build a SQLite-based data layer for user registration and event logging.

**Dependency:** None (can run in parallel with Phase 1–2)

### Task 3.1: Schema Definition & DB Initialization

**Work:**
- Write table definitions in `db/schema.sql`
- Implement a connection management class in `db/database.py`
  - Enable WAL mode
  - Set `PRAGMA synchronous=NORMAL`
  - Auto-create schema on app startup (CREATE IF NOT EXISTS)
- Schema:
  ```sql
  CREATE TABLE users (
      user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
      name       TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE events (
      event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id     INTEGER REFERENCES users(user_id),  -- NULL = unknown
      confidence  REAL,
      photo_path  TEXT,      -- NULL for known users
      occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE INDEX idx_events_occurred ON events(occurred_at DESC);
  CREATE INDEX idx_events_user ON events(user_id);
  ```

**Done Criteria:**
- DB file is created and WAL mode is enabled
- Tables and indexes exist

**Test:**
```python
def test_db_init():
    db = Database(":memory:")
    mode = db.execute("PRAGMA journal_mode;").fetchone()[0]
    assert mode == "wal"

def test_tables_exist():
    db = Database(":memory:")
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = {t[0] for t in tables}
    assert "users" in names
    assert "events" in names
```

### Task 3.2: Repository Class Implementation

**Work:**
- `db/user_repo.py`:
  - `create_user(name) -> user_id`
  - `get_user(user_id) -> User | None`
  - `list_users() -> List[User]`
  - `delete_user(user_id) -> bool`
- `db/event_repo.py`:
  - `log_event(user_id: int | None, confidence: float, photo_path: str | None) -> event_id`
  - `get_events(limit, offset, user_id_filter) -> List[Event]`
  - `get_recent_events(since: datetime) -> List[Event]`

**Done Criteria:**
- All CRUD operations work correctly
- Querying a non-existent user_id returns None
- Timestamps are automatically recorded when logging events

**Test:**
```python
def test_create_and_get_user():
    user_id = user_repo.create_user("Alice")
    user = user_repo.get_user(user_id)
    assert user.name == "Alice"

def test_delete_user():
    user_id = user_repo.create_user("Bob")
    user_repo.delete_user(user_id)
    assert user_repo.get_user(user_id) is None

def test_log_event():
    event_id = event_repo.log_event(user_id=1, confidence=0.92, photo_path=None)
    events = event_repo.get_events(limit=1)
    assert events[0].event_id == event_id

def test_unknown_event_with_photo():
    event_id = event_repo.log_event(
        user_id=None, confidence=0.15, photo_path="photos/unknown_001.jpg"
    )
    event = event_repo.get_events(limit=1)[0]
    assert event.user_id is None
    assert event.photo_path is not None
```

---

## Phase 4 — Camera Pipeline & Main Loop

**Goal:** Capture frames from the Reachy Mini camera and wire together Phase 1–3 modules into a real-time recognition pipeline.

**Dependency:** Phase 1, 2, 3 all complete

### Task 4.1: Camera Capture Module

**Work:**
- Implement Reachy Mini SDK frame capture logic in `camera/capture.py`
- Interface:
  - `CameraCapture.start()` — start capturing
  - `CameraCapture.read() -> np.ndarray` — return the latest frame
  - `CameraCapture.stop()` — release resources
- Provide an OpenCV VideoCapture fallback for testing without the SDK (webcam/video file)

**Done Criteria:**
- Frames can be captured via Reachy Mini SDK or OpenCV fallback
- `read()` returns a BGR numpy array
- Resources are cleaned up after `stop()`

**Test:**
```python
def test_capture_fallback():
    cap = CameraCapture(source="tests/fixtures/test_video.mp4")
    cap.start()
    frame = cap.read()
    assert frame.shape[2] == 3  # BGR
    cap.stop()
```

### Task 4.2: Best-Frame Selector

**Work:**
- Implement best-frame selection logic in `camera/photo.py`
- On unknown detection, select the sharpest frame from the first N frames (e.g., 15 frames ≈ 0.5s)
- Sharpness metric: Laplacian variance (higher = sharper)
- Save the selected frame to the `photos/` directory
- Filename format: `unknown_{timestamp}_{sequence}.jpg`

**Done Criteria:**
- The frame with the highest Laplacian variance is selected from multiple frames
- The saved image is a valid JPEG

**Test:**
```python
def test_best_frame_selection():
    frames = [blurry_frame, sharp_frame, medium_frame]
    selector = BestFrameSelector()
    for f in frames:
        selector.add(f, confidence=0.9)
    best = selector.select()
    assert laplacian_var(best) == laplacian_var(sharp_frame)
```

### Task 4.3: Main Pipeline Loop

**Work:**
- Implement the main pipeline loop in `camera/pipeline.py`
- Loop flow:
  1. Acquire frame via `capture.read()`
  2. Detect faces via `detector.detect(frame)`
  3. For each face: crop → extract embedding via `embedder.embed(crop)`
  4. Match via `recognizer.recognize(embedding)`
  5. Branch on result:
     - Known → `event_repo.log_event(user_id, confidence, None)`
     - Unknown → best-frame capture → `event_repo.log_event(None, confidence, photo_path)` → trigger notification
- Duplicate logging prevention: if the same person is detected in consecutive frames, suppress re-logging for a cooldown period (e.g., 30 seconds)
- Provide event callbacks for external observation (notifications, dashboard)

**Done Criteria:**
- Running the pipeline on a test video correctly logs known/unknown events
- Same-person cooldown works
- Callbacks are invoked correctly

**Test:**
```python
def test_pipeline_known_user(mock_camera, mock_recognizer):
    """A registered user appearing triggers an event log."""
    events = []
    pipeline = Pipeline(
        camera=mock_camera,
        detector=detector,
        embedder=embedder,
        recognizer=mock_recognizer,  # configured to return user_id=1
        on_event=events.append
    )
    pipeline.run_once()
    assert len(events) == 1
    assert events[0].user_id == 1

def test_pipeline_unknown_triggers_photo(mock_camera):
    """An unregistered person appearing triggers photo capture."""
    pipeline = Pipeline(...)
    pipeline.run_once()
    assert os.path.exists(events[0].photo_path)

def test_cooldown_prevents_duplicate():
    """The same person detected consecutively is not re-logged during cooldown."""
    pipeline = Pipeline(...)
    pipeline.run_once()  # 1st detection → logged
    pipeline.run_once()  # 2nd detection within cooldown → skipped
    assert len(events) == 1
```

---

## Phase 5 — Telegram Notifications

**Goal:** Send a photo + message via Telegram when an unknown person is detected, with exponential backoff for repeated detections.

**Dependency:** Phase 4 complete (uses the callback interface)

### Task 5.1: Telegram Bot Send Module

**Work:**
- Implement `notifications/telegram.py`
- Use the `python-telegram-bot` library or direct HTTP API calls
- Method: `send_alert(chat_id, photo_path, message) -> bool`
- Load bot token and chat_id from `.env`
- Retry up to 3 times on send failure (exponential backoff)
- On network error, log and do not halt the pipeline

**Done Criteria:**
- A message with a photo is successfully sent via a real Telegram Bot
- Calling with an invalid token does not propagate an exception; returns False

**Test:**
```python
def test_send_alert_success(mock_telegram_api):
    result = send_alert(CHAT_ID, "tests/fixtures/face.jpg", "Unknown detected")
    assert result is True
    assert mock_telegram_api.called

def test_send_alert_network_error(mock_telegram_api_failing):
    result = send_alert(CHAT_ID, "tests/fixtures/face.jpg", "Unknown detected")
    assert result is False  # Graceful failure
```

### Task 5.2: Exponential Backoff Tracker

**Work:**
- Implement `notifications/backoff.py`
- Track each unknown visitor based on embedding similarity
  - Same unknown: cosine similarity between new embedding and existing unknown embedding > threshold
- Alert schedule:
  - 1st detection: send immediately
  - 2nd: after 10 seconds
  - 3rd: after 20 seconds
  - 4th: after 40 seconds
  - nth: interval doubles each time
- Remove from tracker after the unknown has been out of view for a set period (e.g., 5 minutes)

**Done Criteria:**
- Alerts for the same unknown visitor follow the backoff schedule
- Different unknown visitors have independent backoff sequences
- Tracker cleans up after a visitor disappears

**Test:**
```python
def test_backoff_schedule():
    tracker = BackoffTracker()
    visitor_emb = np.random.randn(512)
    visitor_emb /= np.linalg.norm(visitor_emb)

    assert tracker.should_alert(visitor_emb, t=0) is True    # 1st: immediate
    assert tracker.should_alert(visitor_emb, t=5) is False   # 5s: too early
    assert tracker.should_alert(visitor_emb, t=10) is True   # 10s: 2nd alert
    assert tracker.should_alert(visitor_emb, t=20) is False  # 20s: too early
    assert tracker.should_alert(visitor_emb, t=30) is True   # 30s: 3rd alert

def test_independent_visitors():
    tracker = BackoffTracker()
    assert tracker.should_alert(visitor_a_emb, t=0) is True
    assert tracker.should_alert(visitor_b_emb, t=0) is True  # Different person
```

---

## Phase 6 — FastAPI Backend

**Goal:** Provide a REST API and real-time event stream (SSE) for the web (Next.js) app to consume.

**Dependency:** Phase 3 (DB), Phase 4 (Pipeline callbacks)

### Task 6.1: Project Setup & Base Routes

**Work:**
- Initialize FastAPI app (`api/main.py`)
- Configure CORS (allow Next.js dev server origin)
- Health check endpoint
- Shared dependency management (`api/deps.py`): DB connection, FAISS index, Pipeline state

**Done Criteria:**
- `GET /health` returns 200
- CORS headers are set correctly

### Task 6.2: User Management API

**Work:**
- Implement `api/routes/users.py`:
  - `POST /api/users` — register user (name + face image upload)
    - Detect face in image → extract embedding → register in FAISS + save to DB
  - `GET /api/users` — list registered users
  - `DELETE /api/users/{user_id}` — delete user (remove from both DB and FAISS)
- Pydantic request/response schemas (`api/schemas.py`)

**Done Criteria:**
- Users can be registered via image upload
- Registered users are subsequently recognized by the pipeline
- Deleted users are no longer recognized

**Test:**
```python
def test_register_user(client, test_face_image):
    resp = client.post("/api/users", data={"name": "Alice"},
                       files={"image": test_face_image})
    assert resp.status_code == 201
    assert resp.json()["user_id"] is not None

def test_list_users(client):
    resp = client.get("/api/users")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_delete_user(client):
    user_id = client.post("/api/users", ...).json()["user_id"]
    resp = client.delete(f"/api/users/{user_id}")
    assert resp.status_code == 200
    resp = client.get("/api/users")
    ids = [u["user_id"] for u in resp.json()]
    assert user_id not in ids
```

### Task 6.3: Events API & SSE

**Work:**
- Implement `api/routes/events.py`:
  - `GET /api/events?limit=50&offset=0&type=known|unknown` — event list (paginated)
  - `GET /api/events/stream` — real-time event streaming via Server-Sent Events
- SSE connects to the Pipeline's `on_event` callback (via `asyncio.Queue`)

**Done Criteria:**
- Event listing is correctly paginated
- After SSE connection, the client receives new events as they occur

**Test:**
```python
def test_get_events(client):
    resp = client.get("/api/events?limit=10")
    assert resp.status_code == 200

def test_sse_stream(client):
    with client.stream("GET", "/api/events/stream") as resp:
        trigger_mock_event()
        line = next(resp.iter_lines())
        assert "event" in line
```

### Task 6.4: Photo Serving API

**Work:**
- Implement `api/routes/photos.py`:
  - `GET /api/photos/{filename}` — serve unknown visitor photos
- Serve static files from the `photos/` directory
- Prevent path traversal attacks (validate filenames)

**Done Criteria:**
- Requesting an existing photo returns the image
- Requesting a non-existent file returns 404
- Path manipulations like `../` are blocked

---

## Phase 7 — Web Dashboard (Next.js)

**Goal:** Build a web dashboard providing real-time event monitoring, user management, and an unknown visitor photo gallery.

**Dependency:** Phase 6 complete (API must be running)

### Task 7.1: Project Setup

**Work:**
- Initialize Next.js project (App Router, TypeScript)
- Configure API client (FastAPI server URL)
- Common layout: sidebar (Live Feed / Users / Photos)
- TailwindCSS setup

**Done Criteria:**
- Dev server starts with `npm run dev`
- Base layout and navigation render correctly

### Task 7.2: Live Event Feed Page

**Work:**
- Connect to `/api/events/stream` via SSE for real-time event display
- Each event card: timestamp, name (known) or "Unknown" (unknown), confidence, photo thumbnail (unknown only)
- New events appear at the top (reverse chronological)
- Filter by event type (All / Known / Unknown)

**Done Criteria:**
- SSE connection is maintained and new events appear in real time
- Filters work correctly
- Unknown events display photo thumbnails

### Task 7.3: User Management Page

**Work:**
- Display list of registered users
- User registration form: name input + face photo upload
- User deletion (with confirmation dialog)

**Done Criteria:**
- User registration/deletion works correctly through the API
- Deletion has a confirmation step

### Task 7.4: Unknown Visitor Gallery Page

**Work:**
- Display unknown event photos in a grid layout
- Show timestamp and confidence for each photo
- Date-based filtering/grouping
- Click-to-enlarge photo view

**Done Criteria:**
- Photos are displayed in a grid
- Date filtering works
- Enlarged view works


---

## Phase 8 — Integration & Deployment

**Goal:** Run the full system on Raspberry Pi 5 and configure automatic startup.

**Dependency:** Phases 1–7 all complete

### Task 8.1: Integration Launch Script

**Work:**
- `main.py` (root): full system startup script
  1. Initialize DB
  2. Load FAISS index (or create new one)
  3. Start Camera Pipeline (separate thread/process)
  4. Start FastAPI server (uvicorn)
- Document all required environment variables in `.env.example`:
  ```
  TELEGRAM_BOT_TOKEN=
  TELEGRAM_CHAT_ID=
  DB_PATH=./data/cctv.db
  FAISS_INDEX_PATH=./data/faces.index
  PHOTO_DIR=./data/photos/
  DETECTION_THRESHOLD=0.7
  RECOGNITION_THRESHOLD=0.45
  COOLDOWN_SECONDS=30
  ```

**Done Criteria:**
- The entire system starts with a single command
- Pipeline, API server, and notifications all run concurrently

### Task 8.2: Pi 5 Optimization & Benchmark

**Work:**
- `scripts/benchmark.py`: measure pipeline FPS
  - Measure detection-only / embedding-only / full pipeline separately
- Identify bottlenecks and optimize:
  - Tune ONNX Runtime thread count (`SessionOptions.intra_op_num_threads`)
  - Tune input resolution
  - Frame-skip strategy (run recognition every N frames instead of every frame)

**Done Criteria:**
- Full pipeline runs at 10+ FPS on Pi 5
- Benchmark results are recorded

### Task 8.3: systemd Service Registration

**Work:**
- Write a systemd unit file for automatic startup on boot
- Manage logs via journalctl
- Auto-restart on crash (Restart=on-failure)

**Done Criteria:**
- `sudo systemctl start reachy-mini-cctv` starts the service
- The process auto-restarts if it dies
- Logs are viewable via `journalctl -u reachy-mini-cctv`

---

## Phase 9 — Docker Containerization

**Goal:** Containerize the entire stack (backend + web) with Docker and Docker Compose for reproducible, production-ready deployment. The SQLite database, FAISS index, photos, and ONNX models are persisted via named volumes so that data survives container rebuilds.

**Dependency:** Phases 1–8 complete (can also be started after Phase 6 for iterative development)

### Task 9.1: Backend Dockerfile

**Work:**
- Create `docker/backend.Dockerfile`
- Base image: `python:3.11-slim` (with ARM64 support for Pi 5)
- Install system dependencies: `libgl1`, `libglib2.0-0` (OpenCV), `libsqlite3-0`
- Copy `requirements.txt` and install Python dependencies
- Copy application source (`core/`, `db/`, `camera/`, `notifications/`, `api/`, `scripts/`, `main.py`)
- Set working directory and expose port 8000
- Entrypoint: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- Multi-stage build to keep the final image small (build stage for compiling native deps, runtime stage for running)

**Done Criteria:**
- `docker build -f docker/backend.Dockerfile -t reachy-mini-cctv-backend .` succeeds
- `docker run --rm reachy-mini-cctv-backend` starts the FastAPI server and health check returns 200
- Image size is under 2 GB on ARM64

**Test:**
```bash
docker build -f docker/backend.Dockerfile -t reachy-mini-cctv-backend .
docker run --rm -d -p 8000:8000 --name test-backend reachy-mini-cctv-backend
curl -f http://localhost:8000/health
docker stop test-backend
```

### Task 9.2: Web Dockerfile

**Work:**
- Create `docker/frontend.Dockerfile` (builds the `web/` app)
- Multi-stage build:
  - Stage 1 (`node:24.13.1-alpine`): install deps, run `npm run build`
  - Stage 2 (`node:24.13.1-alpine`): copy build output, run `next start`
- Set `NEXT_PUBLIC_API_URL` as a build arg (default: `http://localhost:8000`)
- Expose port 3000

**Done Criteria:**
- `docker build -f docker/frontend.Dockerfile -t reachy-mini-cctv-web ./web` succeeds
- Container serves the Next.js app on port 3000
- API URL is configurable at build time

**Test:**
```bash
docker build -f docker/frontend.Dockerfile -t reachy-mini-cctv-web ./web \
  --build-arg NEXT_PUBLIC_API_URL=http://backend:8000
docker run --rm -d -p 3000:3000 --name test-web reachy-mini-cctv-web
curl -f http://localhost:3000
docker stop test-web
```

### Task 9.3: Docker Compose Orchestration

**Work:**
- Create `docker-compose.yml` at the project root
- Services:
  - `backend`: builds from `docker/backend.Dockerfile`
    - Volumes: `./data:/app/data` (SQLite DB, FAISS index, photos)
    - Volumes: `./core/models:/app/core/models:ro` (ONNX models, read-only)
    - Environment: loads from `.env`
    - Ports: `8000:8000`
    - Restart policy: `unless-stopped`
    - Device access: map `/dev/video0` or Reachy Mini USB device for camera access (configurable)
  - `web`: builds from `docker/frontend.Dockerfile` (context: `./web`)
    - Depends on: `backend`
    - Ports: `3000:3000`
    - Build args: `NEXT_PUBLIC_API_URL=http://backend:8000`
    - Restart policy: `unless-stopped`
- Named volumes for persistent data
- Network: default bridge network (web → backend via service name)

**Compose file structure:**
```yaml
version: "3.9"

services:
  backend:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - app-data:/app/data
      - ./core/models:/app/core/models:ro
    env_file: .env
    restart: unless-stopped
    # Uncomment for camera access on Pi:
    # devices:
    #   - /dev/video0:/dev/video0

  web:
    build:
      context: ./web
      dockerfile: ../docker/frontend.Dockerfile
      args:
        NEXT_PUBLIC_API_URL: http://backend:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  app-data:
```

**Done Criteria:**
- `docker compose up --build` starts both services
- web app can reach the backend API (health check passes)
- Data persists across `docker compose down` and `docker compose up`
- `docker compose down -v` removes all data (clean slate)

**Test:**
```bash
# Full stack startup
docker compose up --build -d

# Verify backend
curl -f http://localhost:8000/health

# Verify web
curl -f http://localhost:3000

# Verify data persistence
docker compose down
docker compose up -d
curl -f http://localhost:8000/api/users  # Data should still exist

# Clean teardown
docker compose down -v
```

### Task 9.4: Production Hardening

**Work:**
- Add a `.dockerignore` file to exclude unnecessary files (`.git`, `node_modules`, `__pycache__`, `tests/`, `*.pyc`)
- Add health checks to both services in `docker-compose.yml`:
  ```yaml
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
  ```
- Configure logging drivers (json-file with max-size and max-file to prevent disk exhaustion):
  ```yaml
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"
  ```
- Add resource limits for Pi 5 (optional, for safety):
  ```yaml
  deploy:
    resources:
      limits:
        memory: 2G
  ```
- Ensure the backend gracefully handles `SIGTERM` for clean container shutdown
- Document the full deployment workflow in `README.md`

**Done Criteria:**
- `.dockerignore` exists and reduces build context size
- Health checks are configured and `docker compose ps` shows healthy services
- Logs are rotated and do not grow unbounded
- `docker compose restart backend` performs a graceful restart without data loss

---

## Phase Execution Order Summary

```
Phase 1 (Detection) ──→ Phase 2 (Embedding + FAISS) ──→ Phase 4 (Pipeline) ──→ Phase 5 (Telegram)
                                                              ↑                        ↓
Phase 3 (Database)  ─────────────────────────────────────────┘          Phase 8 (Integration)
                                                                              ↑
Phase 6 (FastAPI) ──→ Phase 7 (Web Dashboard) ──────────────────────────────┘
                                                                              ↓
                                                                 Phase 9 (Docker)
```

**Parallelizable segments:**
- Phase 1 + Phase 3: no mutual dependency, can run simultaneously
- Phase 6 + Phase 5: can run simultaneously after Phase 4 is complete
- Phase 7 Tasks (7.2, 7.3, 7.4): each page is independent, can run simultaneously
- Phase 9 can begin after Phase 6 for iterative Docker development, but full completion requires Phase 8

---

## Test Strategy

### Test Fixtures

Prepare test data for use across the project in `tests/fixtures/`:

| File | Purpose |
|---|---|
| `single_face.jpg` | Image containing one face |
| `group.jpg` | Image containing multiple faces |
| `no_face.jpg` | Image with no faces |
| `person_a_1.jpg`, `person_a_2.jpg` | Two different photos of the same person |
| `person_b_1.jpg` | Photo of a different person |
| `blurry_face.jpg` | Blurry face image (for best-frame testing) |
| `test_video.mp4` | Short test video (for pipeline testing) |

### Test Layers

| Layer | Target | Environment |
|---|---|---|
| Unit | Individual classes/functions (Detector, Embedder, Recognizer, Repos) | Anywhere (CI/local) |
| Integration | Pipeline → DB → Notification wiring | Requires model files |
| API | FastAPI endpoints (TestClient) | Requires model files |
| E2E | Camera → Pipeline → DB → API → Dashboard | Pi 5 device only |

### Running Tests

```bash
# Unit + Integration
pytest tests/ -v --ignore=tests/test_e2e.py

# API tests only
pytest tests/test_api.py -v

# E2E (on device only)
pytest tests/test_e2e.py -v
```

### Docker-Based Testing

```bash
# Run tests inside the backend container
docker compose run --rm backend pytest tests/ -v --ignore=tests/test_e2e.py
```
