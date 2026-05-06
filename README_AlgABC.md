# Algorithm A, B, and C — WHAT & WHY

## ======>>>SHARED GOAL<<<======

All three algorithms answer the **same question**:

> For the in-scope code or document lines that survive in the logical repository snapshot at `endTime`, and whose current text form was introduced by a revision timestamp inside `[startTime, endTime]`, how much is attributable to AI?

Equivalently, after scope filtering, the measured population is:

```text
(startTime..endTime diff lines) ∩ (lines alive at endTime)
```

The algorithms differ in **how they discover line origins** -- not in what they measure. Scope selection decides whether the result is code-only, document-only, or both; the line-origin rule stays the same.

---

## ======>>>ONE-GLANCE COMPARISON<<<======

| | **Algorithm A** | **Algorithm B** | **Algorithm C** |
| --- | --- | --- | --- |
| **Core technique** | Live VCS blame at `endTime` | Ordered offline diff replay | Embedded VCS blame in genCodeDesc |
| **Repository access at runtime** | Required for blame | Not required after ordered patches and order metadata are exported | Not required |
| **genCodeDesc version** | v26.03 | v26.03 | v26.04 |
| **Needs per-commit diff patch** | No | Yes | No |
| **Processing order authority** | Live `endTime` snapshot | VCS history order | `REPOSITORY.revisionTimestamp` |
| **Correctness authority** | Live VCS blame | Rebuilt line lineage from patches | Real VCS blame captured by codeAgent at write time |
| **Production status** | Production quality | Narrow paths active | Planned |

---

## ======>>>ALGORITHM A — Blame-Based End-Snapshot Attribution<<<======

### A: WHAT It Is

Algorithm A is the **primary, production-quality baseline**. It starts from the live file snapshot at `endTime`, runs `git blame` or `svn blame` on every surviving in-scope line, and uses the blame result to discover which revision last introduced the current text form of that line. Lines whose origin revision timestamp falls inside `[startTime, endTime]` are counted.

For each counted line, Algorithm A joins the blame result to the matching per-revision genCodeDesc v26.03 record. The lookup should use the line's **origin coordinates** from blame, not blindly use its current `endTime` file path and line number. A line can survive a rename or shift to a different current line number after nearby insertions/deletions, while the v26.03 record still describes the file and line positions as they existed in the origin revision.

Join contract for one live line:

```text
live line at endTime
  -> blame gives origin revisionId + origin file path + origin line/range + origin timestamp
  -> if origin timestamp is inside [startTime, endTime], load genCodeDescV26.03 for origin revisionId
  -> look up DETAIL by origin file path + origin line/range
  -> use genRatio/genMethod, or effective genRatio=0 if sparse v26.03 has no matching entry
```

### A: Flow Diagram

```mermaid
flowchart TD
  A1["Inputs: repoUrl, repoBranch, startTime, endTime, genCodeDescDir"]
  A2["Open live working copy at endTime"]
  A3["Run git blame or svn blame on surviving in-scope lines"]
  A4{"Origin timestamp inside [startTime, endTime]?"}
  A5["Find v26.03 genCodeDesc record by origin revision"]
  A6{"DETAIL matches origin file path + origin line/range?"}
  A7["Use recorded genRatio and genMethod"]
  A8["Treat as manual/unattributed with genRatio=0"]
  A9["Aggregate Weighted, Fully AI, and Mostly AI metrics"]
  A10["Ignore line for this metric window"]

  A1 --> A2 --> A3 --> A4
  A4 -- "No" --> A10
  A4 -- "Yes" --> A5 --> A6
  A6 -- "Yes" --> A7 --> A9
  A6 -- "No" --> A8 --> A9
```

### A: Typical Walkthrough Examples

Read Algorithm A as **live-line first**, not commit first: inspect the live snapshot at `endTime`, ask blame where each live line came from, then join that origin to genCodeDesc.

#### Example 1: Add-only commit

`C0` before the window has:

```python
def total(items):
    return sum(items)
```

`C1` inside `[startTime, endTime]` adds one live line:

```python
def total(items):
    return sum(items)

print(total([1, 2, 3]))
```

Blame at `endTime`:

```text
C0  src/a.py:1  def total(items):
C0  src/a.py:2      return sum(items)
C1  src/a.py:4  print(total([1, 2, 3]))
```

Algorithm A keeps only the `C1` line, loads `genCodeDescV26.03(C1)`, looks up `src/a.py:4`, and uses that entry's `genRatio`. The denominator is `1`.

#### Example 2: Modify existing line

`C0` wrote:

```python
def total(items):
    return sum(items)
```

`C1` inside the window rewrites line 2:

```python
def total(items):
    return sum(items or [])
```

Blame at `endTime`:

```text
C0  src/a.py:1  def total(items):
C1  src/a.py:2      return sum(items or [])
```

Algorithm A counts the current line 2 and looks up `genCodeDescV26.03(C1) -> src/a.py:2`. The old `C0` text is not alive, so the old line does not participate in the metric.

#### Example 3: Pure rename

`C1` inside the window renames `old.py` to `new.py` without changing text.

Blame at `endTime` usually traces through the rename:

```text
C0  origin old.py:1  current new.py:1  def total(items):
C0  origin old.py:2  current new.py:2      return sum(items)
```

Algorithm A sees that the line origins are still `C0`, not `C1`, so `C1` contributes `0` denominator lines. A path-only change is not a new line-content origin.

#### Example 4: Current position differs from origin position

`C1` inside the window creates `src/a.py`:

```python
def total(items):          # C1 line 1
    return sum(items)      # C1 line 2, genRatio=100
```

Later, before `endTime`, `C2` renames the file and inserts a header:

```python
# math helpers             # current line 1

def total(items):          # current line 3
    return sum(items)      # current line 4
```

Blame for current line 4 should still point back to the origin line in `C1`:

```text
current src/math_utils.py:4
  -> origin revision C1, origin file src/a.py, origin line 2
```

Algorithm A must look up `genCodeDescV26.03(C1) -> src/a.py:2`, not `src/math_utils.py:4`. This is why origin coordinates from blame matter.

### A: WHY It Works

- **Directly answers the P0 metric** on the live snapshot.
- Rename and move detection is handled by **mature VCS blame implementations** when the selected VCS and options support it.
- Low logical risk: blame is the **authoritative source** of line origin — no partial reconstruction needed.
- Works for both Git and SVN.

### A: Known Pitfalls

- Requires **live repository access** -- a local checkout or equivalent working copy must be present at runtime.
- Blame performance can be slow on **very large repositories** with many large files.
- Correctness depends on VCS blame quality — SVN with complex mergeinfo may return imprecise results.
- The implementation must run blame in a mode that exposes or reconstructs enough origin coordinates for v26.03 lookup. If only current file path and current line number are available, rename and line-number-shift cases can be misjoined.
- A v26.03 record must exist for every counted origin revision to produce exact attribution; otherwise the configured missing-record policy applies.

---

## ======>>>ALGORITHM B — Incremental Lineage Reconstruction Without Blame<<<======

### B: WHAT It Is

Algorithm B replays an ordered sequence of **per-revision unified-diff patches** from `--commitPatchDir` to reconstruct line ownership incrementally. Instead of asking the VCS "who last changed this line?", it simulates the history by applying diffs in VCS history order and tracking which revision introduced each surviving line. Once a surviving line's origin revision is known, the algorithm looks up `genRatio` from the matching v26.03 genCodeDesc record; if the sparse v26.03 `DETAIL` has no matching line entry, the line is treated as manual/unattributed with effective `genRatio=0`. **No live blame** is needed at runtime; full offline execution requires the patch files, the commit/revision order metadata, and enough exported replay context to apply the selected patch chain deterministically through `toCommit`.

Ordering is part of the correctness contract:

- Git replay order is parent-before-child topological order on `repoBranch`; commit timestamp may filter the window or break ties, but it must not override parent order.
- SVN replay order is ascending server revision number after timestamp filtering.
- Directory iteration order, file name sorting, and patch file modification time are never replay order.

### B: Flow Diagram

```mermaid
flowchart TD
  B1["Inputs: genCodeDescDir v26.03 + commitPatchDir + order/replay context"]
  B2["Build replay sequence from VCS history metadata"]
  B3{"VCS type?"}
  B4["Git: parent-before-child topological order"]
  B5["SVN: ascending server revision number"]
  B6["Replay each revision patch"]
  B7["Apply every file diff section and every hunk"]
  B8["Track origin revision for added, moved, and surviving lines"]
  B9["Inspect simulated surviving in-scope lines at endTime"]
  B10{"Origin timestamp inside [startTime, endTime]?"}
  B11["Find matching v26.03 genCodeDesc record"]
  B12{"DETAIL has matching lineLocation or lineRange?"}
  B13["Use recorded genRatio and genMethod"]
  B14["Treat as manual/unattributed with genRatio=0"]
  B15["Aggregate metrics"]
  B16["Ignore line for this metric window"]

  B1 --> B2 --> B3
  B3 -- "git" --> B4 --> B6
  B3 -- "svn" --> B5 --> B6
  B6 --> B7 --> B8 --> B9 --> B10
  B10 -- "No" --> B16
  B10 -- "Yes" --> B11 --> B12
  B12 -- "Yes" --> B13 --> B15
  B12 -- "No" --> B14 --> B15
```

### B: WHY It Exists

- Enables **offline analysis** without live blame or network access when patch/order artifacts are already available.
- Useful when blame is operationally slow or unavailable.
- Diff artifacts can be **pre-indexed and queried cheaply**.
- Can compute **history-process metrics** beyond live-snapshot attribution (e.g., added-then-deleted AI lines, churn, survival rate).
- Enables **deterministic replay** in test environments.

### B: Known Pitfalls

- Effectively **rebuilds a partial blame engine** -- any gap in replay logic produces wrong attributions silently.
- One unified-diff patch file per replayed revision must exist before the run. Each patch file is the full commit diff: it can cover multiple files, and each file diff can contain multiple hunks. Every file section and every hunk must be replayed.
- Patch order must come from VCS history metadata, not from the filesystem.
- If the replay starts at `fromCommit`, the implementation must still have a deterministic starting state or equivalent exported context; unchanged pre-window lines remain outside the metric denominator unless a replayed patch modifies them.
- Merge-aware lineage replay is **complex** — production readiness for merge-heavy histories requires explicit TDD.
- SVN path-copy and mergeinfo semantics introduce replay edge cases not yet fully covered.
- Still needs per-revision genCodeDesc v26.03 — only the blame step is removed.

---

## ======>>>ALGORITHM C — Embedded Blame, Pure genCodeDesc<<<======

### C: WHAT It Is

Algorithm C is a planned offline algorithm that requires **no repository access** and **no diff artifacts** at runtime. The codeAgent writes one v26.04 genCodeDesc record per revision. Each record contains only changed lines: `changeType=add` entries with `genRatio`, `genMethod`, and real VCS blame, plus `changeType=delete` entries that identify the exact origin line or origin line range to remove. A downstream consumer sorts records by `REPOSITORY.revisionTimestamp`, processes every record with `revisionTimestamp <= endTime`, applies deletes before adds within each record, expands ranges inclusively, and accumulates the surviving-line set. It then filters surviving add entries by embedded `blame.timestamp` inside `[startTime, endTime]` and reads `genRatio` directly.

### C: Flow Diagram

```mermaid
flowchart TD
  C1["Inputs: genCodeDescDir v26.04"]
  C2["Sort records by REPOSITORY.revisionTimestamp"]
  C3["Process every record with revisionTimestamp <= endTime"]
  C4["Expand lineRange and originalLineRange inclusively"]
  C5["Apply delete entries first"]
  C6["Apply add entries to surviving_lines"]
  C7["Keep surviving add entries after accumulation"]
  C8{"blame.timestamp inside [startTime, endTime]?"}
  C9["Read genRatio and genMethod directly from add entry"]
  C10["Ignore line for this metric window"]
  C11["Aggregate Weighted, Fully AI, and Mostly AI metrics"]

  C1 --> C2 --> C3 --> C4 --> C5 --> C6 --> C7 --> C8
  C8 -- "Yes" --> C9 --> C11
  C8 -- "No" --> C10
```

### C: WHY It Exists

- **Zero VCS access** at analysis time -- no checkout, no subprocess, no network.
- **Zero diff artifacts** needed -- no `commitPatchDir`.
- Per-commit files are bounded to changed lines rather than full snapshots; high-churn commits can still produce large records.
- Works for both Git-origin and SVN-origin blame when the codeAgent captured real VCS blame at write time.
- Ideal for **air-gapped, edge, or large-scale batch** deployments.

### C: Known Pitfalls

- Must process **every v26.04 record** needed to reconstruct the branch state up to `endTime`, including records before `startTime`. A missing record in that chain corrupts the surviving-line set.
- `REPOSITORY.revisionTimestamp` is **mandatory** for processing order.
- Within one record, delete entries are applied before add entries, regardless of array order.
- Delete entries must reference the **exact blame origin** using `revisionId + originalFilePath + originalLine` or `revisionId + originalFilePath + originalLineRange`; a mismatch silently leaves ghost lines.
- Embedded blame must be **real VCS blame** captured at write time. Synthetic, inferred, or manually edited blame breaks the contract.
- No independent VCS verification is possible during analysis — **correctness is fully trusted from the codeAgent**.
- If a force-push or amend happens after the file was written, the embedded blame is **silently stale**.

---

## ======>>>IRREPLACEABLE ADVANTAGES<<<======

Each algorithm has something the others **cannot substitute**:

- **Algorithm A** is irreplaceable for **authority and accountability** — it is the only one that relies directly on live VCS blame as the authoritative fact source, enabling trace-back to raw repository proof.
- **Algorithm B** is irreplaceable for **patch-driven historical replay** — deterministic re-execution from the same patch artifacts, history-window experiments, and process reconstruction that A and C cannot provide.
- **Algorithm C** is irreplaceable for **minimal-runtime-dependency offline scalability** — it simultaneously achieves zero repository access and zero diff replay, a deployment advantage the others cannot match.

---

## ======>>>HOW THEY RELATE<<<======

The three algorithms are **semantically equivalent** for the same scenario when their required artifacts are complete and their policy choices match. The choice is driven by what is available and what trade-offs are acceptable:

| Decision Factor | Choose A | Choose B | Choose C |
| --- | --- | --- | --- |
| Live repo checkout available | Yes | — | — |
| Need authoritative VCS proof | Yes | — | — |
| Repo access is expensive/impossible | — | Yes | Yes |
| Have pre-exported diff patches, order metadata, and replay context | — | Yes | — |
| Want history-process metrics | — | Yes | — |
| Want minimal runtime dependencies | — | — | Yes |
| Air-gapped / edge deployment | — | — | Yes |
| codeAgent produces v26.04 with embedded blame | — | — | Yes |

---

## ======>>>HOLISTIC TRADE-OFFS<<<======

Scores 1–5, higher is better:

| Dimension | Alg A | Alg B | Alg C |
| --- | --- | --- | --- |
| Low Coupling | 2 | 4 | 5 |
| Low Complexity | 4 | 2 | 3 |
| Low Storage Footprint | 5 | 2 | 3 |
| High Maintainability | 4 | 2 | 3 |
| High Scalability | 3 | 3 | 5 |
| High Fault Tolerance | 3 | 2 | 3 |
| Correctness Explainability | 5 | 3 | 3 |

---

## ======>>>SOURCE<<<======

Distilled from [AggregateGenCodeDesc — README_IntroAlgABC.md](https://github.com/EnigmaWU/MyLLM_Arena/blob/main/MyStartups/AggregateGenCodeDesc/README_IntroAlgABC.md).

---

## ======>>>APPENDIX: WHAT IS BLAME<<<======

All three algorithms rely on **line origin attribution**, commonly called **blame** -- the concept that for any line in a file, you can ask: **which revision last introduced this line's current text content?**

Blame is **per-line**, not per-commit. In a file with 3 lines, each line may come from a different revision:

```text
file at commit abc123:
  line 1: "int x = 0;"   → blame: revision 111aaa (3 months ago)
  line 2: "x += 1;"      → blame: revision 222bbb (1 week ago)
  line 3: "return x;"    → blame: revision abc123 (this commit)
```

This is why blame can handle **rename** (traces through file path changes when supported/configured), **merge** (follows the VCS blame rules for merged history), and **rewrite** (points to the newer revision that introduced the current text).

How each algorithm gets line-origin attribution:

| Algorithm | Line-origin source |
| --- | --- |
| A | Live `git blame` / `svn blame` at analysis time |
| B | Reconstructed by replaying ordered diffs (rebuilt partial blame) |
| C | Embedded in v26.04 at write time by the codeAgent |
