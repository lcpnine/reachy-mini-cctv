#!/usr/bin/env bash
#
# Run Reachy Mini CCTV on the robot via SSH.
# The app runs inside a tmux session so it keeps running after you disconnect.
#
# Usage:
#   ./scripts/run-on-robot.sh              # start in tmux (detached)
#   ./scripts/run-on-robot.sh --attach      # start and attach to see logs
#   ./scripts/run-on-robot.sh --foreground  # run in foreground (exits when SSH ends)
#
# Prerequisites:
#   - SSH access to the robot (e.g. ssh-copy-id pollen@reachy-mini)
#   - Project and venv already set up on the robot
#   - tmux optional (falls back to nohup if not installed)
#

set -e

# --- Configure these for your setup ---
ROBOT_USER="${ROBOT_USER:-pollen}"
ROBOT_HOST="${ROBOT_HOST:-reachy-mini}"
ROBOT_PROJECT="${ROBOT_PROJECT:-reachy-mini-cctv}"
ROBOT_VENV="${ROBOT_VENV:-}"   # e.g. /venvs/apps_venv or leave empty to use project venv

# REMOTE_DIR and ACTIVATE are expanded on the robot (we pass $HOME in the ssh command)
TMUX_SESSION="reachy-cctv"
REMOTE_DIR_EXPR='$HOME/'"$ROBOT_PROJECT"
if [[ -n "$ROBOT_VENV" ]]; then
  ACTIVATE="source $ROBOT_VENV/bin/activate"
else
  ACTIVATE='source "$REMOTE_DIR/venv/bin/activate"'
fi
# Run on robot: set REMOTE_DIR, then cd, activate venv, run main.py
RUN_CMD="REMOTE_DIR=$REMOTE_DIR_EXPR; cd \"\$REMOTE_DIR\" && $ACTIVATE && python main.py --camera reachy"
LOG_FILE="/tmp/reachy-cctv.log"

SSH_TARGET="${ROBOT_USER}@${ROBOT_HOST}"

# --- Options ---
MODE="background"
if [[ "${1:-}" == "--attach" ]]; then
  MODE="attach"
elif [[ "${1:-}" == "--foreground" ]]; then
  MODE="foreground"
fi

case "$MODE" in
  background)
    echo "Starting Reachy Mini CCTV on $SSH_TARGET..."
    ssh "$SSH_TARGET" bash -s << ENDSSH
      set -e
      REMOTE_DIR=\$HOME/$ROBOT_PROJECT
      if command -v tmux &>/dev/null; then
        if tmux has-session -t $TMUX_SESSION 2>/dev/null; then
          echo "Session already running. Attach: ssh $SSH_TARGET -t tmux attach -t $TMUX_SESSION"
        else
          tmux new-session -d -s $TMUX_SESSION "$RUN_CMD"
          echo "Started (tmux). Attach to logs: ssh $SSH_TARGET -t tmux attach -t $TMUX_SESSION"
        fi
      else
        cd "\$REMOTE_DIR" && $ACTIVATE && nohup python main.py --camera reachy > $LOG_FILE 2>&1 &
        echo "Started (nohup, tmux not installed). Logs: $LOG_FILE"
        echo "View logs: ssh $SSH_TARGET tail -f $LOG_FILE"
      fi
ENDSSH
    ;;
  attach)
    echo "Starting (or attaching) on $SSH_TARGET..."
    ssh -t "$SSH_TARGET" bash -s << ENDSSH
      REMOTE_DIR=\$HOME/$ROBOT_PROJECT
      if command -v tmux &>/dev/null; then
        tmux has-session -t $TMUX_SESSION 2>/dev/null || tmux new-session -d -s $TMUX_SESSION "$RUN_CMD"
        exec tmux attach -t $TMUX_SESSION
      else
        cd "\$REMOTE_DIR" && $ACTIVATE && nohup python main.py --camera reachy > $LOG_FILE 2>&1 &
        sleep 1
        exec tail -f $LOG_FILE
      fi
ENDSSH
    ;;
  foreground)
    echo "Running in foreground on $SSH_TARGET (Ctrl+C will stop the app)..."
    ssh -t "$SSH_TARGET" "REMOTE_DIR=\$HOME/$ROBOT_PROJECT; cd \"\$REMOTE_DIR\" && $ACTIVATE && python main.py --camera reachy"
    ;;
esac
