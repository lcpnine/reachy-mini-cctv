"""
Setup models using the InsightFace package.
This is the easiest way to obtain the required ONNX models.
"""
import sys
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import MODELS_DIR, FACE_DETECTION_MODEL, FACE_EMBEDDING_MODEL


def main():
    print("=" * 60)
    print("Setting up models from InsightFace package")
    print("=" * 60)
    print()

    # Check if insightface is installed
    try:
        import insightface
        print("✓ InsightFace package found")
    except ImportError:
        print("✗ InsightFace package not found")
        print("\nPlease install it:")
        print("  pip install insightface")
        sys.exit(1)

    # Initialize FaceAnalysis (this downloads models automatically)
    print("\nInitializing FaceAnalysis...")
    print("This will download models to ~/.insightface/models/")
    print("(This may take a few minutes on first run)")
    print()

    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        print("✓ Models downloaded and initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing FaceAnalysis: {e}")
        sys.exit(1)

    # Find the model files in InsightFace cache
    insightface_dir = Path.home() / ".insightface" / "models"

    print(f"\nSearching for models in: {insightface_dir}")

    # Look for SCRFD detection model
    detection_models = list(insightface_dir.rglob("scrfd*.onnx")) + \
                      list(insightface_dir.rglob("*det*.onnx"))

    # Look for recognition/embedding models
    embedding_models = list(insightface_dir.rglob("*w600k*.onnx")) + \
                      list(insightface_dir.rglob("*arcface*.onnx")) + \
                      list(insightface_dir.rglob("*recognition*.onnx"))

    print(f"Found {len(detection_models)} detection model(s)")
    print(f"Found {len(embedding_models)} embedding model(s)")
    print()

    # Copy models to our models directory
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if detection_models:
        src = detection_models[0]
        print(f"Copying detection model:")
        print(f"  From: {src}")
        print(f"  To:   {FACE_DETECTION_MODEL}")
        shutil.copy2(src, FACE_DETECTION_MODEL)
        print("✓ Detection model copied")
    else:
        print("⚠ No detection model found")

    print()

    if embedding_models:
        src = embedding_models[0]
        print(f"Copying embedding model:")
        print(f"  From: {src}")
        print(f"  To:   {FACE_EMBEDDING_MODEL}")
        shutil.copy2(src, FACE_EMBEDDING_MODEL)
        print("✓ Embedding model copied")
    else:
        print("⚠ No embedding model found")

    print()
    print("=" * 60)

    # Verify models exist
    if FACE_DETECTION_MODEL.exists() and FACE_EMBEDDING_MODEL.exists():
        print("✓ Setup complete! Both models are ready.")

        # Show model info
        import onnxruntime as ort
        print("\nModel Information:")
        print("-" * 60)

        det_session = ort.InferenceSession(str(FACE_DETECTION_MODEL))
        print(f"Detection model:")
        print(f"  Input: {det_session.get_inputs()[0].shape}")
        print(f"  Outputs: {len(det_session.get_outputs())}")

        emb_session = ort.InferenceSession(str(FACE_EMBEDDING_MODEL))
        print(f"\nEmbedding model:")
        print(f"  Input: {emb_session.get_inputs()[0].shape}")
        print(f"  Output: {emb_session.get_outputs()[0].shape}")

    else:
        print("⚠ Setup incomplete. Please check errors above.")
        print("\nYou may need to manually copy the models from:")
        print(f"  {insightface_dir}")
        print("To:")
        print(f"  {MODELS_DIR}")

    print("=" * 60)


if __name__ == "__main__":
    main()
