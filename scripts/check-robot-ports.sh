#!/usr/bin/env bash
#
# Check if backend and web servers are running on the robot.
# Run from your Mac to diagnose connection issues.
#
# Usage: ROBOT_PROJECT=reachy-mini-cctv ./scripts/check-robot-ports.sh

set -e

ROBOT_USER="${ROBOT_USER:-pollen}"
ROBOT_HOST="${ROBOT_HOST:-reachy-mini}"
ROBOT_PROJECT="${ROBOT_PROJECT:-reachy-mini-cctv}"
SSH_TARGET="${ROBOT_USER}@${ROBOT_HOST}"

echo "=== Checking robot: $SSH_TARGET ==="
echo ""

# Local check (from Mac)
echo "1. From this Mac:"
if ping -c 1 -t 2 "$ROBOT_HOST" &>/dev/null; then
  echo "   ✓ Ping OK"
else
  echo "   ✗ Ping failed - robot unreachable?"
fi

if nc -z -w 2 "$ROBOT_HOST" 8501 2>/dev/null; then
  echo "   ✓ Port 8501 (API) open"
else
  echo "   ✗ Port 8501 (API) - connection refused or timeout"
fi

if nc -z -w 2 "$ROBOT_HOST" 3000 2>/dev/null; then
  echo "   ✓ Port 3000 (Web) open"
else
  echo "   ✗ Port 3000 (Web) - connection refused or timeout"
fi

echo ""
echo "2. On robot (via SSH):"
ssh "$SSH_TARGET" bash -s << 'REMOTE'
  echo "   Listening on 3000/8501:"
  (ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | grep -E ':(3000|8501)\s' || echo "   (none)"
  echo ""
  echo "   Tmux session reachy-mini-cctv:"
  if tmux has-session -t reachy-mini-cctv 2>/dev/null; then
    tmux list-windows -t reachy-mini-cctv 2>/dev/null | sed 's/^/     /'
  else
    echo "   (no session)"
  fi
  echo ""
  echo "   Web log (last 15 lines):"
  if [[ -f /tmp/reachy-mini-cctv-web.log ]]; then
    tail -15 /tmp/reachy-mini-cctv-web.log | sed 's/^/     /'
  else
    echo "   (no log file)"
  fi
REMOTE
