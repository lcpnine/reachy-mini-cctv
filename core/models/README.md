# ONNX Models for Reachy Mini CCTV

This directory contains the ONNX models required for face detection and recognition.

## Required Models

### 1. Face Detection Model
**File:** `face_detection.onnx`
**Recommended:** SCRFD-500M-BNKPS
**Size:** ~2.5 MB

#### Option A: Download from InsightFace (Recommended)
```bash
# Clone InsightFace repository
git clone https://github.com/deepinsight/insightface.git
cd insightface/detection/scrfd

# Download the model using their tools
# Or manually download from their releases
```

#### Option B: Export from InsightFace Python Package
```bash
pip install insightface
python << EOF
from insightface.app import FaceAnalysis
app = FaceAnalysis(providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
# Model will be cached in ~/.insightface/models/
# Copy scrfd_500m_bnkps.onnx to this directory
EOF
```

#### Option C: Download from ONNX Model Zoo
Visit: https://github.com/onnx/models

### 2. Face Embedding Model
**File:** `edgeface_xs_gamma_06.onnx`
**Model:** EdgeFace-XS
**Size:** ~1 MB

#### Option A: Download from InsightFace
```bash
# Similar to detection model
# Available in InsightFace model zoo
```

#### Option B: Use Alternative Embedding Models
You can use other face recognition models such as:
- MobileFaceNet
- ArcFace variants
- Any model that outputs 512-dimensional embeddings

Just update the `FACE_EMBEDDING_MODEL` path in `core/config.py`.

## Alternative Models

### For Face Detection:
- **YuNet** (OpenCV DNN)
- **MediaPipe BlazeFace** (requires TFLite to ONNX conversion)
- **Ultra-Light-Fast-Generic-Face-Detector** (very lightweight)

### For Face Embedding:
- **MobileFaceNet** (~1MB, good for edge devices)
- **ArcFace-R50** (larger but more accurate)

## Verification

After placing the models in this directory, verify they load correctly:

```bash
cd /path/to/reachy-mini-cctv
python << EOF
import onnxruntime as ort
from core.config import FACE_DETECTION_MODEL, FACE_EMBEDDING_MODEL

# Test detection model
det_session = ort.InferenceSession(str(FACE_DETECTION_MODEL))
print(f"Detection model loaded successfully")
print(f"Input: {det_session.get_inputs()[0].shape}")

# Test embedding model
emb_session = ort.InferenceSession(str(FACE_EMBEDDING_MODEL))
print(f"Embedding model loaded successfully")
print(f"Input: {emb_session.get_inputs()[0].shape}")
EOF
```

## Quick Start with Pre-trained Models

For development and testing, you can use the InsightFace Python package which automatically downloads models:

```bash
pip install insightface onnxruntime
python scripts/setup_models_from_insightface.py
```

## License Notes

- SCRFD models: Apache 2.0 License
- EdgeFace models: Apache 2.0 License
- Please check individual model licenses before commercial use

## Model Performance on Raspberry Pi 5

Expected inference times:
- **SCRFD-500M**: ~50-80ms per frame
- **EdgeFace-XS**: ~15-25ms per face

Total pipeline: ~10-15 FPS with optimization
