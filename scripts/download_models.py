"""
Script to download required ONNX models for face detection and embedding.
"""
import os
import sys
import urllib.request
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import MODELS_DIR, FACE_DETECTION_MODEL, FACE_EMBEDDING_MODEL


def download_file(url: str, destination: Path, description: str):
    """Download a file with progress indication."""
    print(f"Downloading {description}...")
    print(f"URL: {url}")
    print(f"Destination: {destination}")

    try:
        def progress_hook(count, block_size, total_size):
            percent = int(count * block_size * 100 / total_size)
            sys.stdout.write(f"\rProgress: {percent}%")
            sys.stdout.flush()

        urllib.request.urlretrieve(url, destination, progress_hook)
        print(f"\n✓ Downloaded {description} successfully!")
        return True
    except Exception as e:
        print(f"\n✗ Error downloading {description}: {e}")
        return False


def main():
    """Download all required models."""
    print("=" * 60)
    print("Reachy Mini CCTV - Model Download Script")
    print("=" * 60)
    print()

    # Ensure models directory exists
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Model URLs (using ONNX model zoo and HuggingFace)
    # Note: These models need to be downloaded manually or via model-specific tools
    # For now, we'll use direct links where available
    models = [
        {
            "url": "https://huggingface.co/onnx-community/scrfd/resolve/main/scrfd_500m_bnkps.onnx",
            "destination": FACE_DETECTION_MODEL,
            "description": "SCRFD-500M Face Detection Model"
        },
        {
            "url": "https://huggingface.co/onnx-community/edgeface/resolve/main/edgeface_xs_gamma_06.onnx",
            "destination": FACE_EMBEDDING_MODEL,
            "description": "EdgeFace-XS Face Embedding Model"
        }
    ]

    success_count = 0
    for model in models:
        if model["destination"].exists():
            print(f"⚠ {model['description']} already exists at {model['destination']}")
            print("  Skipping download. Delete the file to re-download.")
            success_count += 1
        else:
            if download_file(model["url"], model["destination"], model["description"]):
                success_count += 1
        print()

    print("=" * 60)
    if success_count == len(models):
        print(f"✓ All {len(models)} models ready!")
    else:
        print(f"⚠ {success_count}/{len(models)} models ready")
        print("\nNote: If downloads fail, you can manually download the models:")
        for model in models:
            print(f"  - {model['description']}: {model['url']}")
        print(f"\nPlace them in: {MODELS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
