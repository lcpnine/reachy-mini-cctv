#!/usr/bin/env python3
"""
Script to download required ONNX models for face detection and embedding.
Uses Hugging Face Hub for reliable downloads.

Models (from InsightFace buffalo_sc bundle):
  - det_500m.onnx     → SCRFD-500M face detection (input 640×640, 9 outputs)
  - w600k_mbf.onnx    → MobileFaceNet face embedding (input 112×112, 512-d output)
"""
import shutil
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import FACE_DETECTION_MODEL, FACE_EMBEDDING_MODEL, MODELS_DIR

# HuggingFace repo that hosts InsightFace buffalo_sc model pack
REPO_ID = "WePrompt/buffalo_sc"

MODELS = [
    {
        "hf_filename": "det_500m.onnx",
        "destination": FACE_DETECTION_MODEL,
        "description": "SCRFD-500M Face Detection",
        "expected_outputs_min": 6,  # 6 (no kps) or 9 (with kps)
    },
    {
        "hf_filename": "w600k_mbf.onnx",
        "destination": FACE_EMBEDDING_MODEL,
        "description": "MobileFaceNet Face Embedding (w600k_mbf)",
        "expected_outputs_min": 1,
    },
]


def download_model(repo_id: str, filename: str, destination: Path, description: str) -> bool:
    """Download a file from Hugging Face Hub to the given destination."""
    print(f"Downloading {description}...")
    print(f"  Repo: {repo_id}, file: {filename}")
    print(f"  Destination: {destination}")

    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(repo_id=repo_id, filename=filename)
        downloaded = Path(path)
        shutil.copy2(downloaded, destination)
        print(f"  ✓ Downloaded successfully ({destination.stat().st_size / 1024:.0f} KB)")
        return True
    except ImportError:
        print("  ✗ huggingface_hub is required. Run: pip install huggingface_hub")
        return False
    except Exception as e:
        print(f"  ✗ Download error: {e}")
        return False


def verify_model(path: Path, description: str, expected_outputs_min: int) -> bool:
    """Verify a model loads correctly with ONNX Runtime."""
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        inputs = [(i.name, i.shape) for i in sess.get_inputs()]
        outputs = [(o.name, o.shape) for o in sess.get_outputs()]
        print(f"  Verification — {description}:")
        print(f"    Inputs:  {inputs}")
        print(f"    Outputs: {len(outputs)} tensors")
        for name, shape in outputs:
            print(f"      {name}: {shape}")

        if len(outputs) < expected_outputs_min:
            print(f"  ⚠ Expected at least {expected_outputs_min} outputs, got {len(outputs)}")
            print(f"    This may be the WRONG model file!")
            return False

        print(f"  ✓ Model verified OK")
        return True
    except Exception as e:
        print(f"  ✗ Verification failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Reachy Mini CCTV — Model Download & Verify")
    print("=" * 60)
    print()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0

    for model in MODELS:
        dest: Path = model["destination"]
        desc: str = model["description"]

        if dest.exists():
            print(f"[{desc}] File exists at {dest}")
            ok = verify_model(dest, desc, model["expected_outputs_min"])
            if ok:
                success_count += 1
                print()
                continue
            else:
                print(f"  Re-downloading (verification failed)...")
                dest.unlink()

        if download_model(REPO_ID, model["hf_filename"], dest, desc):
            if verify_model(dest, desc, model["expected_outputs_min"]):
                success_count += 1
        print()

    print("=" * 60)
    if success_count == len(MODELS):
        print(f"✓ All {len(MODELS)} models ready and verified!")
    else:
        print(f"⚠ {success_count}/{len(MODELS)} models ready.")
        print()
        print("Manual download (if HF Hub fails):")
        print(f"  wget -O {FACE_DETECTION_MODEL} \\")
        print(f"    https://huggingface.co/{REPO_ID}/resolve/main/det_500m.onnx")
        print(f"  wget -O {FACE_EMBEDDING_MODEL} \\")
        print(f"    https://huggingface.co/{REPO_ID}/resolve/main/w600k_mbf.onnx")
    print("=" * 60)


if __name__ == "__main__":
    main()
