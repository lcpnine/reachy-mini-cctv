/**
 * API client for Reachy Mini CCTV backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Live camera MJPEG stream URL for use in img src */
export function getCameraStreamUrl(): string {
  return `${API_BASE_URL}/api/camera/stream`;
}

/** Recognition result for one face in the current frame (live overlay) */
export interface RecognitionFace {
  is_known: boolean;
  user_name: string;
  confidence: number;
}

export interface RecognitionState {
  faces: RecognitionFace[];
  updated_at: string | null;
}

/** Poll current frame recognition state for live feed overlay */
export async function getRecognitionState(): Promise<RecognitionState> {
  const response = await fetch(`${API_BASE_URL}/api/camera/recognition-state`);
  if (!response.ok) throw new Error('Failed to fetch recognition state');
  return response.json();
}

// Types
export interface User {
  user_id: number;
  name: string;
  created_at: string;
}

export interface Event {
  event_id: number;
  user_id: number | null;
  user_name: string | null;
  confidence: number;
  photo_path: string | null;
  occurred_at: string;
  is_known: boolean;
}

export interface EventStats {
  total_events: number;
  known_events: number;
  unknown_events: number;
  unique_users: number;
}

// Users API
export async function getUsers(): Promise<User[]> {
  const response = await fetch(`${API_BASE_URL}/api/users`);
  if (!response.ok) throw new Error('Failed to fetch users');
  const data = await response.json();
  return data.users;
}

export async function registerUser(name: string, imageFile: File): Promise<User> {
  const formData = new FormData();
  formData.append('name', name);
  formData.append('image', imageFile);

  const response = await fetch(`${API_BASE_URL}/api/users`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to register user');
  }

  return response.json();
}

export async function deleteUser(userId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('Failed to delete user');
  }
}

// Events API
export async function getEvents(
  limit: number = 50,
  offset: number = 0,
  eventType?: 'known' | 'unknown' | 'all'
): Promise<{ events: Event[]; total: number }> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  if (eventType && eventType !== 'all') {
    params.append('event_type', eventType);
  }

  const response = await fetch(`${API_BASE_URL}/api/events?${params}`);
  if (!response.ok) throw new Error('Failed to fetch events');
  return response.json();
}

export async function getEventStats(): Promise<EventStats> {
  const response = await fetch(`${API_BASE_URL}/api/events/stats`);
  if (!response.ok) throw new Error('Failed to fetch event stats');
  return response.json();
}

// Photos API
export function getPhotoUrl(photoPath: string | null): string | null {
  if (!photoPath) return null;
  const filename = photoPath.split('/').pop();
  return `${API_BASE_URL}/api/photos/${filename}`;
}

// SSE Event Stream
export function createEventStream(
  onEvent: (event: Event) => void,
  onError?: (error: Error) => void
): EventSource {
  const eventSource = new EventSource(`${API_BASE_URL}/api/events/stream/sse`);

  eventSource.addEventListener('detection', (e) => {
    try {
      const data = JSON.parse(e.data);
      // Transform pipeline event to Event interface
      const event: Event = {
        event_id: Date.now(), // Temporary ID
        user_id: data.user_id,
        user_name: data.user_name,
        confidence: data.confidence,
        photo_path: data.photo_path,
        occurred_at: data.occurred_at,
        is_known: data.is_known,
      };
      onEvent(event);
    } catch (error) {
      console.error('Failed to parse SSE event:', error);
    }
  });

  eventSource.addEventListener('error', (e) => {
    console.error('SSE error:', e);
    if (onError) {
      onError(new Error('Event stream error'));
    }
  });

  return eventSource;
}
