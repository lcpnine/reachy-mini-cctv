"""
Event API routes including event listing and real-time SSE streaming.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from api.deps import get_event_repo
from api.schemas import EventResponse, EventListResponse, EventStatsResponse
from db.event_repo import EventRepository


router = APIRouter()

# Global queue for SSE events
_sse_queue: Optional[asyncio.Queue] = None


def get_sse_queue() -> asyncio.Queue:
    """Get or create the global SSE event queue."""
    global _sse_queue
    if _sse_queue is None:
        _sse_queue = asyncio.Queue()
    return _sse_queue


async def broadcast_event(event_data: dict):
    """
    Broadcast an event to all SSE clients.

    Args:
        event_data: Event data dictionary
    """
    queue = get_sse_queue()
    await queue.put(event_data)


@router.get("/", response_model=EventListResponse)
async def list_events(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(
        None,
        description="Filter by event type: 'known', 'unknown', or 'all'"
    ),
    event_repo: EventRepository = Depends(get_event_repo)
):
    """
    List events with pagination and filtering.

    Args:
        limit: Maximum number of events to return (1-500)
        offset: Number of events to skip
        user_id: Filter by specific user ID
        event_type: Filter by event type (known/unknown/all)

    Returns:
        Paginated list of events
    """
    # Determine filtering
    include_known = True
    include_unknown = True

    if event_type == "known":
        include_unknown = False
    elif event_type == "unknown":
        include_known = False

    # Get events
    events = event_repo.get_events(
        limit=limit,
        offset=offset,
        user_id_filter=user_id,
        include_known=include_known,
        include_unknown=include_unknown
    )

    # Get total count
    total = event_repo.get_event_count(
        user_id_filter=user_id,
        include_known=include_known,
        include_unknown=include_unknown
    )

    return EventListResponse(
        events=[
            EventResponse(
                event_id=event.event_id,
                user_id=event.user_id,
                user_name=event.user_name,
                confidence=event.confidence,
                photo_path=event.photo_path,
                occurred_at=event.occurred_at,
                is_known=event.user_id is not None
            )
            for event in events
        ],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/stats", response_model=EventStatsResponse)
async def get_event_stats(
    since: Optional[datetime] = Query(None, description="Get stats since this datetime"),
    event_repo: EventRepository = Depends(get_event_repo)
):
    """
    Get event statistics.

    Args:
        since: Only count events since this datetime (optional)

    Returns:
        Event statistics
    """
    from db.user_repo import UserRepository

    if since:
        events = event_repo.get_recent_events(since=since)
        total = len(events)
        known = sum(1 for e in events if e.user_id is not None)
        unknown = sum(1 for e in events if e.user_id is None)
    else:
        total = event_repo.get_event_count()
        known = event_repo.get_event_count(include_unknown=False)
        unknown = event_repo.get_event_count(include_known=False)

    # Get unique user count
    user_repo = UserRepository()
    unique_users = user_repo.get_user_count()

    return EventStatsResponse(
        total_events=total,
        known_events=known,
        unknown_events=unknown,
        unique_users=unique_users
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    event_repo: EventRepository = Depends(get_event_repo)
):
    """
    Get a specific event by ID.

    Args:
        event_id: Event ID

    Returns:
        Event details
    """
    from fastapi import HTTPException

    event = event_repo.get_event(event_id)

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventResponse(
        event_id=event.event_id,
        user_id=event.user_id,
        user_name=event.user_name,
        confidence=event.confidence,
        photo_path=event.photo_path,
        occurred_at=event.occurred_at,
        is_known=event.user_id is not None
    )


@router.get("/stream/sse")
async def stream_events():
    """
    Server-Sent Events (SSE) endpoint for real-time event streaming.

    Returns:
        SSE stream of events
    """
    async def event_generator():
        """Generate SSE events from the queue."""
        queue = get_sse_queue()

        # Send initial connection message
        yield {
            "event": "connected",
            "data": json.dumps({
                "message": "Connected to event stream",
                "timestamp": datetime.now().isoformat()
            })
        }

        # Stream events from queue
        while True:
            try:
                # Wait for new event (with timeout to send keepalive)
                event_data = await asyncio.wait_for(queue.get(), timeout=30.0)

                yield {
                    "event": "detection",
                    "data": json.dumps(event_data)
                }

            except asyncio.TimeoutError:
                # Send keepalive ping
                yield {
                    "event": "ping",
                    "data": json.dumps({"timestamp": datetime.now().isoformat()})
                }

            except Exception as e:
                print(f"SSE error: {e}")
                break

    return EventSourceResponse(event_generator())


# Helper function to be called from the pipeline
def notify_event_detected(event_data: dict):
    """
    Notify all SSE clients about a new event.
    This should be called from the pipeline's on_event callback.

    Args:
        event_data: Event data dictionary
    """
    # Create task to broadcast event
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(broadcast_event(event_data))
    except RuntimeError:
        # No event loop running (e.g., during testing)
        print(f"Cannot broadcast event (no event loop): {event_data}")
