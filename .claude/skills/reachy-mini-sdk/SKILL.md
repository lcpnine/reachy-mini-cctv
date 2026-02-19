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

### 2. World Frame
Fixed relative to the robot's base. Used for `look_at_world` commands.

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

---

# Development Workflow for Wireless Reachy Mini

Efficient workflows for developing and testing code on the Wireless Reachy Mini.

## Prerequisites

- SSH access to your robot (`ssh pollen@reachy-mini.local`, password: `root`)
- SSHFS installed on your computer (`sudo apt install sshfs` on Ubuntu/Debian)
- Your robot's IP address (find it in the dashboard, router, or run `ifconfig` after SSH)

## Quick Cross-Platform Options

### VS Code Remote SSH

VS Code's Remote - SSH extension lets you edit files directly on the robot. Connect to `pollen@reachy-mini.local`, then open any folder. Changes are saved directly on the robot. Works on Windows, macOS, and Linux.

### Rsync

Use `rsync` to sync your local source code to the robot's site-packages:

```bash
rsync -avz /path/to/your_app/src/your_app/ \
    pollen@reachy-mini.local:/venvs/apps_venv/lib/python3.12/site-packages/your_app/
```

Run after each edit to push changes. Add `--delete` to remove files that no longer exist locally.

## Approach A: Clone on Robot, Edit Locally (Recommended)

Your code lives on the robot, but you edit it from your computer.

### Step 1: Clone your repository on the robot

```bash
ssh pollen@reachy-mini.local
cd /home/pollen
git clone https://github.com/YOUR_USER/YOUR_APP.git
```

### Step 2: Mount the robot's files to your local machine

On your local computer:

```bash
mkdir -p ~/wireless_dev
sshfs pollen@reachy-mini.local:/home/pollen/YOUR_APP ~/wireless_dev \
    -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3
```

Open `~/wireless_dev` in your IDE and edit as if local.

### Step 3: Install and run your code on the robot

```bash
ssh pollen@reachy-mini.local
cd /home/pollen/YOUR_APP

# Install in editable mode (changes apply immediately):
/venvs/apps_venv/bin/pip install -e .

# Run your app:
/venvs/apps_venv/bin/python -m YOUR_MODULE.main
# Or run directly:
/venvs/apps_venv/bin/python your_script.py
```

### Step 4: Unmount when done

```bash
fusermount -u ~/wireless_dev
```

## Approach B: Override Installed App Sources

Modify an app already installed via the dashboard by mounting your local files over site-packages.

### Step 1: Locate the installed app

Apps are installed in:
```
/venvs/apps_venv/lib/python3.12/site-packages/YOUR_APP_NAME/
```

### Step 2: Mount your local source over the installed location

Run **on the robot**:

```bash
ssh pollen@reachy-mini.local

sshfs YOUR_USER@YOUR_PC_IP:/path/to/your_app/src/your_app \
    /venvs/apps_venv/lib/python3.12/site-packages/YOUR_APP_NAME \
    -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3
```

**Important:** Mount only the content of your `src/your_app/` directory, not the entire repository.

## Approach C: Mount Local Source and Run Directly

Mount your local source onto the robot and run without pip install.

### Step 1: Mount your local source onto the robot

Run **on the robot**:

```bash
ssh pollen@reachy-mini.local
mkdir -p /home/pollen/my_app_mount

sshfs YOUR_USER@YOUR_PC_IP:/path/to/your_app /home/pollen/my_app_mount \
    -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3
```

### Step 2: Run your app directly

```bash
cd /home/pollen/my_app_mount
/venvs/apps_venv/bin/python main.py
```

## Installing a Specific Branch or Version

```bash
ssh pollen@reachy-mini.local
/venvs/apps_venv/bin/python -m pip install --force-reinstall \
    "git+https://github.com/pollen-robotics/MY_AWESOME_APP.git@MY_AWESOME_BRANCH"
```

Replace `MY_AWESOME_BRANCH` with a branch name, tag, or commit hash.

## Common Pitfalls

**Slow pip install over SSHFS:** If you mount from your computer *to* the robot, pip install will be extremely slow. Use Approach A (files on robot, mount to your computer) or run manually with `python -m your_module`.

**Wrong mount point for site-packages:** Site-packages expects the package directory directly (`your_app/__init__.py`, `main.py`), not the repo structure. Mount only the inner `src/your_app/` content.

## Quick Reference

| Task | Command |
|------|---------|
| SSH to robot | `ssh pollen@reachy-mini.local` |
| Stop daemon | `sudo systemctl stop reachy-mini-daemon` |
| Start daemon | `sudo systemctl start reachy-mini-daemon` |
| View daemon logs | `journalctl -u reachy-mini-daemon -f` |
| Check robot status | `reachyminios_check` |
| Mount robot files locally | `sshfs pollen@IP:/path ~/local_mount -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3` |
| Unmount | `fusermount -u ~/local_mount` |

---

## Always follow when generating code
- Context manager required: `with ReachyMini(media_backend="default") as mini:`
- Audio resampling: use scipy.signal.resample
