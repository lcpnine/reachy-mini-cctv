"""
Photo serving API routes.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.deps import get_photo_storage
from camera.photo import PhotoStorage
from core.config import PHOTOS_DIR


router = APIRouter()


@router.get("/{filename}")
async def get_photo(
    filename: str,
    photo_storage: PhotoStorage = Depends(get_photo_storage)
):
    """
    Serve a photo file.

    Args:
        filename: Photo filename (e.g., "unknown_20240101_120000_001.jpg")

    Returns:
        Photo file
    """
    # Validate filename to prevent path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only allow specific file extensions
    allowed_extensions = {".jpg", ".jpeg", ".png"}
    file_ext = Path(filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Get full path
    photo_path = photo_storage.get_photo_path(f"photos/{filename}")

    # Check if file exists
    if not photo_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")

    # Serve the file
    return FileResponse(
        photo_path,
        media_type=f"image/{file_ext[1:]}",  # Remove the dot
        filename=filename
    )


@router.get("/")
async def list_photos(
    photo_storage: PhotoStorage = Depends(get_photo_storage)
):
    """
    List all available photos.

    Returns:
        List of photo filenames
    """
    # List all photo files
    photos = []

    for photo_path in PHOTOS_DIR.glob("unknown_*.jpg"):
        photos.append({
            "filename": photo_path.name,
            "url": f"/api/photos/{photo_path.name}",
            "size_bytes": photo_path.stat().st_size,
            "created_at": photo_path.stat().st_mtime
        })

    # Sort by creation time (newest first)
    photos.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "photos": photos,
        "total": len(photos)
    }
