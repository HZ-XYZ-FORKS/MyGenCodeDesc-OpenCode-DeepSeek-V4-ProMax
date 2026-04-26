#!/bin/bash
set -e

echo "=== Setup: aggregateGenCodeDesc Demo ==="
echo ""

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="$BASE_DIR/demo_work"
REPO_DIR="$WORK_DIR/repo"
GENCODE_V2604="$WORK_DIR/gcd-v26.04"
GENCODE_V2603="$WORK_DIR/gcd-v26.03"
OUT_DIR="$WORK_DIR/out"
PATCH_DIR="$WORK_DIR/patches"

mkdir -p "$REPO_DIR" "$GENCODE_V2604" "$GENCODE_V2603" "$OUT_DIR" "$PATCH_DIR"

cd "$REPO_DIR"
git init -b main
git config user.name "Demo User"
git config user.email "demo@example.com"

# --- Step 1: Build a 10-commit demo repo ---

echo "" > main.py
git add -A && git commit -m "C0: init" --date "2026-01-01T00:00:00Z"

# C1: Add content with multi-hunk across main.py + utils.py
for i in $(seq 1 30); do echo "line $i"; done > main.py
echo "# utils" > utils.py
echo "def helper_a(): return 1" >> utils.py
echo "" >> utils.py
echo "def helper_b(): return 2" >> utils.py
echo "" >> utils.py
echo "# end utils" >> utils.py
git add main.py utils.py
git commit -m "C1: add main.py + utils.py (multi-file, multi-hunk)" --date "2026-01-15T00:00:00Z"
REV_C1=$(git rev-parse HEAD)

# C2: Rename a file
echo "# utilities" > utils.py
git add utils.py
git commit -m "C2: add utils.py" --date "2026-01-20T00:00:00Z"
git mv utils.py helpers.py
git commit -m "C3: rename utils -> helpers" --date "2026-01-25T00:00:00Z"

# C4: Create feature branch + merge
git checkout -b feature
echo "def feature_a(): return 1" > feature.py
git add feature.py && git commit -m "C4: feature branch commit" --date "2026-02-01T00:00:00Z"
REV_C4=$(git rev-parse HEAD)
git checkout main
GIT_COMMITTER_DATE="2026-02-15T00:00:00Z" git merge feature --no-ff -m "C5: merge feature"

# C6: Cherry-pick from feature
echo "cherry-picked content" > cherry.py
git add cherry.py && git commit -m "C6: cherry-pick" --date "2026-03-01T00:00:00Z"
REV_C6=$(git rev-parse HEAD)

# C7: Revert a line
python3 -c "
lines = open('main.py').readlines()
lines[4] = 'line 5 - HUMAN EDIT\n'
open('main.py', 'w').writelines(lines)
"
git add -A && git commit -m "C7: human edit line 5" --date "2026-03-10T00:00:00Z"

# C8: Multi-hunk modification — change two sections of main.py
python3 -c "
lines = open('main.py').readlines()
lines[4] = 'line 5 - HUMAN EDIT\n'
lines[14] = 'line 15 - AI REWRITE\n'
open('main.py', 'w').writelines(lines)
"
git add -A && git commit -m "C8: multi-hunk edit (lines 5 + 15)" --date "2026-03-15T00:00:00Z"

# C9: Restore both lines
python3 -c "
lines = open('main.py').readlines()
lines[4] = 'line 5\n'
lines[14] = 'line 15\n'
open('main.py', 'w').writelines(lines)
"
git add -A && git commit -m "C9: revert edits" --date "2026-03-20T00:00:00Z"

# C9: Delete a file
git rm helpers.py && git commit -m "C9: delete helpers.py" --date "2026-04-01T00:00:00Z"

echo ""
echo "Repo built: $REPO_DIR ($(git log --oneline | wc -l | tr -d ' ') commits)"

# --- Step 2: Generate genCodeDesc v26.04 files ---

python3 -c "
import json, subprocess, os

repo = '$REPO_DIR'
out_v4 = '$GENCODE_V2604'
out_v3 = '$GENCODE_V2603'
branch = 'main'
url = 'file://$REPO_DIR'

commits = subprocess.run(['git', 'log', '--reverse', '--format=%H %ct'], cwd=repo,
                         capture_output=True, text=True).stdout.strip().split('\n')

def iso(ts):
    day = int(ts) // 86400 % 28 + 1
    hour = int(ts) // 3600 % 24
    return f'2026-01-{day:02d}T{hour:02d}:00:00Z'

for commit_line in commits:
    if not commit_line.strip(): continue
    parts = commit_line.split()
    rev = parts[0]
    ts = iso(parts[1])

    numstat = subprocess.run(['git', 'diff-tree', '--no-commit-id', '-r', '--numstat', rev],
                              cwd=repo, capture_output=True, text=True).stdout.strip()
    if not numstat:
        continue

    detail_v4 = []
    detail_v3 = []
    for line in numstat.split('\n'):
        fields = line.split('\t')
        if len(fields) < 3: continue
        added, deleted, fname = fields[0], fields[1], fields[2]
        if not fname.endswith('.py'): continue
        added_n = int(added) if added != '-' else 0
        deleted_n = int(deleted) if deleted != '-' else 0

        # v26.04 entries
        entries = []
        for i in range(deleted_n):
            entries.append({
                'changeType': 'delete',
                'blame': {'revisionId': rev, 'originalFilePath': fname, 'originalLine': i + 1}
            })
        for i in range(added_n):
            entries.append({
                'changeType': 'add',
                'lineLocation': i + 1,
                'genRatio': 80 if (i % 10) < 7 else 0,
                'genMethod': 'vibeCoding' if (i % 10) < 7 else 'Manual',
                'blame': {
                    'revisionId': rev, 'originalFilePath': fname,
                    'originalLine': i + 1, 'timestamp': ts
                }
            })
        if entries:
            detail_v4.append({'fileName': fname, 'codeLines': entries})

        # v26.03 entries (add only)
        v3_entries = []
        for e in entries:
            if e['changeType'] == 'add':
                v3_entries.append({
                    'lineLocation': e['lineLocation'],
                    'genRatio': e['genRatio'],
                    'genMethod': e['genMethod']
                })
        if v3_entries:
            detail_v3.append({'fileName': fname, 'codeLines': v3_entries})

    if detail_v4:
        record = {
            'protocolName': 'generatedTextDesc',
            'protocolVersion': '26.04',
            'codeAgent': 'DemoCodeAgent',
            'REPOSITORY': {
                'vcsType': 'git', 'repoURL': url, 'repoBranch': branch,
                'revisionId': rev, 'revisionTimestamp': ts
            },
            'SUMMARY': {
                'totalCodeLines': sum(len(e['codeLines']) for e in detail_v4),
                'fullGeneratedCodeLines': 0, 'partialGeneratedCodeLines': 0,
                'totalDocLines': 0, 'fullGeneratedDocLines': 0, 'partialGeneratedDocLines': 0
            },
            'DETAIL': detail_v4
        }
        with open(os.path.join(out_v4, f'{rev}.json'), 'w') as f:
            json.dump(record, f, indent=2)

    if detail_v3:
        record_v3 = {
            'protocolName': 'generatedTextDesc',
            'protocolVersion': '26.03',
            'codeAgent': 'DemoCodeAgent',
            'REPOSITORY': {'vcsType': 'git', 'repoURL': url, 'repoBranch': branch, 'revisionId': rev},
            'SUMMARY': {'totalCodeLines': sum(len(e['codeLines']) for e in detail_v3),
                         'fullGeneratedCodeLines': 0, 'partialGeneratedCodeLines': 0,
                         'totalDocLines': 0, 'fullGeneratedDocLines': 0, 'partialGeneratedDocLines': 0},
            'DETAIL': detail_v3
        }
        with open(os.path.join(out_v3, f'{rev}.json'), 'w') as f:
            json.dump(record_v3, f, indent=2)
"
echo "genCodeDesc v26.04 generated: $GENCODE_V2604 ($(ls $GENCODE_V2604 | wc -l | tr -d ' ') files)"
echo "genCodeDesc v26.03 generated: $GENCODE_V2603 ($(ls $GENCODE_V2603 | wc -l | tr -d ' ') files)"

# --- Step 4: Generate per-revision patches for AlgB ---

python3 -c "
import subprocess, os

repo = '$REPO_DIR'
patch_dir = '$PATCH_DIR'

commits = subprocess.run(
    ['git', 'log', '--topo-order', '--reverse', '--first-parent', '--format=%H'],
    cwd=repo, capture_output=True, text=True
).stdout.strip().split('\n')

for rev in commits:
    if not rev: continue
    diff = subprocess.run(
        ['git', 'format-patch', '-1', '--stdout', '--unified=3', '--first-parent', rev],
        cwd=repo, capture_output=True, text=True
    ).stdout
    if diff.strip():
        with open(os.path.join(patch_dir, f'{rev}.patch'), 'w') as f:
            f.write(diff)
"
echo "Patches generated: $PATCH_DIR"
echo ""
echo "=== Setup Complete ==="
echo "Demo repo:       $REPO_DIR"
echo "genCodeDesc v26.04: $GENCODE_V2604"
echo "genCodeDesc v26.03: $GENCODE_V2603"
echo "Patches:           $PATCH_DIR"
echo ""
echo "Run: ./run_demo.sh"
