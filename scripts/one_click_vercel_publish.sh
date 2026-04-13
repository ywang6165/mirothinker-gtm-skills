#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUNDLE_DIR="$REPO_ROOT/output/interview-bundle"

if [ ! -d "$BUNDLE_DIR" ]; then
  echo "Bundle directory not found: $BUNDLE_DIR"
  echo "Run: python3 $SCRIPT_DIR/build_interview_bundle.py"
  exit 1
fi

echo "Deploying interview bundle from: $BUNDLE_DIR"
cd "$BUNDLE_DIR"

npx vercel deploy --prod --yes
