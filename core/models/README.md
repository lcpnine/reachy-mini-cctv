# ONNX Models for Reachy Mini CCTV

This directory contains the ONNX models required for face detection and recognition.

## Required Models

### 1. Face Detection Model
- **File:** `face_detection.onnx`
- **Model:** SCRFD-500M-BNKPS (from InsightFace `buffalo_sc` pack)
- **Size:** ~2.5 MB
- **Input:** `[1, 3, 640, 640]` (RGB, float32)
- **Outputs:** 9 tensors (scores + bboxes + keypoints for strides 8, 16, 32)

### 2. Face Embedding Model
- **File:** `edgeface_xs_gamma_06.onnx`
- **Model:** MobileFaceNet w600k_mbf (from InsightFace `buffalo_sc` pack)
- **Size:** ~2 MB
- **Input:** `[1, 3, 112, 112]` (RGB, float32)
- **Output:** `[1, 512]` — 512-dimensional embedding

## Download Methods

### Option A: Automated download (Recommended)
```bash
python scripts/download_models.py
```
This downloads from HuggingFace and **verifies** each model has the expected output format.

### Option B: Via InsightFace package
```bash
pip install insightface
python scripts/setup_models_from_insightface.py
```
This triggers InsightFace's built-in model download and then copies + verifies the correct files.

### Option C: Manual download
```bash
# Detection model (SCRFD-500M)
wget -O core/models/face_detection.onnx \
  https://huggingface.co/WePrompt/buffalo_sc/resolve/main/det_500m.onnx

# Embedding model (MobileFaceNet w600k)
wget -O core/models/edgeface_xs_gamma_06.onnx \
  https://huggingface.co/WePrompt/buffalo_sc/resolve/main/w600k_mbf.onnx
```

## Verification

After placing models, verify they are correct:

```bash
python3 -c "
import onnxruntime as ort

# Detection model — must have 6+ outputs (SCRFD multi-stride)
det = ort.InferenceSession('core/models/face_detection.onnx')
print(f'Detection:  input={det.get_inputs()[0].shape}  outputs={len(det.get_outputs())}')
assert len(det.get_outputs()) >= 6, 'ERROR: detection model has too few outputs — wrong file?'

# Embedding model — must have 1 output with 512-d
emb = ort.InferenceSession('core/models/edgeface_xs_gamma_06.onnx')
print(f'Embedding:  input={emb.get_inputs()[0].shape}  output={emb.get_outputs()[0].shape}')
assert len(emb.get_outputs()) == 1, 'ERROR: embedding model has unexpected outputs'

print('✓ Both models verified OK')
"
```

**Key check:** The detection model must have **≥ 6 outputs**. If it only has 1–2 outputs, it's likely an embedding model placed in the wrong slot.

## Model Performance on Raspberry Pi 5

Expected inference times:
- **SCRFD-500M (640×640):** ~50–80 ms per frame
- **MobileFaceNet w600k:** ~15–25 ms per face

Total pipeline: ~10–15 FPS with frame skipping.

## License Notes

- SCRFD models: Apache 2.0 License
- MobileFaceNet / InsightFace models: Apache 2.0 License (non-commercial variants may differ)
- Check individual model licenses before commercial use
