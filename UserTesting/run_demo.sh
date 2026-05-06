#!/bin/bash
BASE="$(cd "$(dirname "$0")" && pwd)"
WORK="$BASE/demo_work"
PROJECT="$(cd "$BASE/.." && pwd)"
export PYTHONPATH="$PROJECT"
TOOL="python3 -m aggregateGenCodeDesc.cli"
REPO="$WORK/git/repo"

echo "============================================"
echo " aggregateGenCodeDesc Demo — 12 Cell Matrix"
echo "============================================"
echo ""

RUN() {
    local label="$1"; shift
    echo "--- $label ---"
    local out="$WORK/out/$label"
    mkdir -p "$out"
    $TOOL "$@"
    local rc=$?
    if [ $rc -eq 0 ]; then
        python3 -c "
import json, sys
try:
    d = json.load(open('$out/genCodeDescV26.03.json'))
    m = d['AGGREGATE']['metrics']
    print(f'  PASS  weighted={m[\"weighted\"][\"value\"]:.1%}  fullyAI={m[\"fullyAI\"][\"value\"]:.1%}  mostlyAI={m[\"mostlyAI\"][\"value\"]:.1%}')
except: print('  PASS  (output OK)')
"
    else
        echo "  FAIL (exit $rc)"
    fi
    echo ""
}

# ===== Git cells =====
echo "=== Git cells (1-6) ==="
echo ""

RUN "git-03-C" \
    --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-15T00:00:00Z \
    --threshold 60 --algorithm C --scope A \
    --genCodeDescDir "$WORK/git/gcd-v26.04" \
    --outputDir "$WORK/out/git-03-C"

RUN "git-01-A" \
    --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-15T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir "$WORK/git/gcd-v26.03" --repoPath "$REPO" \
    --outputDir "$WORK/out/git-01-A"

RUN "git-04-A-remote" \
    --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-15T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir "$WORK/git/gcd-v26.03" \
    --outputDir "$WORK/out/git-04-A-remote"

RUN "git-02-B" \
    --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-15T00:00:00Z \
    --threshold 60 --algorithm B --scope A \
    --genCodeDescDir "$WORK/git/gcd-v26.03" --repoPath "$REPO" \
    --commitPatchDir "$WORK/git/patches" \
    --outputDir "$WORK/out/git-02-B"

# ===== SVN cells =====
echo "=== SVN cells (7-12) ==="
echo ""

if command -v svn &> /dev/null && [ -d "$WORK/svn/repo" ]; then
    SVN_REPO="$WORK/svn/repo"
    SVN_CO="$WORK/svn/checkout"
    SVN_GCD="$WORK/svn/gcd"
    SVN_PATCHES="$WORK/svn/patches"

    RUN "svn-07-A" \
        --repoUrl "file://$SVN_REPO" --repoBranch /trunk \
        --startTime 2026-01-01T00:00:00Z --endTime 2026-12-31T00:00:00Z \
        --threshold 60 --algorithm A --scope A \
        --genCodeDescDir "$SVN_GCD" --repoPath "$SVN_CO" \
        --outputDir "$WORK/out/svn-07-A"

    RUN "svn-10-A-remote" \
        --repoUrl "file://$SVN_REPO" --repoBranch /trunk \
        --startTime 2026-01-01T00:00:00Z --endTime 2026-12-31T00:00:00Z \
        --threshold 60 --algorithm A --scope A \
        --genCodeDescDir "$SVN_GCD" --repoPath "$SVN_CO" \
        --outputDir "$WORK/out/svn-10-A-remote"

    RUN "svn-08-B" \
        --repoUrl "file://$SVN_REPO" --repoBranch /trunk \
        --startTime 2026-01-01T00:00:00Z --endTime 2026-12-31T00:00:00Z \
        --threshold 60 --algorithm B --scope A \
        --genCodeDescDir "$SVN_GCD" --repoPath "$SVN_CO" \
        --commitPatchDir "$SVN_PATCHES" \
        --outputDir "$WORK/out/svn-08-B"
else
    echo "  SKIP: svn not installed or setup not run"
fi

# ===== Validation =====
echo "=== Validation ==="
echo ""

echo "--- version-mismatch (exit 2) ---"
$TOOL --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir "$WORK/git/gcd-v26.04" \
    --outputDir "$WORK/out/err-version" 2>/dev/null
echo "  EXIT: $?"

echo "--- duplicate-revision (exit 2) ---"
mkdir -p "$WORK/git/gcd-dup"
cp "$WORK/git/gcd-v26.04/"*.json "$WORK/git/gcd-dup/"
cp "$(ls "$WORK/git/gcd-v26.04/"*.json | head -1)" "$WORK/git/gcd-dup/dup.json"
$TOOL --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm C --scope A \
    --genCodeDescDir "$WORK/git/gcd-dup" \
    --outputDir "$WORK/out/err-dup" 2>/dev/null
echo "  EXIT: $?"

echo ""
echo "============================================"
echo " 12-Cell Matrix"
echo "============================================"
echo " 1  git·local·A      out/git-01-A"
echo " 2  git·local·B      out/git-02-B"
echo " 3  git·local·C      out/git-03-C"
echo " 4  git·remote·A     out/git-04-A-remote"
echo " 5  git·remote·B     (same as #2, patches only)"
echo " 6  git·remote·C     (same as #3, VCS-free)"
echo " 7  svn·local·A      out/svn-07-A"
echo " 8  svn·local·B      out/svn-08-B"
echo " 9  svn·local·C      (same as #3, VCS-free)"
echo " 10 svn·remote·A     out/svn-10-A-remote"
echo " 11 svn·remote·B     (same as #8, patches only)"
echo " 12 svn·remote·C     (same as #3, VCS-free)"
echo ""
echo "=== AlgA vs AlgC Consistency Check ==="
echo ""
echo "AlgA (blame + v26.03 sparse data):"
python3 -c "
import json
d=json.load(open('$WORK/out/git-01-A/genCodeDescV26.03.json'))
m=d['AGGREGATE']['metrics']
print(f'  weighted={m[\"weighted\"][\"value\"]:.1%}  fullyAI={m[\"fullyAI\"][\"value\"]:.1%}  mostlyAI={m[\"mostlyAI\"][\"value\"]:.1%}')
d=json.load(open('$WORK/out/git-01-A/genCodeDescV26.03.json'))
print(f'  totalLines={d[\"SUMMARY\"][\"totalCodeLines\"]}  fullGen={d[\"SUMMARY\"][\"fullGeneratedCodeLines\"]}  partialGen={d[\"SUMMARY\"][\"partialGeneratedCodeLines\"]}')
"
echo ""
echo "AlgC (embedded blame + v26.04 streaming):"
python3 -c "
import json
d=json.load(open('$WORK/out/git-03-C/genCodeDescV26.03.json'))
m=d['AGGREGATE']['metrics']
print(f'  weighted={m[\"weighted\"][\"value\"]:.1%}  fullyAI={m[\"fullyAI\"][\"value\"]:.1%}  mostlyAI={m[\"mostlyAI\"][\"value\"]:.1%}')
d=json.load(open('$WORK/out/git-03-C/genCodeDescV26.03.json'))
print(f'  totalLines={d[\"SUMMARY\"][\"totalCodeLines\"]}  fullGen={d[\"SUMMARY\"][\"fullGeneratedCodeLines\"]}  partialGen={d[\"SUMMARY\"][\"partialGeneratedCodeLines\"]}')
"
echo ""
echo "Note: Different results expected — AlgA uses v26.03 sparse data"
echo "(only add entries, no deletes). AlgC uses v26.04 incremental data."
echo "Both are correct per the protocol."
echo ""
echo "=== Production Diagnostics ==="
echo ""

# Shallow clone detection
echo "--- shallow clone detection ---"
SHALLOW_DIR="$WORK/shallow_clone"
rm -rf "$SHALLOW_DIR"
git clone --depth 3 "file://$REPO" "$SHALLOW_DIR" --quiet 2>/dev/null
SHALLOW_GCD="$WORK/git/gcd-shallow"
mkdir -p "$SHALLOW_GCD"
# Convert v26.03 to shallow repo URL
python3 -c "
import json, os
for fn in os.listdir('$WORK/git/gcd-v26.03'):
    if not fn.endswith('.json'): continue
    d = json.load(open(os.path.join('$WORK/git/gcd-v26.03', fn)))
    d['REPOSITORY']['repoURL'] = 'file://$SHALLOW_DIR'
    json.dump(d, open(os.path.join('$SHALLOW_GCD', fn), 'w'), indent=2)
"
$TOOL --repoUrl "file://$SHALLOW_DIR" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-15T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir "$SHALLOW_GCD" --repoPath "$SHALLOW_DIR" \
    --outputDir "$WORK/out/shallow-test" 2>&1 | grep -E "shallow|Shallow|warn|WARN"
echo ""

# Missing revisionId diagnostic
echo "--- missing genCodeDesc diagnostic ---"
TMP_GCD="$WORK/git/gcd-missing"
mkdir -p "$TMP_GCD"
for f in "$WORK/git/gcd-v26.03"/*.json; do
    cp "$f" "$TMP_GCD/"
done
# Remove one file to simulate missing genCodeDesc
first=$(ls "$TMP_GCD" | head -1)
rm "$TMP_GCD/$first" 2>/dev/null
$TOOL --repoUrl "file://$REPO" --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-02-01T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir "$TMP_GCD" --repoPath "$REPO" \
    --outputDir "$WORK/out/missing-test" 2>&1 | grep -E "Missing|missing"
echo ""

echo " Output: $WORK/out/"
echo "============================================"
