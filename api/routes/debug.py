"""
Debug endpoints to verify face detection and pipeline state.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_detector, check_models_loaded
from camera.frame_buffer import get as get_latest_frame

router = APIRouter()


class DetectionDebugResponse(BaseModel):
    """Response for detection debug endpoint."""
    faces_detected: int
    frame_available: bool
    frame_shape: list[int] | None
    message: str


@router.get("/detection", response_model=DetectionDebugResponse)
async def debug_detection(
    detector=Depends(get_detector),
):
    """
    Run face detection on the latest frame from the pipeline.
    Use this to verify if the detector sees faces when the live feed shows a face.
    """
    frame = get_latest_frame()
    if frame is None:
        return DetectionDebugResponse(
            faces_detected=0,
            frame_available=False,
            frame_shape=None,
            message="No frame available. Is the pipeline running (not --api-only)?",
        )
    bboxes = detector.detect(frame)
    return DetectionDebugResponse(
        faces_detected=len(bboxes),
        frame_available=True,
        frame_shape=list(frame.shape),
        message=f"Detected {len(bboxes)} face(s) on latest frame. Lower DETECTION_THRESHOLD in .env if you see a face but get 0."
        if len(bboxes) == 0
        else f"Detection OK: {len(bboxes)} face(s).",
    )
