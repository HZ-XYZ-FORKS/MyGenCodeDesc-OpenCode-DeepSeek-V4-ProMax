#!/bin/bash

echo "=== Setup: aggregateGenCodeDesc Demo ==="
echo ""

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="$BASE_DIR/demo_work"

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

export WORK_DIR
PYTHONPATH="$(cd "$BASE_DIR/.." && pwd)" python3 "$BASE_DIR/generate_demo.py"

echo ""
echo "=== Setup Complete ==="
echo "git/"
echo "  repo:          $WORK_DIR/git/repo/"
echo "  genCodeDesc v26.04: $WORK_DIR/git/gcd-v26.04/  ($(ls $WORK_DIR/git/gcd-v26.04/ 2>/dev/null | wc -l | tr -d ' ') files)"
echo "  genCodeDesc v26.03: $WORK_DIR/git/gcd-v26.03/  ($(ls $WORK_DIR/git/gcd-v26.03/ 2>/dev/null | wc -l | tr -d ' ') files)"
echo "  patches:         $WORK_DIR/git/patches/       ($(ls $WORK_DIR/git/patches/ 2>/dev/null | wc -l | tr -d ' ') files)"
if [ -d "$WORK_DIR/svn/repo" ]; then
    echo "svn/"
    echo "  repo:          $WORK_DIR/svn/repo/"
    echo "  genCodeDesc:   $WORK_DIR/svn/gcd/     ($(ls $WORK_DIR/svn/gcd/ 2>/dev/null | wc -l | tr -d ' ') files)"
    echo "  patches:       $WORK_DIR/svn/patches/  ($(ls $WORK_DIR/svn/patches/ 2>/dev/null | wc -l | tr -d ' ') files)"
fi
echo ""
echo "Run: ./run_demo.sh"
