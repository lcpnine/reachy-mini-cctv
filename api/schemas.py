"""
Pydantic models for API request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# User schemas
class UserCreate(BaseModel):
    """Schema for creating a new user."""
    name: str = Field(..., min_length=1, max_length=100, description="User's name")


class UserResponse(BaseModel):
    """Schema for user response."""
    user_id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Schema for user list response."""
    users: list[UserResponse]
    total: int


# Event schemas
class EventResponse(BaseModel):
    """Schema for event response."""
    event_id: int
    user_id: Optional[int]
    user_name: Optional[str]
    confidence: float
    photo_path: Optional[str]
    occurred_at: datetime
    is_known: bool

    model_config = ConfigDict(from_attributes=True)


class EventListResponse(BaseModel):
    """Schema for event list response."""
    events: list[EventResponse]
    total: int
    limit: int
    offset: int


class EventStatsResponse(BaseModel):
    """Schema for event statistics."""
    total_events: int
    known_events: int
    unknown_events: int
    unique_users: int


# Photo schemas
class PhotoInfo(BaseModel):
    """Schema for photo information."""
    filename: str
    path: str
    created_at: datetime
    size_bytes: int


# SSE Event schemas
class SSEEvent(BaseModel):
    """Schema for Server-Sent Events."""
    event_type: str = Field(..., description="Event type (detection, registration, etc.)")
    data: dict = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.now)


# Registration schema
class UserRegistrationRequest(BaseModel):
    """Schema for user registration request."""
    name: str = Field(..., min_length=1, max_length=100)
    # Note: Image file is handled separately as multipart form data


class UserRegistrationResponse(BaseModel):
    """Schema for user registration response."""
    user_id: int
    name: str
    message: str


# Error schemas
class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# Health check schema
class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    timestamp: datetime
    version: str
    database_connected: bool
    models_loaded: bool
