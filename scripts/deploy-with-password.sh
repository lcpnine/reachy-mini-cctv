#!/usr/bin/env bash
#
# Deploy using password (when SSH keys not set up).
# Usage: REACHY_PASSWORD=root ./scripts/deploy-with-password.sh
# Or:    ./scripts/deploy-with-password.sh   # will prompt
#

set -e

ROBOT_USER="${ROBOT_USER:-pollen}"
ROBOT_HOST="${ROBOT_HOST:-reachy-mini.local}"
ROBOT_PROJECT="${ROBOT_PROJECT:-reachy-mini-cctv}"
SSH_TARGET="${ROBOT_USER}@${ROBOT_HOST}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -z "$REACHY_PASSWORD" ]]; then
  echo "SSH password for $SSH_TARGET (default: root):"
  read -s REACHY_PASSWORD
  REACHY_PASSWORD="${REACHY_PASSWORD:-root}"
fi

export SSHPASS="$REACHY_PASSWORD"
SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=no"
RSYNC_CMD="sshpass -e rsync -avz -e 'ssh -o StrictHostKeyChecking=no'"

echo ">>> Syncing project to $SSH_TARGET..."
rsync -avz -e "$SSH_CMD" \
  --exclude '.git' --exclude 'node_modules' --exclude '.next' --exclude 'venv' \
  --exclude '__pycache__' --exclude '*.pyc' --exclude 'data/' \
  "$PROJECT_ROOT/" "$SSH_TARGET:~/$ROBOT_PROJECT/"
echo ">>> Sync done."

echo ">>> Installing on robot..."
$SSH_CMD "$SSH_TARGET" "cd ~/$ROBOT_PROJECT && bash scripts/install-on-robot.sh"

echo ""
echo ">>> Starting main.py (Ctrl+C to stop)..."
$SSH_CMD -tt "$SSH_TARGET" "cd ~/$ROBOT_PROJECT && source venv/bin/activate && python main.py --camera reachy"
