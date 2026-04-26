# User Guide — `aggregateGenCodeDesc`

End-user facing guide for the `aggregateGenCodeDesc` tool.
Defines **WHEN** you run it, **WHERE** inputs/outputs live, and **HOW** to invoke each of the 12 (VCS × access × algorithm) cells.

Each fork of this BASE implements this contract in its chosen language (Python / C++ / Rust) and CLI convention.

- Related docs: [README.md](README.md) · [README_UserStories.md](README_UserStories.md) · [README_AlgABC.md](README_AlgABC.md) · [README_Protocol.md](README_Protocol.md)

---

## 1. Overview

`aggregateGenCodeDesc` analyzes code surviving in the repository snapshot at `endTime` and calculates AI involvement using three distinct metrics:

1. **Weighted mode**: `Σ(genRatio / 100) / totalLines`
2. **Fully AI mode**: `count(genRatio == 100) / totalLines`
3. **Mostly AI mode**: `count(genRatio >= threshold) / totalLines`

The tool is invoked by a **codebase maintainer** who wants to measure how much AI-generated code was introduced in a time window.

---

## 2. Inputs

### 2.1 Mandatory arguments

Every fork must accept the following mandatory CLI arguments. Argument names use lower camel case after the `--` prefix.

| CLI argument | Meaning |
| --- | --- |
| `--repoUrl` | Git or SVN repository URL. For local mode, a filesystem path or `file://` URL. Maps to protocol field `REPOSITORY.repoURL`. |
| `--repoBranch` | Git branch name, or SVN path (e.g. `trunk`, `branches/rel-1.0`). |
| `--startTime` | Window start, inclusive (ISO 8601: `2026-01-01T00:00:00Z`). |
| `--endTime` | Window end, inclusive (ISO 8601). |
| `--genCodeDescDir` | Directory containing the sequence of genCodeDesc JSON files for this window. See §2.2. |

### 2.2 `--genCodeDescDir` contract

The directory contains **a sequence of genCodeDesc JSON files**, one per revision, covering `[startTime, endTime]` on `repoBranch`.

- **One protocol version per directory.** All files MUST be **v26.03** OR all **v26.04**. Mixed versions are rejected with exit code `2`.
- **Discovery** — every `*.json` file in the directory is loaded, parsed, and validated.
- **Ordering** — sorted by `revisionTimestamp` ascending (Alg C). Alg A/B use the repo's own topological order; the dir only provides `genRatio` lookup.
- **Identity** — each file's `REPOSITORY.repoURL` + `repoBranch` + `revisionId` must match the window's repo + branch. Mismatches → validation error per AC-006-2.
- **Algorithm compatibility**:

  | Algorithm | v26.03 | v26.04 |
  |---|---|---|
  | A (live blame) | ✅ | ❌ reject |
  | B (diff replay) | ✅ | ❌ reject |
  | C (embedded blame) | ❌ reject | ✅ required |

- **Missing revision policy** — when a revision in the window has no matching genCodeDesc file:
  - Alg A/B: treat lines as `genRatio=0` (unattributed). Configurable: `abort` or `zero` or `skip`.
  - Alg C: chain break — configurable: `abort` or `ignore`.
- **Duplicate revisionId policy** — configurable: `reject` (default) or `last-wins`.
- **Clock-skew policy** (Alg C only) — non-monotonic `revisionTimestamp` configurable: `abort` or `ignore`.

### 2.3 Optional and as-needed arguments

All other CLI arguments are optional, or are used only when the selected mode, algorithm, scope, output behavior, or validation policy needs them.

| CLI argument | Default / when needed | Meaning |
| --- | --- | --- |
| `--threshold` | As needed | Integer 0..100. Used by the *Mostly AI* mode. |
| `--algorithm` | As needed | Line-origin discovery strategy: `A`, `B`, or `C` (see [README_AlgABC.md](README_AlgABC.md)). |
| `--scope` | As needed | File/path filter: `A`, `B`, `C`, or `D` (see [README_Protocol.md](README_Protocol.md) — Scope Definitions). |
| `--outputDir` | As needed | Directory where output artifacts are written (created if missing). See §3. |
| `--repoPath` | none | **Alg A only.** Path to a local working copy of the repository. If not given and `--repoUrl` is remote, the tool auto-clones. |
| `--commitPatchDir` | none | **Alg B only.** Directory holding per-revision unified diff files for offline replay. See §2.4. |
| `--blameWhitespace` | `respect` | **Alg A, Git only.** `respect` or `ignore` (cf. `git blame -w`). See AC-004-3. |
| `--renameDetection` | `basic` | **Alg A/B, Git only.** `off` / `basic` (`-M`) / `aggressive` (`-M -C -C`). |
| `--logLevel` | `Info` | Stderr logging verbosity: `Debug`, `Info`, `Warning`, `Error`. See §2.5. |
| `--onMissing` | Alg-dependent | Missing genCodeDesc policy. See §2.2. |
| `--onDuplicate` | `reject` | Duplicate revisionId policy. See §2.2. |
| `--onClockSkew` | `abort` | Clock skew policy for Alg C. See §2.2. |

Protocol version is auto-detected from the first file in `genCodeDescDir`; all files must share that version.

### 2.4 `--commitPatchDir` contract (Alg B)

- **Only consumed by Alg B.** Ignored (with a warning) by Alg A and Alg C.
- One file per revision in `[startTime, endTime]`, named `<revisionId>.patch`, covering that revision's full change set against its parent on `repoBranch`.
- A single `<revisionId>.patch` may contain multiple file diff sections, and each file diff section may contain multiple hunks (`@@ ... @@`). Alg B must replay every file section and every hunk in the patch.
- The directory is scanned for `*.patch` files.
- Ordering: Alg B builds the patch replay sequence from VCS history metadata, not from directory iteration, file modification time, or filename sorting.
  - Git: replay commits in parent-before-child topological order on `repoBranch`. Commit time is used to select the `[startTime, endTime]` window and may be used as a deterministic tie-breaker, but it must not override parent order.
  - SVN: replay revisions on `repoBranch` by ascending server revision number, after filtering revisions by server timestamp in `[startTime, endTime]`.
- Missing revisions fall under `--onMissing`; duplicates under `--onDuplicate`.
- Makes Alg B reproducible and network-free once this directory is populated.

### 2.5 `--logLevel` semantics

| Level | What is logged |
|---|---|
| `Debug` | Everything in `Info` **plus internal debugging detail** (parser tokens, raw VCS command lines, per-file timings, hash-map stats, rejected candidates). Very verbose — for tool developers. |
| `Info` (default) | **File loading** events (each genCodeDesc / diff file opened, parsed, accepted or rejected), **line-by-line state transfer** (per-line origin lookups, add/delete set transitions in Alg C, diff-hunk line-position tracking in Alg B), and the **final summary** (denominator, three metrics, diagnostics). |
| `Warning` | Only warnings and errors (missing/duplicate revisions, clock skew, mixed versions, degraded results). No per-file or per-line output. |
| `Error` | Only fatal errors that abort processing. |

---

## 3. Output

`outputDir` receives **two artifacts**:

| File (fixed name) | What it is |
|---|---|
| `genCodeDescV26.03.json` | Aggregate result in genCodeDescProtoV26.03-shaped JSON (§3.1). |
| `commitStart2EndTime.patch` | Single cumulative unified diff covering `[startTime, endTime]` on `repoBranch` (§3.2). |

Both files are produced by **all three algorithms** (A / B / C).

### 3.1 `genCodeDescV26.03.json`

Shape follows **[`Protocols/genCodeDescProtoV26.03.json`](Protocols/genCodeDescProtoV26.03.json)** — same field names, same SUMMARY / DETAIL / REPOSITORY structure. The aggregate result reuses the protocol so downstream consumers that already understand a per-revision genCodeDesc record also understand the aggregate.

Mapping from metric to protocol fields:

| Protocol field | Aggregate meaning |
|---|---|
| `protocolVersion` | `"26.03"` (the output envelope version; independent of the input `genCodeDescDir` version). |
| `codeAgent` | `"myCodeAgentName"`. |
| `REPOSITORY.repoURL` / `repoBranch` | Echoed from input arguments. |
| `REPOSITORY.revisionId` | `"aggregate:<startTime>..<endTime>"` — a synthetic id identifying the window. |
| `SUMMARY.totalCodeLines` | Denominator — count of all in-window live code lines, including manual/unattributed lines that may be omitted from `DETAIL`. |
| `SUMMARY.fullGeneratedCodeLines` | Count of lines with `genRatio == 100` (numerator of *Fully AI*). |
| `SUMMARY.partialGeneratedCodeLines` | Count of lines with `0 < genRatio < 100`. |
| `SUMMARY.totalDocLines` / `fullGeneratedDocLines` / `partialGeneratedDocLines` | Same, restricted to doc files (Scope C/D). For code and doc counts, `total >= fullGenerated + partialGenerated`; the difference is manual/unattributed lines with effective `genRatio=0`. |
| `DETAIL[].fileName` | Each in-window live file that has emitted attribution entries. Files with only omitted manual/unattributed lines may be absent. |
| `DETAIL[].codeLines[]` / `docLines[]` | Sparse v26.03 attribution entries. Lines with `genRatio > 0` are emitted as `{lineLocation, genRatio, genMethod}` (or `lineRange` when contiguous). Manual/unattributed lines may be omitted; absence means effective `genRatio=0`. |

**Aggregate-only extensions** (added as sibling top-level keys; ignored by vanilla v26.03 consumers):

| Field | Meaning |
|---|---|
| `AGGREGATE.window` | `{startTime, endTime}`. |
| `AGGREGATE.parameters` | `{algorithm, scope, threshold, inputProtocolVersion}`. |
| `AGGREGATE.metrics.weighted` | `{value, numerator}` — `Σ(genRatio/100) / totalCodeLines`. |
| `AGGREGATE.metrics.fullyAI` | `{value, numerator}` — `fullGeneratedCodeLines / totalCodeLines`. |
| `AGGREGATE.metrics.mostlyAI` | `{value, numerator, threshold}` — `count(genRatio >= T) / totalCodeLines`. |
| `AGGREGATE.diagnostics` | `{missingRevisions[], duplicateRevisions[], clockSkewDetected, warnings[]}`. |

Example (10 in-window live code lines, generated `genRatio = [100,100,100,100,100, 80,80,80, 30]`, plus one omitted manual line with effective `genRatio=0`, threshold 60):

```json
{
  "protocolName": "generatedTextDesc",
  "protocolVersion": "26.03",
  "codeAgent": "aggregateGenCodeDesc",

  "SUMMARY": {
    "totalCodeLines": 10,
    "fullGeneratedCodeLines": 5,
    "partialGeneratedCodeLines": 4,
    "totalDocLines": 0,
    "fullGeneratedDocLines": 0,
    "partialGeneratedDocLines": 0
  },

  "DETAIL": [
    {
      "fileName": "src/auth.py",
      "codeLines": [
        {"lineRange": {"from": 1, "to": 5}, "genRatio": 100, "genMethod": "codeCompletion"},
        {"lineRange": {"from": 6, "to": 8}, "genRatio":  80, "genMethod": "vibeCoding"},
        {"lineLocation": 9,                 "genRatio":  30, "genMethod": "vibeCoding"}
      ]
    }
  ],

  "REPOSITORY": {
    "vcsType": "git",
    "repoURL": "https://github.com/acme/foo",
    "repoBranch": "main",
    "revisionId": "aggregate:2026-01-01T00:00:00Z..2026-04-01T00:00:00Z"
  },

  "AGGREGATE": {
    "window": {
      "startTime": "2026-01-01T00:00:00Z",
      "endTime":   "2026-04-01T00:00:00Z"
    },
    "parameters": {
      "algorithm": "C",
      "scope": "A",
      "threshold": 60,
      "inputProtocolVersion": "26.04"
    },
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

*All runtime logs go to stderr so they do not interfere with capturing or piping the JSON output.*

### 3.2 `commitStart2EndTime.patch`

A **single cumulative unified diff** representing the net change from the window's first parent to the window's end revision on `repoBranch`. Equivalent to:

```text
git diff <revJustBeforeStartTime>..<revAtEndTime> -- <scope paths>
```

- **Format**: standard unified diff (`diff --git ...` / `---` / `+++` / `@@` hunks). Applyable with `git apply` or `patch -p1`.
- **Scope**: filtered by `scope` argument (same file filter applied to the JSON denominator).
- **Generated by all three algorithms**:

  | Algorithm | How the patch is produced |
  |---|---|
  | A | Produced via `git diff` / `svn diff` on the working copy or remote endpoint. |
  | B | Concatenation of the per-revision patches from `commitPatchDir` in topological/parent order, separated by `# --- commit <rev> ---` markers. |
  | C | Synthesised from the v26.04 embedded add-line entries: one synthetic `+` per in-window surviving add, serialised as a unified-diff-shaped document. No VCS access required. |

- **Purpose**: pairs with the JSON — JSON answers *"what ratio?"*, the patch answers *"which lines were counted?"*, so the pair is auditable without re-accessing the repo.
- **Header**: the patch begins with a comment block identifying `repoURL`, `repoBranch`, `startTime`, `endTime`, `algorithm`, `scope`, and the synthetic `aggregate:<start>..<end>` id.

---

## 4. Scenario matrix — 12 cells

Axes: **VCS** = `git` | `svn` · **Access** = `local` | `remote` · **Algorithm** = `A` | `B` | `C`.

The cells below describe prerequisites, a minimal example command shape, and known limits.

### 4.1 git × local

#### git · local · A (live blame)

- **Prereqs**: working copy on disk; `git` on PATH; `genCodeDescDir` is v26.03.
- **Example**:
  ```
  aggregateGenCodeDesc \
    --repoUrl file:///srv/repos/foo --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir ./gcd-v26.03/ --repoPath /srv/repos/foo \
    --outputDir ./out/
  ```
- **Limits**: shallow clone invalidates blame (AC-005-4).

#### git · local · B (offline diff replay)

- **Prereqs**: working copy; `commitPatchDir` populated with `<revisionId>.patch` files.
- **Example**:
  ```
  aggregateGenCodeDesc \
    --repoUrl file:///srv/repos/foo --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm B --scope A \
    --genCodeDescDir ./gcd-v26.03/ --repoPath /srv/repos/foo \
    --commitPatchDir ./diffs/ --outputDir ./out/
  ```
- **Limits**: deep rename chains inflate state (README scale table).

#### git · local · C (embedded blame, v26.04 only)

- **Prereqs**: **no VCS access needed**; `genCodeDescDir` must contain v26.04.
- **Example**:
  ```
  aggregateGenCodeDesc \
    --repoUrl https://github.com/acme/foo --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm C --scope A \
    --genCodeDescDir ./gcd-v26.04/ --outputDir ./out/
  ```
- **Limits**: trust shifts fully to codeAgent write-time correctness.

### 4.2 git × remote

#### git · remote · A

- **Prereqs**: `--repoPath` or the tool auto-clones to temp directory.
- **Example** (auto-clone):
  ```
  aggregateGenCodeDesc \
    --repoUrl https://github.com/acme/foo --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir ./gcd-v26.03/ --outputDir ./out/
  ```
- **Limits**: shallow clones invalidate blame (AC-005-4).

#### git · remote · B

- **Prereqs**: `commitPatchDir` with pre-exported patches; `--repoPath` for ordering.
- **Example**:
  ```
  aggregateGenCodeDesc \
    --repoUrl https://github.com/acme/foo --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm B --scope A \
    --genCodeDescDir ./gcd-v26.03/ --repoPath /local/clone \
    --commitPatchDir ./diffs/ --outputDir ./out/
  ```
- **Limits**: patch preparation is the caller's responsibility.

#### git · remote · C

- **Prereqs**: **no network access**. `genCodeDescDir` is v26.04.
- **Example**:
  ```
  aggregateGenCodeDesc \
    --repoUrl https://github.com/acme/foo --repoBranch main \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm C --scope A \
    --genCodeDescDir ./gcd-v26.04/ --outputDir ./out/
  ```
- **Recommended** for air-gapped / batch scenarios.

### 4.3 svn × local

#### svn · local · A

- **Prereqs**: working copy; `svn` on PATH; `genCodeDescDir` is v26.03.
- **Example**:
  ```
  aggregateGenCodeDesc \
    --repoUrl file:///srv/svn/repo --repoBranch /trunk \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir ./gcd-v26.03/ --repoPath /srv/svn/wc \
    --outputDir ./out/
  ```
- **Limits**: `svn blame` imprecision on merge-originated lines.

#### svn · local · B

- **Prereqs**: working copy; per-revision patches via `svn diff -cN`.
- **Example**:
  ```
  aggregateGenCodeDesc \
    --repoUrl file:///srv/svn/repo --repoBranch /trunk \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm B --scope A \
    --genCodeDescDir ./gcd-v26.03/ --repoPath /srv/svn/wc \
    --commitPatchDir ./svn-diffs/ --outputDir ./out/
  ```
- **Limits**: no cross-file move detection.

#### svn · local · C

- Identical to `git · local · C` — VCS is not consulted.

### 4.4 svn × remote

#### svn · remote · A

- **Prereqs**: working copy (checked out ahead of time); `svn` on PATH.
- **Example**:
  ```
  aggregateGenCodeDesc \
    --repoUrl svn://svn.example.com/repo --repoBranch /trunk \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm A --scope A \
    --genCodeDescDir ./gcd-v26.03/ --repoPath /local/svn-checkout \
    --outputDir ./out/
  ```
- **Limits**: the tool should not contact the svn server directly.

#### svn · remote · B

- **Prereqs**: pre-exported patches in `commitPatchDir`; `svn` on PATH for ordering.
- **Example**:
  ```
  aggregateGenCodeDesc \
    --repoUrl svn://svn.example.com/repo --repoBranch /trunk \
    --startTime 2026-01-01T00:00:00Z --endTime 2026-04-01T00:00:00Z \
    --threshold 60 --algorithm B --scope A \
    --genCodeDescDir ./gcd-v26.03/ --repoPath /local/svn-checkout \
    --commitPatchDir ./svn-diffs/ --outputDir ./out/
  ```
- **Limits**: patch preparation is the caller's responsibility.

#### svn · remote · C

- Identical to `git · remote · C` — VCS is not consulted.

### 4.5 Cell summary

| # | VCS | Access | Alg | Needs repo at runtime? | Best for |
|---|---|---|---|---|---|
| 1 | git | local | A | yes | development loops |
| 2 | git | local | B | yes (patches) | reproducible offline replays |
| 3 | git | local | C | **no** | hermetic CI |
| 4 | git | remote | A | yes (working copy) | on-demand audits |
| 5 | git | remote | B | no (patches only) | offline batch |
| 6 | git | remote | C | **no** | air-gapped / large-scale |
| 7 | svn | local | A | yes | svn dev loops |
| 8 | svn | local | B | yes (patches) | svn offline replays |
| 9 | svn | local | C | **no** | hermetic CI (svn) |
| 10 | svn | remote | A | yes (working copy) | on-demand audits (svn) |
| 11 | svn | remote | B | no (patches only) | offline batch (svn) |
| 12 | svn | remote | C | **no** | air-gapped (svn) |

---

## 5. Validation & error taxonomy

Mapped to [README_UserStories.md](README_UserStories.md) US-006:

| Condition | Flag | Default | Exit |
|---|---|---|---|
| Missing genCodeDesc for a revision in window | `--onMissing` | `zero` (A/B), `abort` (C) | 0 (ZERO/SKIP) / 2 (ABORT) |
| `REPOSITORY` mismatch in a file | — | always reject | 2 |
| Duplicate `revisionId` | `--onDuplicate` | `reject` | 2 (REJECT) / 0 (LAST-WINS) |
| Non-monotonic `revisionTimestamp` (Alg C) | `--onClockSkew` | `abort` | 2 (ABORT) / 0 (IGNORE) |
| `genRatio` outside 0..100 | — | always reject | 2 |
| Mixed protocol versions in dir | — | always reject | 2 |
| Alg C given v26.03, or Alg A/B given v26.04 | — | always reject | 2 |

---

## 6. Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Runtime/IO error (network, disk, VCS CLI failure, uncaught exception) |
| 2 | Input/validation error (bad args, bad genCodeDesc, mixed versions, alg/version mismatch) |

---

## 7. Quick-start examples by algorithm

### Algorithm A: Live Blame (Git, local working copy)

```text
aggregateGenCodeDesc \
  --repoUrl https://github.com/acme/myrepo \
  --repoBranch main \
  --startTime 2026-01-01T00:00:00Z \
  --endTime 2026-04-01T00:00:00Z \
  --threshold 60 \
  --algorithm A --scope A \
  --genCodeDescDir ./gcd-v26.03/ \
  --outputDir ./out/
```

### Algorithm B: Offline Diff Replay (Git or SVN)

```text
aggregateGenCodeDesc \
  --repoUrl https://svn.example.com/repo \
  --repoBranch /trunk \
  --startTime 2026-02-01T00:00:00Z \
  --endTime 2026-02-28T23:59:59Z \
  --threshold 60 \
  --algorithm B --scope A \
  --genCodeDescDir ./gcd-v26.03/ \
  --commitPatchDir ./diffs/ \
  --outputDir ./out/
```

### Algorithm C: Embedded Blame (v26.04 only, no VCS access)

```text
aggregateGenCodeDesc \
  --repoUrl https://github.com/acme/myrepo \
  --repoBranch main \
  --startTime 2026-01-01T00:00:00Z \
  --endTime 2026-04-01T00:00:00Z \
  --threshold 60 \
  --algorithm C --scope A \
  --genCodeDescDir ./gcd-v26.04/ \
  --outputDir ./out/
```

---

## 8. How forks implement this guide

1. Fork `MyGenCodeDescBase` for a specific CodeAgent & LLM combination.
2. Implement `aggregateGenCodeDesc` in your chosen language (Python / C++ / Rust).
3. Your fork's `README.md` references this guide and documents:
    - Any additional compatibility flags beyond the mandatory lower-camel-case CLI flags above.
    - Which of the 12 cells are supported (all 12 is the target; AlgC-only forks may skip cells 1–2, 7–8).
    - Known limitations per cell (e.g. "Alg B is not yet implemented").
    - Policy defaults for `--onMissing`, `--onDuplicate`, `--onClockSkew`.
4. All 64 acceptance criteria in [README_UserStories.md](README_UserStories.md) are test targets.
