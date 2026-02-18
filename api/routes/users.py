"""
User management API routes.
"""
import cv2
import numpy as np
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from api.deps import (
    get_user_repo,
    get_detector,
    get_embedder,
    get_recognizer,
)
from api.schemas import (
    UserResponse,
    UserListResponse,
    UserRegistrationResponse,
    ErrorResponse
)
from db.user_repo import UserRepository
from core.detector import FaceDetector
from core.embedder import FaceEmbedder
from core.recognizer import FaceRecognizer


router = APIRouter()


@router.post("/", response_model=UserRegistrationResponse, status_code=201)
async def register_user(
    name: str = Form(...),
    image: UploadFile = File(...),
    user_repo: UserRepository = Depends(get_user_repo),
    detector: FaceDetector = Depends(get_detector),
    embedder: FaceEmbedder = Depends(get_embedder),
    recognizer: FaceRecognizer = Depends(get_recognizer)
):
    """
    Register a new user with a face image.

    Args:
        name: User's name
        image: Face image file (JPEG, PNG)

    Returns:
        User registration response with user_id
    """
    try:
        # Read image file
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Detect face
        bbox = detector.detect_largest(img)

        if bbox is None:
            raise HTTPException(
                status_code=400,
                detail="No face detected in the image. Please provide a clear photo with a visible face."
            )

        # Crop face
        face_crop = img[bbox.y1:bbox.y2, bbox.x1:bbox.x2]

        # Extract embedding
        embedding = embedder.embed(face_crop)

        if embedding is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to extract face embedding"
            )

        # Create user in database
        user_id = user_repo.create_user(name)

        # Register embedding in FAISS index
        recognizer.register(user_id, embedding)

        # Save recognizer state
        recognizer.save()

        return UserRegistrationResponse(
            user_id=user_id,
            name=name,
            message=f"User '{name}' registered successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.get("/", response_model=UserListResponse)
async def list_users(
    limit: int = 100,
    offset: int = 0,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    List all registered users.

    Args:
        limit: Maximum number of users to return
        offset: Number of users to skip

    Returns:
        List of users
    """
    users = user_repo.list_users(limit=limit, offset=offset)
    total = user_repo.get_user_count()

    return UserListResponse(
        users=[
            UserResponse(
                user_id=user.user_id,
                name=user.name,
                created_at=user.created_at
            )
            for user in users
        ],
        total=total
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Get a specific user by ID.

    Args:
        user_id: User ID

    Returns:
        User details
    """
    user = user_repo.get_user(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        created_at=user.created_at
    )


@router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repo),
    recognizer: FaceRecognizer = Depends(get_recognizer)
):
    """
    Delete a user.
    Removes the user from both the database and the face recognition index.

    Args:
        user_id: User ID

    Returns:
        Success message
    """
    # Check if user exists
    user = user_repo.get_user(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Remove from FAISS index
    recognizer.remove(user_id)

    # Save recognizer state
    recognizer.save()

    # Delete from database
    user_repo.delete_user(user_id)

    return {
        "message": f"User '{user.name}' (ID: {user_id}) deleted successfully"
    }


@router.get("/search/", response_model=UserListResponse)
async def search_users(
    q: str,
    limit: int = 20,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Search users by name.

    Args:
        q: Search query
        limit: Maximum number of results

    Returns:
        List of matching users
    """
    users = user_repo.search_users(query=q, limit=limit)

    return UserListResponse(
        users=[
            UserResponse(
                user_id=user.user_id,
                name=user.name,
                created_at=user.created_at
            )
            for user in users
        ],
        total=len(users)
    )
