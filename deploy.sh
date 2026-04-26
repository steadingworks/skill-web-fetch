#!/usr/bin/env bash
# deploy.sh — build web-fetch image on ds-m1 and deploy stack
# Requires: skill_web_public_key secret already exists (created by skill-auth/deploy.sh)
set -euo pipefail

TARGET=steward.ds-m1
REMOTE_DIR=/home/hopper/docker/skill-web-fetch
STACK=skill-web-fetch

# ── Preflight ─────────────────────────────────────────────────────────────────

check_secrets() {
  local existing
  existing=$(ssh "$TARGET" "sudo docker secret ls --format '{{.Name}}'")

  if ! echo "$existing" | grep -q "^skill_web_public_key$"; then
    echo "error: skill_web_public_key secret not found."
    echo "Run skill-auth/deploy.sh secrets first — it creates both key secrets."
    exit 1
  fi
  echo "→ skill_web_public_key present ✓"
}

# ── Build ─────────────────────────────────────────────────────────────────────

build_image() {
  echo "→ Syncing source to $TARGET:$REMOTE_DIR..."
  ssh "$TARGET" "mkdir -p $REMOTE_DIR"
  rsync -av --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    ./ "$TARGET:$REMOTE_DIR/"

  echo "→ Building image on $TARGET..."
  ssh "$TARGET" "cd $REMOTE_DIR && sudo docker build -t skill-web-fetch:latest api/"
  echo "  ✓ Image built"
}

# ── Deploy ────────────────────────────────────────────────────────────────────

deploy_stack() {
  echo "→ Deploying stack $STACK..."
  ssh "$TARGET" "cd $REMOTE_DIR && sudo docker stack deploy -c compose.yaml $STACK"
  echo "  ✓ Stack deployed"
  echo ""
  echo "→ Service status:"
  ssh "$TARGET" "sudo docker service ps ${STACK}_api --format '{{.Node}}\t{{.CurrentState}}'"
}

# ── Main ──────────────────────────────────────────────────────────────────────

case "${1:-deploy}" in
  build)   build_image ;;
  deploy)  check_secrets; build_image; deploy_stack ;;
  *)       echo "Usage: $0 [build|deploy]"; exit 1 ;;
esac
