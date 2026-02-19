#!/usr/bin/env bash
#
# Stop Reachy Mini CCTV on the robot (kill tmux session or main.py process).
#
# Usage:
#   ./scripts/stop-on-robot.sh
#
# Uses same ROBOT_USER / ROBOT_HOST as run-on-robot.sh.
#

set -e

ROBOT_USER="${ROBOT_USER:-pollen}"
ROBOT_HOST="${ROBOT_HOST:-reachy-mini}"
TMUX_SESSION="reachy-cctv"

SSH_TARGET="${ROBOT_USER}@${ROBOT_HOST}"

echo "Stopping Reachy Mini CCTV on $SSH_TARGET..."
ssh "$SSH_TARGET" "tmux kill-session -t $TMUX_SESSION 2>/dev/null && echo 'Stopped (tmux session killed).' || (pkill -f 'python main.py' 2>/dev/null && echo 'Stopped (process killed).' || echo 'No running session or process found.')"
