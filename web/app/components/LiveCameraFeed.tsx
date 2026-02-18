"use client"

import { getCameraStreamUrl, getRecognitionState, type RecognitionFace } from "@/lib/api"
import { useState, useEffect, useRef } from "react"

export default function LiveCameraFeed() {
  const [error, setError] = useState(false)
  const [faces, setFaces] = useState<RecognitionFace[]>([])
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const poll = async () => {
      try {
        const state = await getRecognitionState()
        setFaces(state.faces)
      } catch {
        setFaces([])
      }
    }
    poll()
    intervalRef.current = setInterval(poll, 400)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [])

  return (
    <div className="aspect-video bg-gray-900 flex items-center justify-center min-h-[280px] relative">
      {!error ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element -- MJPEG stream requires img */}
          <img
            src={getCameraStreamUrl()}
            alt="Live camera feed from Reachy"
            className="w-full h-full object-contain"
            onError={() => setError(true)}
          />
          {faces.length > 0 && (
            <div className="absolute bottom-3 left-3 right-3 flex flex-wrap gap-2">
              {faces.map((face, i) => (
                <span
                  key={i}
                  className={
                    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium shadow-lg " +
                    (face.is_known
                      ? "bg-emerald-500/90 text-white"
                      : "bg-amber-500/90 text-white")
                  }
                >
                  {face.is_known ? (
                    <>
                      <span aria-hidden>✓</span>
                      <span>Recognized: {face.user_name}</span>
                      <span className="opacity-90">({(face.confidence * 100).toFixed(0)}%)</span>
                    </>
                  ) : (
                    <>
                      <span aria-hidden>?</span>
                      <span>Unknown visitor</span>
                      <span className="opacity-90">({(face.confidence * 100).toFixed(0)}%)</span>
                    </>
                  )}
                </span>
              ))}
            </div>
          )}
        </>
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
