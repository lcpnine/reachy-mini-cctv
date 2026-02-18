'use client';

import { useState, useEffect, useCallback } from 'react';
import { Event, getEvents, getEventStats, EventStats, createEventStream, getPhotoUrl } from '@/lib/api';

export default function LiveFeedPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [stats, setStats] = useState<EventStats | null>(null);
  const [filter, setFilter] = useState<'all' | 'known' | 'unknown'>('all');
  const [loading, setLoading] = useState(true);
  const [sseConnected, setSSEConnected] = useState(false);

  // Fetch initial events
  useEffect(() => {
    async function fetchInitialData() {
      try {
        const [eventsData, statsData] = await Promise.all([
          getEvents(50, 0, filter),
          getEventStats(),
        ]);
        setEvents(eventsData.events);
        setStats(statsData);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch initial data:', error);
        setLoading(false);
      }
    }
    fetchInitialData();
  }, [filter]);

  // Connect to SSE for real-time updates
  useEffect(() => {
    const eventSource = createEventStream(
      (newEvent) => {
        // Add new event to the top of the list
        setEvents((prev) => [newEvent, ...prev]);
        // Update stats
        setStats((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            total_events: prev.total_events + 1,
            known_events: newEvent.is_known ? prev.known_events + 1 : prev.known_events,
            unknown_events: !newEvent.is_known ? prev.unknown_events + 1 : prev.unknown_events,
          };
        });
      },
      (error) => {
        console.error('SSE error:', error);
        setSSEConnected(false);
      }
    );

    setSSEConnected(true);

    return () => {
      eventSource.close();
      setSSEConnected(false);
    };
  }, []);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatConfidence = (confidence: number) => {
    return (confidence * 100).toFixed(1) + '%';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Live Event Feed</h1>
            <p className="text-gray-600 mt-1">Real-time face detection events</p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                sseConnected
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {sseConnected ? '🟢 Live' : '🔴 Offline'}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-600">Total Events</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">{stats.total_events}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-600">Known Visitors</div>
            <div className="text-3xl font-bold text-green-600 mt-2">{stats.known_events}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-600">Unknown Visitors</div>
            <div className="text-3xl font-bold text-orange-600 mt-2">{stats.unknown_events}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-600">Registered Users</div>
            <div className="text-3xl font-bold text-blue-600 mt-2">{stats.unique_users}</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mb-6">
        <div className="flex gap-2">
          {(['all', 'known', 'unknown'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filter === f
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Events List */}
      <div className="space-y-4">
        {events.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-500">No events yet. Waiting for detections...</p>
          </div>
        ) : (
          events.map((event) => (
            <div
              key={event.event_id}
              className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start gap-4">
                {/* Photo (if unknown) */}
                {event.photo_path && (
                  <div className="flex-shrink-0">
                    <img
                      src={getPhotoUrl(event.photo_path) || ''}
                      alt="Unknown visitor"
                      className="w-24 h-24 rounded-lg object-cover"
                    />
                  </div>
                )}

                {/* Event Info */}
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {event.is_known ? (
                          <span className="text-green-600">✓ {event.user_name}</span>
                        ) : (
                          <span className="text-orange-600">⚠ Unknown Visitor</span>
                        )}
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {formatDate(event.occurred_at)}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-600">Confidence</div>
                      <div
                        className={`text-lg font-bold mt-1 ${
                          event.confidence > 0.7
                            ? 'text-green-600'
                            : event.confidence > 0.5
                            ? 'text-yellow-600'
                            : 'text-red-600'
                        }`}
                      >
                        {formatConfidence(event.confidence)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
