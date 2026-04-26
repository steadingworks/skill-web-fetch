#!/usr/bin/env bash
# deploy.sh — build and push image to GHCR, deploy stack to Swarm
# Requires: skill_web_public_key secret already exists (see skill-auth/deploy.sh secrets)
set -euo pipefail

TARGET=steward.ds-m1
STACK=skill-web-fetch
IMAGE=ghcr.io/steadingworks/skill-web-fetch:latest

# ── Build and push ─────────────────────────────────────────────────────────────

build() {
  echo "→ Building $IMAGE..."
  docker buildx build --platform linux/amd64,linux/arm64 -t "$IMAGE" api/
  echo "→ Pushing to GHCR..."
  docker push "$IMAGE"
  echo "  ✓ Pushed $IMAGE"
}

# ── Deploy ────────────────────────────────────────────────────────────────────

deploy() {
  echo "→ Deploying stack $STACK..."
  ssh "$TARGET" "mkdir -p /home/hopper/docker/$STACK"
  rsync -av --delete \
    --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    compose.yaml "$TARGET:/home/hopper/docker/$STACK/"
  ssh "$TARGET" "sudo docker stack deploy -c /home/hopper/docker/$STACK/compose.yaml $STACK"
  echo "  ✓ Stack deployed"
  echo ""
  echo "→ Service status:"
  ssh "$TARGET" "sudo docker service ps ${STACK}_api --format '{{.Node}}\t{{.CurrentState}}'"
}

# ── Main ──────────────────────────────────────────────────────────────────────

case "${1:-}" in
  build)  build ;;
  push)   build ;;
  deploy) build; deploy ;;
  stack)  deploy ;;
  *)
    echo "Usage: $0 <command>"
    echo ""
    echo "  build    Build and push image to GHCR"
    echo "  deploy   Build, push, and deploy stack"
    echo "  stack    Deploy stack only (skip build)"
    exit 1
    ;;
esac
