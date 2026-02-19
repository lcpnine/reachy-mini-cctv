#!/usr/bin/env python3
"""
Setup models using the InsightFace package.
Downloads the buffalo_l (or buffalo_sc) model pack and copies
the detection and recognition ONNX files into core/models/.

Verification: after copying, checks that the detection model has
multiple outputs (SCRFD) and the embedding model has a single
high-dimensional output.
"""
import shutil
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import FACE_DETECTION_MODEL, FACE_EMBEDDING_MODEL, MODELS_DIR


def verify_detection_model(path: Path) -> bool:
    """Return True if path is a valid SCRFD detection model (6+ outputs)."""
    import onnxruntime as ort
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    return len(sess.get_outputs()) >= 6


def verify_embedding_model(path: Path) -> bool:
    """Return True if path looks like a face embedding model (1 output, ≥128-d)."""
    import onnxruntime as ort
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    if len(sess.get_outputs()) != 1:
        return False
    out_shape = sess.get_outputs()[0].shape
    # Expect something like [1, 512] or [None, 512]
    return len(out_shape) == 2 and (isinstance(out_shape[1], int) and out_shape[1] >= 128)


def main():
    print("=" * 60)
    print("Setting up models from InsightFace package")
    print("=" * 60)
    print()

    try:
        import insightface
        print("✓ InsightFace package found")
    except ImportError:
        print("✗ InsightFace not installed.  Install with:")
        print("    pip install insightface")
        sys.exit(1)

    # This triggers model download to ~/.insightface/models/
    print("\nInitializing FaceAnalysis (downloads models on first run)...")
    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(640, 640))
        print("✓ Models downloaded")
    except Exception as e:
        print(f"✗ FaceAnalysis init failed: {e}")
        sys.exit(1)

    insightface_dir = Path.home() / ".insightface" / "models"
    print(f"\nSearching for ONNX files in {insightface_dir} ...")

    all_onnx = list(insightface_dir.rglob("*.onnx"))
    print(f"Found {len(all_onnx)} .onnx file(s)")

    # Classify each file
    det_candidates = []
    emb_candidates = []

    for p in all_onnx:
        try:
            if verify_detection_model(p):
                det_candidates.append(p)
                print(f"  [DET] {p.name}  ({p.stat().st_size / 1024:.0f} KB)")
            elif verify_embedding_model(p):
                emb_candidates.append(p)
                print(f"  [EMB] {p.name}  ({p.stat().st_size / 1024:.0f} KB)")
            else:
                print(f"  [???] {p.name}  (skipped)")
        except Exception:
            print(f"  [ERR] {p.name}  (failed to load)")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Detection model ----
    print()
    if det_candidates:
        # Prefer the smallest (SCRFD-500M is ~2–3 MB)
        src = min(det_candidates, key=lambda p: p.stat().st_size)
        print(f"Copying detection model: {src.name} → {FACE_DETECTION_MODEL.name}")
        shutil.copy2(src, FACE_DETECTION_MODEL)
        print("✓ Detection model ready")
    else:
        print("⚠ No detection model found among InsightFace files.")
        print("  Run `python scripts/download_models.py` to download directly from HuggingFace.")

    # ---- Embedding model ----
    print()
    if emb_candidates:
        src = min(emb_candidates, key=lambda p: p.stat().st_size)
        print(f"Copying embedding model: {src.name} → {FACE_EMBEDDING_MODEL.name}")
        shutil.copy2(src, FACE_EMBEDDING_MODEL)
        print("✓ Embedding model ready")
    else:
        print("⚠ No embedding model found among InsightFace files.")

    # ---- Final verification ----
    print()
    print("=" * 60)
    import onnxruntime as ort

    all_ok = True
    if FACE_DETECTION_MODEL.exists():
        sess = ort.InferenceSession(str(FACE_DETECTION_MODEL), providers=["CPUExecutionProvider"])
        n_out = len(sess.get_outputs())
        inp = sess.get_inputs()[0]
        print(f"Detection  : input {inp.shape}, {n_out} outputs  ✓" if n_out >= 6
              else f"Detection  : input {inp.shape}, {n_out} outputs  ⚠ (expected ≥6)")
        if n_out < 6:
            all_ok = False
    else:
        print("Detection  : MISSING")
        all_ok = False

    if FACE_EMBEDDING_MODEL.exists():
        sess = ort.InferenceSession(str(FACE_EMBEDDING_MODEL), providers=["CPUExecutionProvider"])
        out = sess.get_outputs()[0]
        print(f"Embedding  : input {sess.get_inputs()[0].shape}, output {out.shape}  ✓")
    else:
        print("Embedding  : MISSING")
        all_ok = False

    if all_ok:
        print("\n✓ Setup complete — both models verified!")
    else:
        print("\n⚠ Setup incomplete. See notes above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
