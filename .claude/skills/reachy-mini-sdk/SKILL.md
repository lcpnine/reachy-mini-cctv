---
name: reachy-mini-sdk
description: Reachy Mini Python SDK API reference (goto_target, media, IMU, etc.)
---
# Reachy Mini Python SDK — Complete API Reference

> This document is intended as a coding reference for LLMs. It covers all available APIs in the Reachy Mini Python SDK.

---

## Setup & Connection

### Import & Context Manager

```python
from reachy_mini import ReachyMini

with ReachyMini() as mini:
    pass  # All SDK usage should be inside this context manager
```

### Connection Modes

The SDK auto-detects USB/localhost vs. network connection. You can override:

```python
ReachyMini()                                        # Auto-detect (recommended)
ReachyMini(connection_mode="localhost_only")        # Force USB/localhost
ReachyMini(connection_mode="network")               # Force network
```

### Media Backends

Specify the media backend based on your hardware version:

```python
ReachyMini(media_backend="default")    # OpenCV + Sounddevice (Reachy Mini Lite)
ReachyMini(media_backend="gstreamer")  # GStreamer (Reachy Mini Lite alternative)
ReachyMini(media_backend="webrtc")     # WebRTC (Reachy Mini Wireless, remote execution)
```

**Auto-selection rules for Reachy Mini Wireless:**
- Running locally (SSH on robot): automatically uses `"gstreamer"`
- Running remotely (from your computer): automatically uses `"webrtc"`
- No need to specify `media_backend` for wireless setups.

---

## Movement API

### `goto_target()` — Smooth Interpolated Movement

Moves the robot smoothly using interpolation. Controls `head`, `antennas`, and `body_yaw`.

```python
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose
import numpy as np

with ReachyMini() as mini:
    mini.goto_target(
        head=create_head_pose(z=10, mm=True),   # Move head up 10mm
        antennas=np.deg2rad([45, 45]),          # Antennas out (radians)
        body_yaw=np.deg2rad(30),                # Rotate body 30 degrees
        duration=2.0,                           # Duration in seconds
        method="minjerk"                        # Interpolation method
    )
```

**Parameters:**
| Parameter   | Type    | Description |
|-------------|---------|-------------|
| `head`      | pose    | Head target pose, created via `create_head_pose()` |
| `antennas`  | ndarray | Antenna angles as numpy array `[left, right]` in radians |
| `body_yaw`  | float   | Body rotation angle in radians |
| `duration`  | float   | Movement duration in seconds |
| `method`    | str     | Interpolation method (see below) |

**Interpolation methods:**
- `"linear"` — Constant speed
- `"minjerk"` — (default) Smooth acceleration/deceleration
- `"ease"` — Ease in/out
- `"cartoon"` — Exaggerated, animated feel

### `create_head_pose()` — Head Pose Helper

```python
from reachy_mini.utils import create_head_pose

pose = create_head_pose(z=10, mm=True)   # Move 10mm along Z axis
```

### `set_target()` — Instant Movement (No Interpolation)

Bypasses interpolation entirely. Use for high-frequency control such as following a joystick or replaying a pre-generated trajectory.

```python
mini.set_target(
    head=...,
    antennas=...,
    body_yaw=...
)
```

---

## Sensors API

### Camera

Returns a single frame from the robot's camera.

```python
with ReachyMini(media_backend="default") as mini:
    frame = mini.media.get_frame()
    # Returns: numpy array, shape (height, width, 3), dtype uint8
```

### IMU (Wireless version only)

> ⚠️ IMU is only available on the **Reachy Mini Wireless** version.

```python
with ReachyMini() as mini:
    imu_data = mini.imu

    accel_x, accel_y, accel_z = imu_data["accelerometer"]  # m/s²
    gyro_x, gyro_y, gyro_z    = imu_data["gyroscope"]       # rad/s
    quat_w, quat_x, quat_y, quat_z = imu_data["quaternion"] # (w, x, y, z)
    temperature                = imu_data["temperature"]     # °C
```

---

## Audio API

All audio goes through `mini.media`. Both input and output devices are locked (busy) while started.

### Start / Stop

```python
with ReachyMini(media_backend="default") as mini:
    mini.media.start_recording()   # Lock and initialize microphone input
    mini.media.start_playing()     # Lock and initialize speaker output

    # ... use audio APIs ...

    mini.media.stop_recording()    # Release microphone
    mini.media.stop_playing()      # Release speaker
```

### Record Audio

```python
samples = mini.media.get_audio_sample()
# Returns: numpy array, shape (samples, 2), dtype float32, sampled at 16kHz
```

### Play Audio

```python
mini.media.push_audio_sample(samples)
# Expects: numpy array, shape (samples, 1 or 2), dtype float32, sampled at 16kHz
# Note: Non-blocking — returns immediately, plays in background
```

To wait for playback to complete:

```python
import time
time.sleep(len(samples) / mini.media.get_output_audio_samplerate())
```

### Resampling

If input and output sample rates differ, resample before playing:

```python
from scipy.signal import resample

samples = mini.media.get_audio_sample()
samples = resample(
    samples,
    mini.media.get_output_audio_samplerate() * len(samples) / mini.media.get_input_audio_samplerate()
)
mini.media.push_audio_sample(samples)
```

### Audio Info Methods

```python
mini.media.get_input_audio_samplerate()    # Sample rate of microphone input (Hz)
mini.media.get_output_audio_samplerate()   # Sample rate of speaker output (Hz)
mini.media.get_input_channels()            # Number of input channels
mini.media.get_output_channels()           # Number of output channels
```

### Direction of Arrival (DoA)

```python
doa, is_speech_detected = mini.media.get_DoA()
# doa: float (radians)
#   0       = left
#   π/2     = front or back
#   π       = right
# is_speech_detected: bool
```

---

## Motion Recording API

Record robot movements (in compliant/passive mode or from sent commands) and replay them later.

```python
with ReachyMini() as mini:
    mini.start_recording()

    # Move the robot manually or send commands here

    recorded_data = mini.stop_recording()
    # recorded_data can be saved and replayed later
```

---

## Full Audio Example

```python
from reachy_mini import ReachyMini
from scipy.signal import resample
import time

with ReachyMini(media_backend="default") as mini:
    mini.media.start_recording()
    mini.media.start_playing()

    samples = mini.media.get_audio_sample()

    samples = resample(
        samples,
        mini.media.get_output_audio_samplerate() * len(samples) / mini.media.get_input_audio_samplerate()
    )

    mini.media.push_audio_sample(samples)
    time.sleep(len(samples) / mini.media.get_output_audio_samplerate())

    doa, is_speech_detected = mini.media.get_DoA()
    print(f"Direction of Arrival: {doa} rad, Speech detected: {is_speech_detected}")

    mini.media.stop_recording()
    mini.media.stop_playing()
```

---

## Data Format Summary

| API | Shape | dtype | Sample Rate |
|-----|-------|-------|-------------|
| `get_frame()` | `(H, W, 3)` | `uint8` | N/A |
| `get_audio_sample()` | `(samples, 2)` | `float32` | 16kHz |
| `push_audio_sample()` | `(samples, 1 or 2)` | `float32` | 16kHz |

---

## Media Backend Summary

| Version | Execution | Backend |
|---------|-----------|---------|
| Reachy Mini Lite | Any | `"default"` (recommended) or `"gstreamer"` |
| Reachy Mini Wireless | Local (SSH) | `"gstreamer"` (auto) |
| Reachy Mini Wireless | Remote | `"webrtc"` (auto) |

---

## Notes & Caveats

- `push_audio_sample()` is **non-blocking**. Use `time.sleep()` to wait for playback.
- IMU is **only available** on the Reachy Mini Wireless version.
- After calling `start_recording()` / `start_playing()`, audio devices are marked as **busy** to other applications until `stop_recording()` / `stop_playing()` are called.
- WebRTC backend currently supports **Linux clients only**. Windows and macOS support is planned.

# Core Concepts & Architecture

Understanding how Reachy Mini works under the hood will help you build robust applications and debug issues.

## Software Architecture

Reachy Mini uses a **Client-Server** architecture:

1.  **The Daemon (Server):** 
    * Runs on the computer connected to the robot (or the simulation).
    * Handles hardware I/O (USB/Serial), safety checks, and sensor reading.
    * Exposes a REST API (`localhost:8000`) and WebSocket.
    
2.  **The SDK (Client):**
    * Your Python code (`reachy_mini` package).
    * Connects to the Daemon over the network.
    * *Advantage:* You can run your AI code on a powerful server while the Daemon runs on a Raspberry Pi connected to the robot.

## Coordinate Systems

When moving the robot, you will work with two main reference frames:

### 1. Head Frame
Located at the base of the head. Used for `goto_target` and `set_target` commands.

[![Reachy Mini Head Frame](https://github.com/pollen-robotics/reachy_mini/raw/develop/docs/assets/head_frame.png)]()

### 2. World Frame
Fixed relative to the robot's base. Used for `look_at_world` commands.

[![Reachy Mini World Frame](https://github.com/pollen-robotics/reachy_mini/raw/develop/docs/assets/world_frame.png)]()

## Safety Limits ⚠️

Reachy Mini has physical and software limits to prevent self-collision and damage. The SDK will automatically clamp values to the closest valid position.

| Joint / Axis | Limit Range |
| :--- | :--- |
| **Head Pitch/Roll** | [-40°, +40°] |
| **Head Yaw** | [-180°, +180°] |
| **Body Yaw** | [-160°, +160°] |
| **Yaw Delta** | Max 65° difference between Head and Body Yaw |

## Motor Modes

You can change how the motors behave:
* **`mini.enable_motors()`**: Stiff. Holds position.
* **`mini.disable_motors()`**: Limp. No power.
* **`mini.enable_gravity_compensation()`**: "Soft" mode. You can move the head by hand, and it will stay where you leave it. (Only works with the Placo kinematics backend.)

## Always follow when generating code
- Context manager required: `with ReachyMini(media_backend="default") as mini:`
- Audio resampling: use scipy.signal.resample
