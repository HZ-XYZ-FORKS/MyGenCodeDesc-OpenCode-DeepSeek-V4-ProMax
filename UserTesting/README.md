# User Testing Manual — `aggregateGenCodeDesc`

## What You Will Do

Run `aggregateGenCodeDesc` against a real Git repo to measure AI-generated code ratio. The demo covers all 12 deployment cells from [README_UserGuide.md](../README_UserGuide.md).

## Prerequisites

- macOS / Linux with `git` on PATH
- Python 3.10+
- (Optional) `svn` for SVN cells
- (Optional) `pip3 install orjson` for faster processing

## Quick Start (5 minutes)

```bash
# 1. Setup the demo environment
cd UserTesting/
chmod +x setup_demo.sh run_demo.sh
./setup_demo.sh

# 2. Run all 12 cells
./run_demo.sh

# 3. View results
ls -la demo_work/out/cell-03-git-local-C/
python3 -c "
import json
d = json.load(open('demo_work/out/cell-03-git-local-C/genCodeDescV26.03.json'))
print(json.dumps(d['AGGREGATE']['metrics'], indent=2))
"
```

## What setup_demo.sh Creates

| Asset | Path | Purpose |
|-------|------|---------|
| Git repo (10 commits) | `demo_work/repo/` | Source of truth for blame/diff |
| genCodeDesc v26.04 | `demo_work/gcd-v26.04/` | Input for Algorithm C |
| genCodeDesc v26.03 | `demo_work/gcd-v26.03/` | Input for Algorithms A, B |
| Commit patches | `demo_work/patches/` | Input for Algorithm B replay |
| Output directory | `demo_work/out/` | Results from all 12 cells |

## Manual Verification Steps

### 1. Algorithm C — Hermetic CI (cell 3)

```bash
python3 -m aggregateGenCodeDesc.cli \
  --repoUrl "https://github.com/demo/repo" \
  --repoBranch main \
  --startTime 2026-01-01T00:00:00Z \
  --endTime 2026-04-15T00:00:00Z \
  --threshold 60 \
  --algorithm C --scope A \
  --genCodeDescDir demo_work/gcd-v26.04/ \
  --outputDir demo_work/out/manual/

ls demo_work/out/manual/
# → genCodeDescV26.03.json  commitStart2EndTime.patch
```

**Verify**: Open `genCodeDescV26.03.json` and check that `AGGREGATE.metrics.weighted.value > 0`. No VCS was accessed.

### 2. Algorithm A — Live Blame (cell 1)

```bash
python3 -m aggregateGenCodeDesc.cli \
  --repoUrl "file://$PWD/demo_work/repo" \
  --repoBranch main \
  --startTime 2026-01-01T00:00:00Z \
  --endTime 2026-04-15T00:00:00Z \
  --threshold 60 \
  --algorithm A --scope A \
  --genCodeDescDir demo_work/gcd-v26.03/ \
  --repoPath demo_work/repo/ \
  --outputDir demo_work/out/manual/
```

**Verify**: The tool ran `git blame --porcelain` on each `.py` file. Check that `commitStart2EndTime.patch` contains a real `git diff` output.

### 3. Algorithm B — Diff Replay (cell 2)

```bash
python3 -m aggregateGenCodeDesc.cli \
  --repoUrl "file://$PWD/demo_work/repo" \
  --repoBranch main \
  --startTime 2026-01-01T00:00:00Z \
  --endTime 2026-04-15T00:00:00Z \
  --threshold 60 \
  --algorithm B --scope A \
  --genCodeDescDir demo_work/gcd-v26.03/ \
  --repoPath demo_work/repo/ \
  --commitPatchDir demo_work/patches/ \
  --outputDir demo_work/out/manual/
```

**Verify**: The tool replayed all patches in topological order. Check output JSON exists.

### 4. Error Handling

```bash
# Wrong protocol version → exit 2
python3 -m aggregateGenCodeDesc.cli \
  --repoUrl "file://$PWD/demo_work/repo" --repoBranch main \
  --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
  --algorithm A --scope A \
  --genCodeDescDir demo_work/gcd-v26.04/ \
  --outputDir demo_work/out/err/ 2>&1
echo "Exit code: $?"  # → 2

# Duplicate revision → exit 2 (default policy)
mkdir -p demo_work/gcd-dup
cp demo_work/gcd-v26.04/*.json demo_work/gcd-dup/
cp "$(ls demo_work/gcd-v26.04/*.json | head -1)" demo_work/gcd-dup/dup.json
python3 -m aggregateGenCodeDesc.cli \
  --repoUrl "https://github.com/demo/repo" --repoBranch main \
  --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
  --algorithm C --scope A \
  --genCodeDescDir demo_work/gcd-dup/ \
  --outputDir demo_work/out/err2/ 2>&1
echo "Exit code: $?"  # → 2
```

### 5. Logging Levels

```bash
python3 -m aggregateGenCodeDesc.cli \
  --repoUrl "https://github.com/demo/repo" --repoBranch main \
  --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
  --algorithm C --scope A --threshold 60 \
  --genCodeDescDir demo_work/gcd-v26.04/ \
  --outputDir demo_work/out/ \
  --logLevel DEBUG 2>&1 | head -20
```

## 12-Cell Coverage

| # | Cell | run_demo.sh test | Manual command above |
|---|------|:---:|:---:|
| 1 | git · local · A | cell-01-git-local-A | Step 2 |
| 2 | git · local · B | cell-02-git-local-B | Step 3 |
| 3 | git · local · C | cell-03-git-local-C | Step 1 |
| 4 | git · remote · A | cell-04-git-remote-A | (same as Step 2, fire:// URL) |
| 5 | git · remote · B | — | `--commitPatchDir` + `file://` URL |
| 6 | git · remote · C | — | same as Step 1 |
| 7 | svn · local · A | cell-07-svn-local-A | (svn required) |
| 8 | svn · local · B | — | svn diff patches |
| 9 | svn · local · C | — | same as Step 1 |
| 10 | svn · remote · A | — | svn blame via URL |
| 11 | svn · remote · B | — | svn diff patches |
| 12 | svn · remote · C | — | same as Step 1 |

## Expected Output JSON

```json
{
  "protocolVersion": "26.03",
  "codeAgent": "aggregateGenCodeDesc",
  "AGGREGATE": {
    "metrics": {
      "weighted":  {"value": 0.77, "numerator": 7.7},
      "fullyAI":   {"value": 0.50, "numerator": 5},
      "mostlyAI":  {"value": 0.80, "numerator": 8, "threshold": 60}
    },
    "diagnostics": {
      "missingRevisions": [],
      "duplicateRevisions": [],
      "clockSkewDetected": false,
      "warnings": []
    }
  }
}
```

## Clean Up

```bash
rm -rf demo_work/
```
