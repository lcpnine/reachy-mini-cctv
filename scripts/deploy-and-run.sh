#!/usr/bin/env bash
#
# Deploy to robot and run. Will prompt for SSH password (default: root) if keys not set up.
#
# Usage:
#   ./scripts/deploy-and-run.sh           # sync, install, run
#   ./scripts/deploy-and-run.sh --sync    # sync only (first time)
#   ./scripts/deploy-and-run.sh --run     # run only (already installed)
#

set -e

ROBOT_USER="${ROBOT_USER:-pollen}"
ROBOT_HOST="${ROBOT_HOST:-reachy-mini.local}"
ROBOT_PROJECT="${ROBOT_PROJECT:-reachy-mini-cctv}"
SSH_TARGET="${ROBOT_USER}@${ROBOT_HOST}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

do_sync() {
  echo ">>> Syncing project to $SSH_TARGET:~/reachy-mini-cctv/ ..."
  rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '.next' --exclude 'venv' \
    --exclude '__pycache__' --exclude '*.pyc' --exclude 'data/' \
    "$PROJECT_ROOT/" "$SSH_TARGET:~/$ROBOT_PROJECT/"
  echo ">>> Sync done."
}

do_install() {
  echo ">>> Installing on robot..."
  ssh "$SSH_TARGET" "cd ~/$ROBOT_PROJECT && bash scripts/install-on-robot.sh"
}

do_run() {
  echo ">>> Starting on robot..."
  ssh -tt "$SSH_TARGET" "cd ~/$ROBOT_PROJECT && source venv/bin/activate && python main.py --camera reachy"
}

case "${1:-}" in
  --sync)   do_sync ;;
  --install) do_sync && do_install ;;
  --run)    do_run ;;
  *)
    do_sync
    do_install
    echo ""
    echo ">>> Install done. Starting Python main.py..."
    do_run
    ;;
esac
