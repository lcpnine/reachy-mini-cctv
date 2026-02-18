"use client"

import { getCameraStreamUrl } from "@/lib/api"
import { useState } from "react"

export default function LiveCameraFeed() {
  const [error, setError] = useState(false)

  return (
    <div className="aspect-video bg-gray-900 flex items-center justify-center min-h-[280px]">
      {!error ? (
        // eslint-disable-next-line @next/next/no-img-element -- MJPEG stream requires img
        <img
          src={getCameraStreamUrl()}
          alt="Live camera feed from Reachy"
          className="w-full h-full object-contain"
          onError={() => setError(true)}
        />
      ) : (
        <div className="flex flex-col items-center justify-center gap-2 text-gray-500">
          <svg
            className="w-12 h-12"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
          <span className="text-sm">Camera unavailable</span>
        </div>
      )}
    </div>
  )
}
