#!/usr/bin/env bash
#
# Run Reachy Mini CCTV on the robot via SSH.
# Starts both backend (API + camera) and web dashboard.
# Runs inside a tmux session so it keeps running after you disconnect.
#
# Usage:
#   ./scripts/run-on-robot.sh              # start in tmux (detached)
#   ./scripts/run-on-robot.sh --attach      # start and attach to see logs
#   ./scripts/run-on-robot.sh --foreground  # run in foreground (exits when SSH ends)
#   ./scripts/run-on-robot.sh --sync        # rsync project to robot, then start
#
# Prerequisites:
#   - SSH access to the robot (e.g. ssh-copy-id pollen@reachy-mini)
#   - Project and venv already set up on the robot
#   - Node.js 24.x on the robot (for web dashboard):
#       curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
#       sudo apt-get install -y nodejs
#   - tmux optional (falls back to nohup if not installed or if tmux fails)
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

# Backend: main.py
RUN_CMD="REMOTE_DIR=$REMOTE_DIR_EXPR; cd \"\$REMOTE_DIR\" && $ACTIVATE && python main.py --camera reachy"

# Web: ensure build exists, then npm start
WEB_CMD="REMOTE_DIR=$REMOTE_DIR_EXPR; cd \"\$REMOTE_DIR/web\" && (test -d .next || (npm install && npm run build)) && npm start"

LOG_FILE="/tmp/reachy-cctv.log"
WEB_LOG_FILE="/tmp/reachy-cctv-web.log"

SSH_TARGET="${ROBOT_USER}@${ROBOT_HOST}"

# --- Options ---
MODE="background"
SYNC_FIRST=false
for arg in "$@"; do
  case "$arg" in
    --attach)     MODE="attach" ;;
    --foreground) MODE="foreground" ;;
    --sync)       SYNC_FIRST=true ;;
  esac
done

# Project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Pre-flight: sync project to robot if requested
if [[ "$SYNC_FIRST" == true ]]; then
  echo "Syncing project to $SSH_TARGET:~/$ROBOT_PROJECT/ ..."
  rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '.next' --exclude 'venv' \
    --exclude '__pycache__' --exclude '*.pyc' --exclude 'data/' \
    "$PROJECT_ROOT/" "$SSH_TARGET:~/$ROBOT_PROJECT/"
  echo "Sync done."
fi

case "$MODE" in
  background)
    echo "Starting Reachy Mini CCTV (backend + web) on $SSH_TARGET..."
    ssh "$SSH_TARGET" bash -s << ENDSSH
      set -e
      REMOTE_DIR=\$HOME/$ROBOT_PROJECT

      if [[ ! -d "\$REMOTE_DIR" ]]; then
        echo "Error: Project directory \$REMOTE_DIR does not exist on the robot."
        echo ""
        echo "Set up the project first:"
        echo "  1. ssh $SSH_TARGET"
        echo "  2. git clone https://github.com/lcpnine/reachy-mini-cctv.git \$REMOTE_DIR"
        echo "  3. cd \$REMOTE_DIR && python3 -m venv venv && source venv/bin/activate"
        echo "  4. pip install -r requirements.txt reachy-mini"
        echo "  5. python scripts/setup_models_from_insightface.py"
        echo ""
        echo "Or sync from your machine: ./scripts/run-on-robot.sh --sync"
        echo "Or if project is elsewhere, set: ROBOT_PROJECT=your-folder ./scripts/run-on-robot.sh"
        exit 1
      fi
      if [[ ! -d "\$REMOTE_DIR/web" ]]; then
        echo "Error: \$REMOTE_DIR/web does not exist."
        exit 1
      fi
      if [[ -z "$ROBOT_VENV" ]] && [[ ! -f "\$REMOTE_DIR/venv/bin/activate" ]]; then
        echo "Error: venv not found. On the robot run:"
        echo "  cd \$REMOTE_DIR && python3 -m venv venv && source venv/bin/activate"
        echo "  pip install -r requirements.txt reachy-mini"
        exit 1
      fi

      run_nohup() {
        cd "\$REMOTE_DIR" && $ACTIVATE && nohup python main.py --camera reachy > $LOG_FILE 2>&1 &
        cd "\$REMOTE_DIR/web" && (test -d .next || (npm install && npm run build)) && nohup npm start > $WEB_LOG_FILE 2>&1 &
        echo "Started (nohup)."
        echo "  - API:  http://$ROBOT_HOST:8501"
        echo "  - Web:  http://$ROBOT_HOST:3000"
        echo "Logs: ssh $SSH_TARGET tail -f $LOG_FILE"
      }

      if command -v tmux &>/dev/null; then
        if tmux has-session -t $TMUX_SESSION 2>/dev/null; then
          echo "Session already running. Attach: ssh $SSH_TARGET -t tmux attach -t $TMUX_SESSION"
        else
          if tmux new-session -d -s $TMUX_SESSION -n backend "$RUN_CMD" 2>/dev/null && \
             tmux new-window -t $TMUX_SESSION -n web "$WEB_CMD" 2>/dev/null; then
            echo "Started backend + web (tmux)."
            echo "  - API:  http://$ROBOT_HOST:8501"
            echo "  - Web:  http://$ROBOT_HOST:3000"
            echo "Attach to logs: ssh $SSH_TARGET -t tmux attach -t $TMUX_SESSION"
          else
            echo "tmux failed (e.g. no server / permission), falling back to nohup."
            run_nohup
          fi
        fi
      else
        run_nohup
      fi
ENDSSH
    ;;
  attach)
    echo "Starting (or attaching) on $SSH_TARGET..."
    ssh -t "$SSH_TARGET" bash -s << ENDSSH
      REMOTE_DIR=\$HOME/$ROBOT_PROJECT

      if [[ ! -d "\$REMOTE_DIR" ]] || [[ ! -d "\$REMOTE_DIR/web" ]]; then
        echo "Error: Project \$REMOTE_DIR (or web/) not found. Run: ./scripts/run-on-robot.sh --sync"
        exit 1
      fi
      if [[ -z "$ROBOT_VENV" ]] && [[ ! -f "\$REMOTE_DIR/venv/bin/activate" ]]; then
        echo "Error: venv not found. Set up Python venv on the robot first."
        exit 1
      fi

      if command -v tmux &>/dev/null; then
        if ! tmux has-session -t $TMUX_SESSION 2>/dev/null; then
          if tmux new-session -d -s $TMUX_SESSION -n backend "$RUN_CMD" 2>/dev/null; then
            tmux new-window -t $TMUX_SESSION -n web "$WEB_CMD" 2>/dev/null || true
          else
            echo "tmux failed, using nohup + tail..."
            cd "\$REMOTE_DIR" && $ACTIVATE && nohup python main.py --camera reachy > $LOG_FILE 2>&1 &
            cd "\$REMOTE_DIR/web" && (test -d .next || (npm install && npm run build)) && nohup npm start > $WEB_LOG_FILE 2>&1 &
            sleep 1
            exec tail -f $LOG_FILE
          fi
        fi
        exec tmux attach -t $TMUX_SESSION
      else
        cd "\$REMOTE_DIR" && $ACTIVATE && nohup python main.py --camera reachy > $LOG_FILE 2>&1 &
        cd "\$REMOTE_DIR/web" && (test -d .next || (npm install && npm run build)) && nohup npm start > $WEB_LOG_FILE 2>&1 &
        sleep 1
        exec tail -f $LOG_FILE
      fi
ENDSSH
    ;;
  foreground)
    echo "Running in foreground on $SSH_TARGET (Ctrl+C will stop both)..."
    ssh -t "$SSH_TARGET" bash -s << ENDSSH
      REMOTE_DIR=\$HOME/$ROBOT_PROJECT

      if [[ ! -d "\$REMOTE_DIR" ]] || [[ ! -d "\$REMOTE_DIR/web" ]]; then
        echo "Error: Project \$REMOTE_DIR (or web/) not found. Run: ./scripts/run-on-robot.sh --sync"
        exit 1
      fi
      if [[ -z "$ROBOT_VENV" ]] && [[ ! -f "\$REMOTE_DIR/venv/bin/activate" ]]; then
        echo "Error: venv not found. Set up Python venv on the robot first."
        exit 1
      fi

      cleanup() { kill \$BACKEND_PID \$WEB_PID 2>/dev/null; exit 0; }
      trap cleanup INT TERM
      cd "\$REMOTE_DIR" && $ACTIVATE && python main.py --camera reachy &
      BACKEND_PID=\$!
      cd "\$REMOTE_DIR/web" && (test -d .next || (npm install && npm run build)) && npm start &
      WEB_PID=\$!
      wait
ENDSSH
    ;;
esac
