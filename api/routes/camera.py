"""
Camera stream API - MJPEG live feed from Reachy's camera.
"""
import asyncio
import cv2
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from camera.frame_buffer import get as get_latest_frame

router = APIRouter()


def _encode_jpeg(frame) -> bytes:
    """Encode BGR numpy array to JPEG bytes."""
    ret, buf = cv2.imencode(".jpg", frame)
    if not ret:
        return b""
    return buf.tobytes()


async def _generate_mjpeg():
    """Async generator yielding MJPEG frames."""
    boundary = "frame"
    no_frame_count = 0
    max_no_frame = 100  # ~5 sec at 20Hz check rate

    while True:
        frame = get_latest_frame()
        if frame is not None:
            no_frame_count = 0
            jpeg = _encode_jpeg(frame)
            if jpeg:
                yield (
                    f"--{boundary}\r\n"
                    f"Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(jpeg)}\r\n\r\n"
                ).encode() + jpeg + b"\r\n"
        else:
            no_frame_count += 1
            if no_frame_count >= max_no_frame:
                break
        await asyncio.sleep(0.05)  # ~20 FPS max


@router.get("/stream")
async def stream_camera():
    """
    MJPEG stream of the camera feed.
    Use in img tag: <img src="/api/camera/stream" />
    Waits for frames from pipeline; shows nothing until first frame arrives.
    """
    return StreamingResponse(
        _generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
        },
    )
