"use client"

import { Event, getEvents, getPhotoUrl } from "@/lib/api"
import { useEffect, useState } from "react"

export default function PhotosPage() {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPhoto, setSelectedPhoto] = useState<Event | null>(null)
  const [dateFilter, setDateFilter] = useState<
    "all" | "today" | "week" | "month"
  >("all")

  async function fetchPhotos() {
    try {
      // Fetch only unknown events (they have photos)
      const data = await getEvents(100, 0, "unknown")
      setEvents(data.events)
      setLoading(false)
    } catch (error) {
      console.error("Failed to fetch photos:", error)
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    queueMicrotask(() => {
      if (!cancelled) fetchPhotos()
    })
    return () => {
      cancelled = true
    }
  }, [])

  const filterEventsByDate = (events: Event[]) => {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const weekAgo = new Date(today)
    weekAgo.setDate(weekAgo.getDate() - 7)
    const monthAgo = new Date(today)
    monthAgo.setMonth(monthAgo.getMonth() - 1)

    return events.filter((event) => {
      const eventDate = new Date(event.occurred_at)
      switch (dateFilter) {
        case "today":
          return eventDate >= today
        case "week":
          return eventDate >= weekAgo
        case "month":
          return eventDate >= monthAgo
        default:
          return true
      }
    })
  }

  const filteredEvents = filterEventsByDate(events)

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const formatConfidence = (confidence: number) => {
    return (confidence * 100).toFixed(1) + "%"
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading photos...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Unknown Visitor Gallery
        </h1>
        <p className="text-gray-600 mt-1">Photos of unregistered visitors</p>
      </div>

      {/* Date Filters */}
      <div className="mb-6 flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700">Show:</span>
        {(["all", "today", "week", "month"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setDateFilter(f)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              dateFilter === f
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            {f === "all" ? "All Time" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <div className="ml-auto text-sm text-gray-600">
          {filteredEvents.length}{" "}
          {filteredEvents.length === 1 ? "photo" : "photos"}
        </div>
      </div>

      {/* Photos Grid */}
      {filteredEvents.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-gray-500">
            No photos available for the selected time period.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {filteredEvents.map((event) => (
            <div
              key={event.event_id}
              className="bg-white rounded-lg shadow overflow-hidden hover:shadow-xl transition-shadow cursor-pointer"
              onClick={() => setSelectedPhoto(event)}
            >
              {event.photo_path && (
                <div className="aspect-square relative">
                  <img
                    src={getPhotoUrl(event.photo_path) || ""}
                    alt="Unknown visitor"
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-orange-600">
                    Unknown
                  </span>
                  <span
                    className={`text-xs font-medium ${
                      event.confidence > 0.5
                        ? "text-yellow-600"
                        : "text-red-600"
                    }`}
                  >
                    {formatConfidence(event.confidence)}
                  </span>
                </div>
                <p className="text-xs text-gray-600">
                  {formatDate(event.occurred_at)}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Photo Detail Modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedPhoto(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-col md:flex-row">
              {/* Photo */}
              <div className="flex-1 bg-gray-100">
                {selectedPhoto.photo_path && (
                  <img
                    src={getPhotoUrl(selectedPhoto.photo_path) || ""}
                    alt="Unknown visitor"
                    className="w-full h-auto max-h-[70vh] object-contain"
                  />
                )}
              </div>

              {/* Details */}
              <div className="w-full md:w-80 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold text-gray-900">
                    Event Details
                  </h2>
                  <button
                    onClick={() => setSelectedPhoto(null)}
                    className="text-gray-500 hover:text-gray-700 text-2xl"
                  >
                    ×
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Status
                    </label>
                    <p className="text-orange-600 font-semibold mt-1">
                      Unknown Visitor
                    </p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Detection Time
                    </label>
                    <p className="text-gray-900 mt-1">
                      {formatDate(selectedPhoto.occurred_at)}
                    </p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Confidence Score
                    </label>
                    <p
                      className={`font-semibold mt-1 ${
                        selectedPhoto.confidence > 0.5
                          ? "text-yellow-600"
                          : "text-red-600"
                      }`}
                    >
                      {formatConfidence(selectedPhoto.confidence)}
                    </p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Event ID
                    </label>
                    <p className="text-gray-900 mt-1">
                      #{selectedPhoto.event_id}
                    </p>
                  </div>

                  <div className="pt-4 border-t border-gray-200">
                    <p className="text-xs text-gray-500">
                      This photo was captured when an unregistered person was
                      detected. You can register them as a user from the Users
                      page.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
