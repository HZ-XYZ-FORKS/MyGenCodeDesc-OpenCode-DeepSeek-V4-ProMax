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
echo "Git repo:        $WORK_DIR/repo/"
echo "genCodeDesc v26.04: $WORK_DIR/gcd-v26.04/  ($(ls $WORK_DIR/gcd-v26.04/ 2>/dev/null | wc -l | tr -d ' ') files)"
echo "genCodeDesc v26.03: $WORK_DIR/gcd-v26.03/  ($(ls $WORK_DIR/gcd-v26.03/ 2>/dev/null | wc -l | tr -d ' ') files)"
echo "Patches:           $WORK_DIR/patches/       ($(ls $WORK_DIR/patches/ 2>/dev/null | wc -l | tr -d ' ') files)"
if [ -d "$WORK_DIR/svn_repo" ]; then
    echo "SVN repo:          $WORK_DIR/svn_repo/"
    echo "SVN genCodeDesc:   $WORK_DIR/gcd-svn/     ($(ls $WORK_DIR/gcd-svn/ 2>/dev/null | wc -l | tr -d ' ') files)"
fi
echo ""
echo "Run: ./run_demo.sh"
