# reachy-mini-cctv

A face-aware home security system powered by the Reachy Mini robot. It recognizes registered visitors, logs their presence, and alerts you with a photo when an unknown person is detected.

---

## What It Does

**reachy-mini-cctv** turns the Reachy Mini into a stationary security camera with a brain. Instead of recording everything blindly, it understands *who* is in front of it and responds accordingly.

- **Registered person detected** → silently logs the visit (name + timestamp). No alert, no photo.
- **Unknown person detected** → captures a photo and sends you a notification immediately.

You can review all events — both known and unknown — through a web dashboard in real time.

---

## How Detection Works

The camera processes every frame continuously. When a face appears, the system compares it against a database of registered faces. The comparison happens entirely on-device; no image is ever sent to an external server for analysis.

### For registered users

A log entry is created with the user's name and the time of detection. Nothing else happens. The assumption is that if you registered someone, you already trust them.

### For unknown visitors

The system captures a **best-frame photo** — the sharpest, highest-confidence frame from the first few seconds of detection — and sends it to you alongside a notification.

If the same unknown person remains in view or returns, the system captures additional photos on an **exponential backoff schedule** to avoid storage waste while still keeping a record of extended or repeated presence:

| Detection event | Photo taken at |
|---|---|
| 1st detection | Immediately (best frame) |
| 2nd | 10 s after the 1st |
| 3rd | 20 s after the 2nd |
| 4th | 40 s after the 3rd |
| 5th+ | Interval doubles each time |

Each unknown visitor is tracked independently. If a second unknown person appears while the first is still present, the system starts a separate backoff sequence for them immediately.

---

## Who It's For

This is a personal, owner-operated system. You register the people you know — family, frequent guests, roommates — and the system treats everyone else as an unknown visitor. There is a single notification recipient: you.

It is designed as a general-purpose project with no fixed installation environment. The Reachy Mini can be placed facing a front door, a room entrance, or any area you want monitored.

---

## Web Dashboard

A local web dashboard provides a real-time view of the system without needing to check your phone. From the dashboard you can:

- See live detection events as they happen
- Browse the photo history of unknown visitors
- View the access log for registered users
- Manage the registered user database (add or remove people)

The dashboard runs locally on the same device as the camera and is accessible from any browser on the same network.

---

## Notifications

When an unknown person is detected, you receive a push notification containing:

- The captured photo of the person
- The date and time of detection

Notifications are sent to a single recipient (the system owner). The notification channel (e.g. Telegram, email, or similar) is configurable.

---

## Privacy Considerations

- **On-device inference.** All face detection and recognition runs locally on the Reachy Mini. No images or biometric data leave the device during analysis.
- **Selective storage.** Photos are only saved for unknown visitors. Registered users are never photographed by the system.
- **Local dashboard.** The web interface is not exposed to the public internet by default.
- **Your data, your device.** The face database and event logs are stored as local files on the device.
