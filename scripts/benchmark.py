#!/usr/bin/env python3
"""
Benchmark script to measure pipeline performance on Raspberry Pi 5.
Measures FPS for detection, embedding, and full pipeline.
"""
import sys
import time
import cv2
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.detector import FaceDetector
from core.embedder import FaceEmbedder
from core.recognizer import FaceRecognizer
from camera.capture import create_camera


def measure_fps(func, iterations: int = 100, warmup: int = 10):
    """
    Measure FPS for a given function.

    Args:
        func: Function to benchmark
        iterations: Number of iterations to run
        warmup: Number of warmup iterations

    Returns:
        Average FPS
    """
    # Warmup
    for _ in range(warmup):
        func()

    # Measure
    start_time = time.time()
    for _ in range(iterations):
        func()
    elapsed = time.time() - start_time

    fps = iterations / elapsed
    avg_time = (elapsed / iterations) * 1000  # ms

    return fps, avg_time


def benchmark_detector(detector: FaceDetector, test_image: np.ndarray):
    """Benchmark face detection."""
    print("\n" + "=" * 60)
    print("Benchmarking Face Detection")
    print("=" * 60)

    def detect():
        return detector.detect(test_image)

    fps, avg_time = measure_fps(detect, iterations=100)

    print(f"FPS:           {fps:.2f}")
    print(f"Avg Time:      {avg_time:.2f} ms")
    print(f"Input Size:    {test_image.shape[:2]}")


def benchmark_embedder(embedder: FaceEmbedder, face_crop: np.ndarray):
    """Benchmark face embedding extraction."""
    print("\n" + "=" * 60)
    print("Benchmarking Face Embedding")
    print("=" * 60)

    def embed():
        return embedder.embed(face_crop)

    fps, avg_time = measure_fps(embed, iterations=100)

    print(f"FPS:           {fps:.2f}")
    print(f"Avg Time:      {avg_time:.2f} ms")
    print(f"Input Size:    {face_crop.shape[:2]}")


def benchmark_recognizer(recognizer: FaceRecognizer, embedding: np.ndarray):
    """Benchmark face recognition search."""
    print("\n" + "=" * 60)
    print("Benchmarking Face Recognition")
    print("=" * 60)

    def recognize():
        return recognizer.recognize(embedding)

    fps, avg_time = measure_fps(recognize, iterations=1000)

    print(f"FPS:           {fps:.2f}")
    print(f"Avg Time:      {avg_time:.2f} ms")
    print(f"Index Size:    {recognizer.get_embedding_count()} embeddings")


def benchmark_full_pipeline(
    detector: FaceDetector,
    embedder: FaceEmbedder,
    recognizer: FaceRecognizer,
    test_image: np.ndarray
):
    """Benchmark the full recognition pipeline."""
    print("\n" + "=" * 60)
    print("Benchmarking Full Pipeline (Detection + Embedding + Recognition)")
    print("=" * 60)

    def pipeline():
        # Detect
        boxes = detector.detect(test_image)
        if not boxes:
            return None

        # Use first detection
        bbox = boxes[0]
        face_crop = test_image[bbox.y1:bbox.y2, bbox.x1:bbox.x2]

        # Embed
        embedding = embedder.embed(face_crop)
        if embedding is None:
            return None

        # Recognize
        result = recognizer.recognize(embedding)
        return result

    fps, avg_time = measure_fps(pipeline, iterations=50)

    print(f"FPS:           {fps:.2f}")
    print(f"Avg Time:      {avg_time:.2f} ms")
    print(f"Input Size:    {test_image.shape[:2]}")


def benchmark_camera(camera_source: str, duration: int = 10):
    """Benchmark camera frame capture."""
    print("\n" + "=" * 60)
    print("Benchmarking Camera Capture")
    print("=" * 60)

    camera = create_camera(camera_source)
    camera.start()

    frame_count = 0
    start_time = time.time()
    end_time = start_time + duration

    print(f"Capturing frames for {duration} seconds...")

    while time.time() < end_time:
        frame = camera.read()
        if frame is not None:
            frame_count += 1

    elapsed = time.time() - start_time
    fps = frame_count / elapsed

    camera.stop()

    print(f"FPS:           {fps:.2f}")
    print(f"Frames:        {frame_count}")
    print(f"Duration:      {elapsed:.2f} s")


def create_test_image(width: int = 640, height: int = 480):
    """Create a synthetic test image with a face-like pattern."""
    # Create a blank image
    img = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

    # Draw a simple face-like pattern (oval + eyes + mouth)
    center = (width // 2, height // 2)
    axes = (100, 120)

    # Face oval
    cv2.ellipse(img, center, axes, 0, 0, 360, (255, 220, 180), -1)

    # Eyes
    cv2.circle(img, (center[0] - 40, center[1] - 30), 15, (0, 0, 0), -1)
    cv2.circle(img, (center[0] + 40, center[1] - 30), 15, (0, 0, 0), -1)

    # Mouth
    cv2.ellipse(img, (center[0], center[1] + 30), (40, 20), 0, 0, 180, (180, 50, 50), -1)

    return img


def main():
    """Main benchmark function."""
    print("=" * 60)
    print("Reachy Mini CCTV - Performance Benchmark")
    print("=" * 60)
    print()

    # System info
    import platform
    print(f"Platform:      {platform.system()} {platform.release()}")
    print(f"Processor:     {platform.processor()}")
    print(f"Python:        {sys.version.split()[0]}")
    print()

    # Initialize components
    print("Initializing components...")
    detector = FaceDetector()
    embedder = FaceEmbedder()
    recognizer = FaceRecognizer()

    # Add some dummy embeddings to the recognizer for realistic benchmarks
    print("Creating test data...")
    for i in range(10):
        dummy_embedding = np.random.randn(512).astype(np.float32)
        dummy_embedding /= np.linalg.norm(dummy_embedding)
        recognizer.register(i, dummy_embedding)

    # Create test image
    test_image = create_test_image()

    # Get a face crop for embedding benchmark
    boxes = detector.detect(test_image)
    if boxes:
        bbox = boxes[0]
        face_crop = test_image[bbox.y1:bbox.y2, bbox.x1:bbox.x2]
    else:
        # Fallback: use center crop
        h, w = test_image.shape[:2]
        face_crop = test_image[h//4:3*h//4, w//4:3*w//4]

    # Get an embedding for recognition benchmark
    embedding = embedder.embed(face_crop)

    # Run benchmarks
    benchmark_detector(detector, test_image)
    benchmark_embedder(embedder, face_crop)

    if embedding is not None:
        benchmark_recognizer(recognizer, embedding)
        benchmark_full_pipeline(detector, embedder, recognizer, test_image)
    else:
        print("\n⚠ Skipping recognition and full pipeline benchmarks (no embedding)")

    # Camera benchmark (optional, skip in headless environments)
    try:
        from core.config import CAMERA_SOURCE
        if CAMERA_SOURCE != "reachy":  # Skip if using Reachy SDK
            benchmark_camera(CAMERA_SOURCE, duration=5)
    except Exception as e:
        print(f"\n⚠ Camera benchmark skipped: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Benchmark Complete")
    print("=" * 60)
    print()
    print("Target FPS for real-time operation: 10+ FPS")
    print("For optimal performance on Raspberry Pi 5:")
    print("  - Use lower resolution input (320x240 or 640x480)")
    print("  - Consider frame skipping (process every Nth frame)")
    print("  - Adjust detection confidence threshold")
    print("=" * 60)


if __name__ == "__main__":
    main()
