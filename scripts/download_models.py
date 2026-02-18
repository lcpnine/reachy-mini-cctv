"""
Script to download required ONNX models for face detection and embedding.
Uses Hugging Face Hub for reliable downloads (no 401 with default urllib).
"""
import shutil
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import MODELS_DIR, FACE_DETECTION_MODEL, FACE_EMBEDDING_MODEL


def download_model(repo_id: str, filename: str, destination: Path, description: str) -> bool:
    """Download a file from Hugging Face Hub to the given destination."""
    print(f"Downloading {description}...")
    print(f"  Repo: {repo_id}, file: {filename}")
    print(f"  Destination: {destination}")

    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=MODELS_DIR,
        )
        downloaded = Path(path)
        if downloaded.resolve() != destination.resolve():
            shutil.copy2(downloaded, destination)
            if downloaded != destination:
                downloaded.unlink(missing_ok=True)
        print(f"✓ Downloaded {description} successfully!")
        return True
    except ImportError:
        print("✗ huggingface_hub is required. Run: pip install huggingface_hub")
        return False
    except Exception as e:
        print(f"✗ Error downloading {description}: {e}")
        return False


def main():
    """Download all required models."""
    print("=" * 60)
    print("Reachy Mini CCTV - Model Download Script")
    print("=" * 60)
    print()

    # Ensure models directory exists
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # WePrompt/buffalo_sc: SCRFD det_500m + recognition w600k_mbf (InsightFace-compatible)
    models = [
        {
            "repo_id": "WePrompt/buffalo_sc",
            "filename": "det_500m.onnx",
            "destination": FACE_DETECTION_MODEL,
            "description": "SCRFD-500M Face Detection Model",
        },
        {
            "repo_id": "WePrompt/buffalo_sc",
            "filename": "w600k_mbf.onnx",
            "destination": FACE_EMBEDDING_MODEL,
            "description": "Face Embedding Model (w600k_mbf)",
        },
    ]

    success_count = 0
    for model in models:
        if model["destination"].exists():
            print(f"⚠ {model['description']} already exists at {model['destination']}")
            print("  Skipping download. Delete the file to re-download.")
            success_count += 1
        else:
            if download_model(
                model["repo_id"],
                model["filename"],
                model["destination"],
                model["description"],
            ):
                success_count += 1
        print()

    print("=" * 60)
    if success_count == len(models):
        print(f"✓ All {len(models)} models ready!")
    else:
        print(f"⚠ {success_count}/{len(models)} models ready")
        print("\nManual download (browser or wget/curl):")
        print("  - SCRFD: https://huggingface.co/WePrompt/buffalo_sc/resolve/main/det_500m.onnx")
        print("    Save as: face_detection.onnx")
        print("  - Embedding: https://huggingface.co/WePrompt/buffalo_sc/resolve/main/w600k_mbf.onnx")
        print("    Save as: edgeface_xs_gamma_06.onnx")
        print(f"\nPlace files in: {MODELS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
