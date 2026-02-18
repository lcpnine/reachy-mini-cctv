# Architecture & Technology Stack

This document explains the technology choices behind the Reachy Mini CCTV face recognition system, including alternatives considered and the reasoning behind each decision.

---

## System Overview

```
[Reachy Mini Camera]
    → OpenCV           — frame capture at 30 FPS
    → Face Detection   — locate faces in the frame
    → Crop + Resize    — normalize to 112×112
    → Face Embedding   — extract 512-dim feature vector
    → FAISS Search     — cosine similarity lookup
    → SQLite           — fetch user metadata by ID
    → Output           — recognition result / event trigger
```

The entire pipeline runs **on-device** on the Raspberry Pi 5 inside the Reachy Mini. No external server is required for inference.

---

## 1. Face Detection

**Chosen: MediaPipe BlazeFace (Short Range)**

| Model | Size | Pi 5 FPS (est.) | Accuracy | Notes |
|---|---|---|---|---|
| **MediaPipe BlazeFace** ✅ | ~230 KB | 40+ | 98.6% AP | Google-maintained, TFLite-native |
| OpenCV Haar Cascade | ~930 KB | 60+ | Low | High false-positive rate |
| YOLOv8n-face | ~6 MB | ~12 (CPU) | mAP50 94.6% (Easy) | Too heavy for CPU-only Pi 5 |
| SCRFD-500M (InsightFace) | ~2 MB | 30+ | WIDERFace 90%+ | Good alternative; ONNX-ready |

**Why:** BlazeFace is a purpose-built face detector from Google Research ([Bazarevsky et al., 2019](https://arxiv.org/abs/1907.05047)). The short-range TFLite model is only ~230 KB with ~0.13M parameters, making it exceptionally lightweight. It was designed for sub-millisecond inference on mobile CPUs — the original paper reports ~2.94 ms per frame on a Pixel 1 CPU. On the Pi 5's Cortex-A76 cores, 40+ FPS is highly plausible even without GPU acceleration.

The model is accessible through Google's [MediaPipe Face Detection](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector) solution or as a standalone TFLite model. For our ONNX-based pipeline, we convert the TFLite model to ONNX or use SCRFD-500M from InsightFace as a drop-in alternative that ships natively in ONNX format.

**Alternatives considered:**

- **OpenCV Haar Cascade** is faster but produces too many false positives and cannot handle profile or angled faces — unreliable for a security application.
- **YOLOv8n-face** offers high accuracy (mAP50 94.6% on WIDERFace-Easy) but benchmarks at only ~12 FPS on Pi 5 CPU at 640×640 resolution, leaving insufficient headroom for the embedding and search stages.
- **SCRFD-500M** from InsightFace is a strong alternative (~2 MB, ONNX-native, WIDERFace 90%+ on Easy) and remains a viable swap if MediaPipe's TFLite-to-ONNX conversion proves problematic.

---

## 2. Face Embedding

**Chosen: [EdgeFace (edgeface_xs_gamma_06)](https://github.com/otroshi/edgeface)**

| Model | Parameters | Embedding Dim | LFW Accuracy | Notes |
|---|---|---|---|---|
| **EdgeFace-xs** ✅ | 1.77 M | 512 | 99.73% | Winner of IJCB 2023 compact track |
| FaceNet (InceptionResNetV1) | ~23 M | 128 (original) / 512 (VGGFace2) | 99.65% | 13× larger; 512-dim only in VGGFace2 variant |
| ArcFace / buffalo_l (IResNet-50) | ~43.8 M | 512 | 99.83% | 25× larger; too heavy for Pi 5 |
| MobileFaceNet | ~1.0 M | 128 (default) | 99.55% | Viable lightweight alternative |

**Why:** EdgeFace was explicitly designed for edge deployment and won the compact track of the IJCB 2023 Efficient Face Recognition Competition. At 1.77M parameters it is over 13× smaller than FaceNet and nearly 25× smaller than ArcFace (buffalo_l), while still achieving 99.73% accuracy on LFW — well within the accuracy requirement for a small, controlled user base (tens of people).

The model is published by Idiap Research Institute ([arXiv:2307.01838](https://arxiv.org/abs/2307.01838), IEEE T-BIOM 2024) and available on both [GitHub](https://github.com/otroshi/edgeface) and [Hugging Face](https://huggingface.co/Idiap/EdgeFace-Base). Pre-trained ONNX checkpoints are provided, making integration with our inference runtime straightforward.

**Alternatives considered:**

- **FaceNet** (InceptionResNetV1) achieves comparable accuracy but at ~23M parameters it would introduce significant latency and memory pressure on the Pi 5. Note: FaceNet's original paper uses 128-dim embeddings; the commonly-cited 512-dim variant comes from David Sandberg's VGGFace2 re-training. The popular `facenet-pytorch` library by Tim Esler and `py-feat` both wrap this model.
- **ArcFace / buffalo_l** from InsightFace uses an IResNet-50 backbone with ~43.8M parameters (not ~34M as sometimes cited — IResNet-50 differs from standard ResNet-50). Running a model this size on a Pi 5 would introduce unacceptable latency.
- **MobileFaceNet** (~1.0M parameters, 128-dim default) is another edge-optimized option that could work, but EdgeFace achieves higher LFW accuracy with native ONNX support and better documentation.

---

## 3. Inference Runtime

**Chosen: ONNX Runtime**

| Runtime | Notes |
|---|---|
| **ONNX Runtime** ✅ | ARM64 wheels available on PyPI; NEON SIMD optimization |
| TFLite | Good for TensorFlow-native models; limited to TF ecosystem |
| PyTorch Mobile | Higher memory overhead; ONNX conversion preferred |

**Why:** Both the detection and embedding models are exported to ONNX format and run through ONNX Runtime. ONNX Runtime provides official ARM64 support with NEON SIMD optimization, and pre-built wheels are available on PyPI for straightforward installation on the Pi 5.

Benchmarks show ONNX Runtime delivers approximately **1.5–3× speedup** over naive PyTorch eager-mode inference on CPU for models in this size range. While not as dramatic as some claimed speedups (which apply to GPU-accelerated LLM workloads with INT4 quantization), this is still a meaningful improvement on a CPU-constrained device.

ONNX also acts as a neutral interchange format — if we need to swap the detection or embedding model in the future, any model exportable to ONNX integrates without changes to the surrounding code.

---

## 4. Vector Search

**Chosen: FAISS `IndexFlatIP`**

| Library | Scale | RAM | Live Updates | Notes |
|---|---|---|---|---|
| **FAISS IndexFlatIP** ✅ | Small–large | Low | Yes | Exact inner-product search |
| FAISS IVF+PQ | Large | Very low | Yes | Approximate; for 10k+ vectors |
| HNSWlib | Small–medium | High | Yes | Fast queries, slower insertions |
| Annoy | Small | Low | No | Requires full index rebuild on update |
| sqlite-vec | Small | Very low | Yes | SQLite extension; zero dependencies |

**Why:** With tens of registered users, the face index is tiny. `IndexFlatIP` performs exact inner-product search (equivalent to cosine similarity on L2-normalized 512-dim vectors) with sub-millisecond query latency at this scale. There is no need for approximate search indexes like IVF+PQ, which trade accuracy for speed only when the index contains tens of thousands of vectors or more.

If the system ever scales to thousands of users, switching to `IndexIVFPQ` is straightforward and requires no changes to the surrounding code.

**Note on HNSWlib:** Listed as "Awkward" for updates in earlier versions of this document — HNSWlib does support element addition after index construction, though deletion requires workarounds. The characterization has been corrected above.

---

## 5. Metadata Database

**Chosen: SQLite (WAL mode)**

| Database | Notes |
|---|---|
| **SQLite** ✅ | Embedded, zero server overhead, 200k+ reads/sec on ARM Linux |
| PostgreSQL | Needed only for multi-writer or multi-camera setups |
| Redis | Overkill; no persistence benefit here |

**Why:** FAISS stores the embedding vectors and returns a `user_id` on a match. SQLite stores the human-readable metadata — name, registration date, and any additional fields — keyed on that `user_id`. This separation keeps each store doing what it does best.

SQLite is a natural fit for this deployment:

- **No server process.** It runs in-process as a single `.db` file, consuming no additional RAM or CPU on the Pi.
- **Zero dependencies.** Python's `sqlite3` module is part of the standard library.
- **Read-heavy workload.** Face recognition involves many reads (metadata lookup per recognition event) and very few writes (only when registering or removing a user). SQLite handles this ratio with ease. Benchmarks show 200k+ simple reads/sec on ARM Linux servers; Pi 5 performance will be somewhat lower for complex queries but more than sufficient for key lookups on small tables.
- **Simple backup.** The entire database is a single file — copying it is sufficient for backup or migration.

One configuration change is required to support concurrent reads during dashboard/remote access:

```python
import sqlite3

conn = sqlite3.connect("cctv.db")
conn.execute("PRAGMA journal_mode=WAL;")    # Allow concurrent reads and writes
conn.execute("PRAGMA synchronous=NORMAL;")  # Balance between speed and durability
```

WAL (Write-Ahead Logging) mode allows read queries from the remote dashboard to proceed without being blocked by recognition-event writes, and vice versa. Per SQLite's official documentation: readers do not block writers and a writer does not block readers in WAL mode.

**When to reconsider:** If this system expands to multiple cameras writing simultaneously, or moves to a centralized server setup, PostgreSQL would be the natural migration target. At that point, the FAISS index would also likely move to a dedicated vector database. Neither change is necessary for the current single-device deployment.

---

## Schema

```sql
-- User registry
CREATE TABLE users (
    user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT    NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Recognition event log
CREATE TABLE events (
    event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(user_id),
    confidence REAL,
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

The `user_id` in `users` corresponds 1-to-1 with the FAISS index position, linking vector search results to human-readable metadata.

---

## Sources & Verification

| Component | Primary Source |
|---|---|
| MediaPipe BlazeFace | [arXiv:1907.05047](https://arxiv.org/abs/1907.05047), [Google AI Edge docs](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector) |
| EdgeFace | [arXiv:2307.01838](https://arxiv.org/abs/2307.01838), [GitHub](https://github.com/otroshi/edgeface), [HuggingFace](https://huggingface.co/Idiap/EdgeFace-Base) |
| FaceNet | [facenet-pytorch](https://github.com/timesler/facenet-pytorch), [davidsandberg/facenet](https://github.com/davidsandberg/facenet) |
| ArcFace / buffalo_l | [InsightFace model zoo](https://github.com/deepinsight/insightface/blob/master/model_zoo/README.md) |
| MobileFaceNet | [arXiv:1804.07573](https://arxiv.org/abs/1804.07573) |
| YOLOv8n-face | [lindevs/yolov8-face](https://github.com/lindevs/yolov8-face) |
| ONNX Runtime | [PyPI ARM64 wheels](https://pypi.org/project/onnxruntime/), [Microsoft docs](https://onnxruntime.ai/) |
| FAISS | [facebookresearch/faiss](https://github.com/facebookresearch/faiss) |
| HNSWlib | [nmslib/hnswlib](https://github.com/nmslib/hnswlib) |
| Annoy | [spotify/annoy](https://github.com/spotify/annoy) |
| sqlite-vec | [asg017/sqlite-vec](https://github.com/asg017/sqlite-vec) |
