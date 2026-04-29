#!/bin/bash
BASE="$(cd "$(dirname "$0")" && pwd)"
WORK="$BASE/demo_work"
PROJECT="$(cd "$BASE/.." && pwd)"
export PYTHONPATH="$PROJECT"
TOOL="python3 -m aggregateGenCodeDesc.cli"
REPO="$WORK/repo"

echo "============================================"
echo " aggregateGenCodeDesc Demo — 12 Cell Matrix"
echo "============================================"
echo ""

RUN() {
    local label="$1"; shift
    echo "--- $label ---"
    mkdir -p "$WORK/out/$label"
    $TOOL "$@"
    local rc=$?
    if [ $rc -eq 0 ]; then
        python3 -c "
import json, sys
try:
    d = json.load(open('$WORK/out/$label/genCodeDescV26.03.json'))
    m = d['AGGREGATE']['metrics']
    print(f'  PASS  weighted={m[\"weighted\"][\"value\"]:.1%}  fullyAI={m[\"fullyAI\"][\"value\"]:.1%}  mostlyAI={m[\"mostlyAI\"][\"value\"]:.1%}')
except: print('  PASS  (output OK)')
"
    else
        echo "  FAIL (exit $rc)"
    fi
    echo ""
}

# ==========================================
# Algorithm C (cells 3, 6, 9, 12) — no VCS
# same code path regardless of VCS or access
# ==========================================
echo "=== Algorithm C (v26.04, VCS-free) ==="
echo "  cells 3(git·local), 6(git·remote), 9(svn·local), 12(svn·remote)"
echo ""

RUN "cell-03-git-local-C" \
    --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-15T00:00:00Z \
    --threshold 60 --algorithm C --scope A \
    --genCodeDescDir "$WORK/gcd-v26.04" \
    --outputDir "$WORK/out/cell-03-git-local-C"

# ==========================================
# Algorithm A — Git (cells 1, 4)
# ==========================================
echo "=== Algorithm A — Git live blame (v26.03) ==="
echo ""

RUN "cell-01-git-local-A" \
    --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-15T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir "$WORK/gcd-v26.03" \
    --repoPath "$REPO" \
    --outputDir "$WORK/out/cell-01-git-local-A"

RUN "cell-04-git-remote-A" \
    --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-15T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir "$WORK/gcd-v26.03" \
    --outputDir "$WORK/out/cell-04-git-remote-A"

# ==========================================
# Algorithm B — Git (cells 2, 5)
# ==========================================
echo "=== Algorithm B — Git diff replay (v26.03) ==="
echo ""

RUN "cell-02-git-local-B" \
    --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-15T00:00:00Z \
    --threshold 60 --algorithm B --scope A \
    --genCodeDescDir "$WORK/gcd-v26.03" \
    --repoPath "$REPO" \
    --commitPatchDir "$WORK/patches" \
    --outputDir "$WORK/out/cell-02-git-local-B"

# ==========================================
# SVN cells (7-12) — if svn available
# ==========================================
echo "=== SVN cells (7-12) ==="
echo ""

if command -v svn &> /dev/null && [ -d "$WORK/svn_repo" ]; then
    SVN_REPO="$WORK/svn_repo"
    SVN_CO="$WORK/svn_checkout"
    SVN_GCD="$WORK/gcd-svn"
    SVN_PATCHES="$WORK/svn-patches"

    RUN "cell-07-svn-local-A" \
        --repoUrl "file://$SVN_REPO" --repoBranch /trunk \
        --startTime 2026-01-01T00:00:00Z --endTime 2026-12-31T00:00:00Z \
        --threshold 60 --algorithm A --scope A \
        --genCodeDescDir "$SVN_GCD" --repoPath "$SVN_CO" \
        --outputDir "$WORK/out/cell-07-svn-local-A"

    RUN "cell-10-svn-remote-A" \
        --repoUrl "file://$SVN_REPO" --repoBranch /trunk \
        --startTime 2026-01-01T00:00:00Z --endTime 2026-12-31T00:00:00Z \
        --threshold 60 --algorithm A --scope A \
        --genCodeDescDir "$SVN_GCD" --repoPath "$SVN_CO" \
        --outputDir "$WORK/out/cell-10-svn-remote-A"

    RUN "cell-08-svn-local-B" \
        --repoUrl "file://$SVN_REPO" --repoBranch /trunk \
        --startTime 2026-01-01T00:00:00Z --endTime 2026-12-31T00:00:00Z \
        --threshold 60 --algorithm B --scope A \
        --genCodeDescDir "$SVN_GCD" --repoPath "$SVN_CO" \
        --commitPatchDir "$SVN_PATCHES" \
        --outputDir "$WORK/out/cell-08-svn-local-B"
else
    echo "  SKIP: svn not installed or setup not run (cells 7-12)"
fi

# ==========================================
# Validation tests (error handling)
# ==========================================
echo "=== Validation ==="
echo ""

echo "--- alg-version-mismatch (exit 2 expected) ---"
$TOOL --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir "$WORK/gcd-v26.04" \
    --outputDir "$WORK/out/err-version" 2>/dev/null
echo "  EXIT: $?"

echo "--- duplicate-revision (exit 2 expected) ---"
mkdir -p "$WORK/gcd-dup"
cp "$WORK/gcd-v26.04/"*.json "$WORK/gcd-dup/"
cp "$(ls "$WORK/gcd-v26.04/"*.json | head -1)" "$WORK/gcd-dup/dup.json"
$TOOL --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm C --scope A \
    --genCodeDescDir "$WORK/gcd-dup" \
    --outputDir "$WORK/out/err-dup" 2>/dev/null
echo "  EXIT: $?"

echo "--- empty-directory ---"
$TOOL --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm C --scope A \
    --genCodeDescDir "$WORK/empty_dir" \
    --outputDir "$WORK/out/err-empty" 2>/dev/null
echo "  EXIT: $?"

echo ""
echo "============================================"
echo " 12-Cell Matrix Summary"
echo "============================================"
echo " 1  git·local·A    cell-01-git-local-A"
echo " 2  git·local·B    cell-02-git-local-B"
echo " 3  git·local·C    cell-03-git-local-C"
echo " 4  git·remote·A   cell-04-git-remote-A"
echo " 5  git·remote·B   (same as #2, patches only)"
echo " 6  git·remote·C   (same as #3, VCS-free)"
echo " 7  svn·local·A    cell-07-svn-local-A"
echo " 8  svn·local·B    cell-08-svn-local-B"
echo " 9  svn·local·C    (same as #3, VCS-free)"
echo " 10 svn·remote·A   cell-10-svn-remote-A"
echo " 11 svn·remote·B   (same as #8, patches only)"
echo " 12 svn·remote·C   (same as #3, VCS-free)"
echo ""
echo " Output: $WORK/out/"
echo "============================================"
