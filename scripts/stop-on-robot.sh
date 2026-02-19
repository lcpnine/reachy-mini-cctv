#!/usr/bin/env bash
#
# Stop Reachy Mini CCTV on the robot (backend + web dashboard).
# Kills the tmux session or falls back to killing processes.
#
# Usage:
#   ./scripts/stop-on-robot.sh
#
# Uses same ROBOT_USER / ROBOT_HOST / ROBOT_PROJECT as run-on-robot.sh.
#

set -e

ROBOT_USER="${ROBOT_USER:-pollen}"
ROBOT_HOST="${ROBOT_HOST:-reachy-mini}"
ROBOT_PROJECT="${ROBOT_PROJECT:-reachy-mini-cctv}"
TMUX_SESSION="reachy-mini-cctv"

SSH_TARGET="${ROBOT_USER}@${ROBOT_HOST}"

echo "Stopping Reachy Mini CCTV (backend + web) on $SSH_TARGET..."
ssh "$SSH_TARGET" bash -s << 'ENDSSH'
  STOPPED=""
  if tmux kill-session -t reachy-mini-cctv 2>/dev/null; then
    STOPPED="tmux session (backend + web)"
  fi
  if pkill -f "python main.py" 2>/dev/null; then
    STOPPED="${STOPPED:+$STOPPED, }backend"
  fi
  if pkill -f "next start" 2>/dev/null || pkill -f "node.*next" 2>/dev/null; then
    STOPPED="${STOPPED:+$STOPPED, }web"
  fi
  if [[ -n "$STOPPED" ]]; then
    echo "Stopped: $STOPPED"
  else
    echo "No running session or process found."
  fi
ENDSSH
