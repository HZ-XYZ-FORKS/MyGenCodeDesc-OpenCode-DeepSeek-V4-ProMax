# User Stories — WHAT Each Fork Must Satisfy

This document defines **testable acceptance criteria** for every fork of MyGenCodeDescBase.
If your fork passes all AC scenarios below, your `aggregateGenCodeDesc` implementation is correct.

Format follows the [create-user-story](/.github/skills/create-user-story/SKILL.md) skill:
`AS A / I WANT / SO THAT` + `GIVEN / WHEN / THEN` with AC categories.

---

## Roles

| Role | Definition | Source |
|------|-----------|--------|
| **codebase maintainer** | Person who uses `aggregateGenCodeDesc` to measure AI-generated code ratio across revisions. | [README.md](README.md) — "WHAT WE WANT" |
| **tool developer** | Developer who builds, debugs, and maintains a fork of `aggregateGenCodeDesc`. | [README.md](README.md) — "WHAT WE WANT" |

---

## US-001: Core Metric Calculation

AS A codebase maintainer,
I WANT to compute the AI-generation ratio of live code lines changed within a time window,
SO THAT I can quantify how much of the codebase is AI-generated.

### AC-001-1: [Typical] Weighted mode calculates sum of genRatio

```gherkin
Scenario: [Typical] Weighted AI ratio for mixed-authorship lines
  GIVEN 10 in-window live lines with genRatio values [100,100,100,100,100,80,80,80,30,0]
  WHEN aggregateGenCodeDesc computes the Weighted metric
  THEN the result is 77.0%
```

### AC-001-2: [Typical] Fully AI mode counts only genRatio==100

```gherkin
Scenario: [Typical] Fully AI ratio counts only fully-generated lines
  GIVEN 10 in-window live lines with genRatio values [100,100,100,100,100,80,80,80,30,0]
  WHEN aggregateGenCodeDesc computes the Fully AI metric
  THEN the result is 50.0%
```

### AC-001-3: [Typical] Mostly AI mode counts genRatio >= threshold

```gherkin
Scenario: [Typical] Mostly AI ratio with threshold 60
  GIVEN 10 in-window live lines with genRatio values [100,100,100,100,100,80,80,80,30,0]
  AND the threshold is 60
  WHEN aggregateGenCodeDesc computes the Mostly AI metric
  THEN the result is 80.0%
```

### AC-001-4: [Edge] All lines are human-written

```gherkin
Scenario: [Edge] Zero AI ratio when all lines are human-written
  GIVEN 50 in-window live lines all with genRatio 0
  WHEN aggregateGenCodeDesc computes all three metrics
  THEN Weighted is 0.0%
  AND Fully AI is 0.0%
  AND Mostly AI is 0.0%
```

### AC-001-5: [Edge] All lines are fully AI-generated

```gherkin
Scenario: [Edge] 100% ratio when all lines are AI-generated
  GIVEN 50 in-window live lines all with genRatio 100
  WHEN aggregateGenCodeDesc computes all three metrics
  THEN Weighted is 100.0%
  AND Fully AI is 100.0%
  AND Mostly AI is 100.0%
```

### AC-001-6: [Edge] No lines changed within the time window

```gherkin
Scenario: [Edge] No in-window lines yields zero denominator
  GIVEN a repository with 1000 live lines
  AND none of them were added or modified within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric
  THEN the result is 0.0% for all modes
  AND totalLines is 0
```

### AC-001-7: [Typical] Sparse DETAIL treats omitted lines as manual

```gherkin
Scenario: [Typical] v26.03 DETAIL omits manual lines while SUMMARY counts them
  GIVEN SUMMARY.totalCodeLines is 10
  AND SUMMARY.fullGeneratedCodeLines is 5
  AND SUMMARY.partialGeneratedCodeLines is 4
  AND DETAIL contains entries for only the 9 generated lines
  WHEN aggregateGenCodeDesc validates and computes the aggregate metrics
  THEN the record is accepted because totalCodeLines >= fullGeneratedCodeLines + partialGeneratedCodeLines
  AND the omitted in-window live line is treated as genRatio 0 and manual/unattributed
  AND Weighted is 77.0%
  AND Fully AI is 50.0%
  AND Mostly AI is 80.0% when threshold is 60
```

---

## US-002: File-Level Conditions

AS A codebase maintainer,
I WANT file renames, deletes, copies, and moves to be handled correctly,
SO THAT the AI ratio is not distorted by file-level operations.

### AC-002-1: [Typical] Pure rename preserves line attribution

```gherkin
Scenario: [Typical] File renamed without content change
  GIVEN file "old.py" with 100 lines was renamed to "new.py" in a commit within [startTime, endTime]
  AND no content was changed
  WHEN aggregateGenCodeDesc computes the metric
  THEN all 100 lines keep their original genRatio from the commit that wrote them
  AND no lines are double-counted
```

### AC-002-2: [Typical] Rename + modify attributes changed lines to new commit

```gherkin
Scenario: [Typical] File renamed and partially modified
  GIVEN file "old.py" renamed to "new.py"
  AND 20 of 100 lines were modified in the same commit
  WHEN aggregateGenCodeDesc computes the metric
  THEN the 80 unchanged lines keep their original genRatio
  AND the 20 modified lines use the genRatio from the rename commit's genCodeDesc
```

### AC-002-3: [Typical] Deleted file contributes zero to metric

```gherkin
Scenario: [Typical] File deleted within the window
  GIVEN file "removed.py" with 50 AI-generated lines (genRatio 100) existed before startTime
  AND the file was deleted in a commit within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric at endTime
  THEN "removed.py" contributes 0 lines to the metric
  AND none of its lines appear in the live snapshot
```

### AC-002-4: [Edge] File copied to new path

```gherkin
Scenario: [Edge] File duplicated via copy
  GIVEN file "lib.py" with 100 lines exists
  AND "lib.py" was copied to "lib_v2.py" in a commit within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric
  THEN all lines in "lib_v2.py" are attributed to the copy commit
  AND "lib.py" lines retain their original attribution
```

---

## US-003: Commit-Level Conditions

AS A codebase maintainer,
I WANT merge, squash, cherry-pick, revert, amend, and rebase operations to produce correct attribution,
SO THAT the metric is accurate regardless of branch workflow.

### AC-003-1: [Typical] Merge commit traces through to original revision

```gherkin
Scenario: [Typical] Merge commit preserves original line origins
  GIVEN branch "feature" has 50 AI-generated lines (genRatio 100) from commit F1
  AND branch "main" merges "feature" in merge commit M1 within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric
  THEN the 50 lines are attributed to commit F1 (not M1)
  AND genRatio comes from F1's genCodeDesc
```

### AC-003-2: [Typical] Squash merge attributes all lines to the squash commit

```gherkin
Scenario: [Typical] Squash merge collapses attribution
  GIVEN 3 commits (C1, C2, C3) with varying genRatio are squash-merged into commit S1
  AND S1 is within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric
  THEN all surviving lines are attributed to S1
  AND genRatio comes from S1's genCodeDesc
```

### AC-003-3: [Typical] Cherry-pick creates independent attribution

```gherkin
Scenario: [Typical] Cherry-picked commit has its own genCodeDesc
  GIVEN commit C1 on branch "feature" has 30 AI-generated lines
  AND C1 is cherry-picked to "main" as commit C2 within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric for "main"
  THEN lines are attributed to C2 (not C1)
  AND genRatio comes from C2's genCodeDesc
```

### AC-003-4: [Typical] Revert commit removes AI attribution

```gherkin
Scenario: [Typical] Reverted AI lines are gone
  GIVEN commit C1 added 20 AI-generated lines (genRatio 100)
  AND commit R1 reverts C1 within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric at endTime
  THEN the 20 reverted lines contribute 0 to the metric
```

### AC-003-5: [Edge] Amend / force-push orphans old genCodeDesc

```gherkin
Scenario: [Edge] Amended commit replaces revisionId
  GIVEN commit C1 (revisionId "aaa") has genCodeDesc written
  AND C1 is amended to C2 (revisionId "bbb") via force-push
  WHEN aggregateGenCodeDesc looks up genCodeDesc for the amended commit
  THEN C1's genCodeDesc (revisionId "aaa") is orphaned
  AND only C2's genCodeDesc (revisionId "bbb") is used
```

### AC-003-6: [Edge] Rebase replays commits with new revisionIds

```gherkin
Scenario: [Edge] Rebased commits need regenerated genCodeDesc
  GIVEN commits C1, C2, C3 are rebased onto new base
  AND new commits C1', C2', C3' have different revisionIds
  WHEN aggregateGenCodeDesc searches for genCodeDesc of C1', C2', C3'
  THEN it uses genCodeDesc matching the new revisionIds
  AND genCodeDesc for old C1, C2, C3 revisionIds are ignored
```

---

## US-004: Line-Level Conditions

AS A codebase maintainer,
I WANT line-level ownership transfers and edge cases to be handled correctly,
SO THAT per-line genRatio accurately reflects current authorship.

### AC-004-1: [Typical] AI line edited by human transfers ownership

```gherkin
Scenario: [Typical] Human edits an AI-generated line
  GIVEN line 42 of "auth.py" was AI-generated (genRatio 100) in commit C1
  AND a human modifies line 42 in commit C2 within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric
  THEN line 42's genRatio comes from C2's genCodeDesc
  AND the old genRatio 100 from C1 no longer applies
```

### AC-004-2: [Typical] Human line rewritten by AI transfers ownership

```gherkin
Scenario: [Typical] AI rewrites a human-written line
  GIVEN line 10 of "utils.py" was human-written (genRatio 0) in commit C1
  AND AI rewrites line 10 in commit C2 (genRatio 100) within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric
  THEN line 10's genRatio is 100 (from C2's genCodeDesc)
```

### AC-004-3: [Edge] Whitespace-only change may or may not transfer blame

```gherkin
Scenario: [Edge] Whitespace-only change with default blame settings
  GIVEN line 5 of "config.py" was AI-generated (genRatio 100) in commit C1
  AND commit C2 only changes indentation of line 5
  WHEN aggregateGenCodeDesc computes the metric
  THEN the result depends on VCS blame behavior (git blame -w policy)
  AND the fork documents its whitespace policy explicitly
```

### AC-004-4: [Edge] Line ending change (CRLF↔LF) affects entire file

```gherkin
Scenario: [Edge] CRLF to LF conversion changes all lines
  GIVEN file "data.txt" has 500 lines with mixed genRatio
  AND a .gitattributes change converts all line endings (CRLF→LF) in commit C2
  WHEN aggregateGenCodeDesc computes the metric
  THEN all 500 lines are attributed to commit C2
  AND genRatio comes from C2's genCodeDesc for all lines
```

### AC-004-5: [Edge] Identical content re-added gets new attribution

```gherkin
Scenario: [Edge] Deleted and re-added identical line has new origin
  GIVEN line "return 42" was deleted in commit C1
  AND the same text "return 42" was re-added in commit C2 within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric
  THEN the line is attributed to C2 (not the original commit)
  AND genRatio comes from C2's genCodeDesc
```

### AC-004-6: [Edge] Line moved within file gets new attribution

```gherkin
Scenario: [Edge] Line moved from position 10 to position 50
  GIVEN line "x = compute()" at position 10 in commit C1
  AND the line is moved to position 50 in commit C2 within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric
  THEN the line at position 50 is attributed to commit C2
```

---

## US-005: Branch and History Conditions

AS A codebase maintainer,
I WANT the metric to correctly handle long-lived branches, multiple merges, and time window boundaries,
SO THAT multi-branch workflows do not produce incorrect results.

### AC-005-1: [Typical] Lines outside the time window are excluded

```gherkin
Scenario: [Typical] Line committed before startTime is excluded
  GIVEN line 1 of "main.py" was committed at T0 (before startTime)
  AND the line is still live at endTime with genRatio 100
  WHEN aggregateGenCodeDesc computes the metric for [startTime, endTime]
  THEN line 1 is NOT included in the metric calculation
```

### AC-005-2: [Typical] Multiple merges in window — each line has one origin

```gherkin
Scenario: [Typical] Several branches merged within the window
  GIVEN branches A, B, C are all merged into main within [startTime, endTime]
  AND each branch contributed distinct lines with known genRatio
  WHEN aggregateGenCodeDesc computes the metric
  THEN each line has exactly one blame origin
  AND no line is double-counted across merges
```

### AC-005-3: [Edge] Long-lived branch with deep divergence

```gherkin
Scenario: [Edge] Feature branch diverged 6 months from main
  GIVEN branch "feature" diverged from "main" 6 months ago
  AND "feature" is merged into "main" within [startTime, endTime]
  WHEN aggregateGenCodeDesc computes the metric
  THEN blame traces each line to its actual origin commit on whichever branch
  AND the metric includes only lines whose origin commit is within [startTime, endTime]
```

### AC-005-4: [Edge] Shallow clone limits blame accuracy (AlgA/B)

```gherkin
Scenario: [Edge] Shallow clone causes blame to hit boundary
  GIVEN a Git repository cloned with --depth 50
  AND some line origins are beyond the 50-commit boundary
  WHEN aggregateGenCodeDesc uses AlgA (live blame)
  THEN lines beyond the boundary are shown as originating from the boundary commit
  AND the fork documents this as a known limitation
```

### AC-005-5: [Edge] Submodule has separate genCodeDesc chain

```gherkin
Scenario: [Edge] Code in a Git submodule
  GIVEN the repository includes a submodule at path "libs/crypto"
  AND the submodule has its own repoURL and genCodeDesc chain
  WHEN aggregateGenCodeDesc computes the metric for the parent repo
  THEN the submodule's lines are NOT included in the parent's metric
  AND the submodule requires its own independent aggregateGenCodeDesc run
```

---

## US-006: Destructive and Edge Conditions

AS A codebase maintainer,
I WANT lost, corrupted, or duplicate genCodeDesc records to be detected and handled safely,
SO THAT the metric result is reliable or explicitly flagged as degraded.

### AC-006-1: [Fault] Missing genCodeDesc for a revision

```gherkin
Scenario: [Fault] One revision's genCodeDesc is missing
  GIVEN commit C5 is within [startTime, endTime]
  AND no genCodeDesc record exists for C5
  WHEN aggregateGenCodeDesc processes the window
  THEN lines from C5 are treated as genRatio 0 (unattributed) for AlgA/B
  AND for AlgC the missing record is reported as a chain break error
```

### AC-006-2: [Fault] Corrupted genCodeDesc with wrong revisionId

```gherkin
Scenario: [Fault] genCodeDesc has mismatched REPOSITORY fields
  GIVEN a genCodeDesc file claims revisionId "abc123"
  AND the REPOSITORY.repoURL does not match the target repository
  WHEN aggregateGenCodeDesc validates the record
  THEN the record is rejected with a validation error
  AND the error identifies the mismatched field
```

### AC-006-3: [Misuse] Duplicate genCodeDesc for the same revision

```gherkin
Scenario: [Misuse] Two genCodeDesc records for the same revisionId
  GIVEN two genCodeDesc files both have revisionId "abc123"
  AND they contain different genRatio values for the same lines
  WHEN aggregateGenCodeDesc processes the window
  THEN the duplicate is detected
  AND processing either rejects both or uses the last-written record (fork-defined policy)
  AND the duplicate is logged as a warning
```

### AC-006-4: [Fault] Clock skew causes incorrect ordering (AlgC)

```gherkin
Scenario: [Fault] Non-monotonic timestamps in AlgC
  GIVEN commit C1 has revisionTimestamp 2026-01-03T00:00:00Z
  AND commit C2 has revisionTimestamp 2026-01-02T00:00:00Z (earlier than C1 but committed after)
  WHEN aggregateGenCodeDesc uses AlgC which sorts by revisionTimestamp
  THEN the accumulation order is wrong
  AND the fork either rejects non-monotonic sequences OR documents the inaccuracy
```

### AC-006-5: [Misuse] genRatio value outside valid range

```gherkin
Scenario: [Misuse] genRatio is 150 in a genCodeDesc record
  GIVEN a genCodeDesc DETAIL entry has genRatio 150
  WHEN aggregateGenCodeDesc validates the entry
  THEN the entry is rejected with error "genRatio must be 0-100"
  AND no partial data from the invalid record is used
```

### AC-006-6: [Typical] Mandatory CLI argument names are lower camel case

```gherkin
Scenario: [Typical] Mandatory CLI arguments map to runtime and protocol identity
  GIVEN aggregateGenCodeDesc is invoked with --repoUrl, --repoBranch, --startTime, --endTime, and --genCodeDescDir
  WHEN the tool parses runtime arguments
  THEN --repoUrl is used as the requested repository identity and echoed as REPOSITORY.repoURL in the aggregate output
  AND --repoBranch, --startTime, --endTime, and --genCodeDescDir are used consistently for validation, filtering, and input discovery
  AND these five lower-camel-case CLI flags are the BASE mandatory contract for argument parsing
  AND all other CLI flags are optional or as-needed
```

---

## US-007: Git vs SVN Differences

AS A codebase maintainer,
I WANT the metric to work correctly for both Git and SVN repositories,
SO THAT forks targeting SVN are not broken by Git-specific assumptions.

### AC-007-1: [Typical] Git revision identity is SHA hash

```gherkin
Scenario: [Typical] Git revisionId format
  GIVEN the target repository uses Git
  WHEN a genCodeDesc record is created
  THEN revisionId is a 40-character (SHA-1) or 64-character (SHA-256) hex string
  AND the aggregator accepts both formats
```

### AC-007-2: [Typical] SVN revision identity is sequential integer

```gherkin
Scenario: [Typical] SVN revisionId format
  GIVEN the target repository uses SVN
  WHEN a genCodeDesc record is created
  THEN revisionId is a positive integer (e.g., "4217")
  AND the aggregator accepts numeric revisionId
```

### AC-007-3: [Edge] SVN merge blame is imprecise

```gherkin
Scenario: [Edge] SVN blame returns imprecise results after merge
  GIVEN an SVN repository with a branch merged via svn merge
  AND svn:mergeinfo tracks the merge
  WHEN aggregateGenCodeDesc uses svn blame on merged lines
  THEN the fork documents that SVN blame may attribute lines to wrong revisions
  AND this is logged as a known limitation
```

### AC-007-4: [Edge] Rebase/amend are Git-only — SVN ignores them

```gherkin
Scenario: [Edge] SVN fork does not handle rebase
  GIVEN the target repository uses SVN
  WHEN the aggregator checks for rebase or amend conditions
  THEN these conditions are skipped (SVN history is immutable)
  AND no error is raised
```

### AC-007-5: [Edge] SVN branch is a path, not a ref

```gherkin
Scenario: [Edge] SVN repoBranch maps to a path
  GIVEN an SVN repository with branches at /branches/feature-x
  WHEN a genCodeDesc record references repoBranch
  THEN repoBranch contains the SVN path (e.g., "/branches/feature-x")
  AND the aggregator normalizes SVN branch paths correctly
```

---

## US-008: Scale and Performance

AS A codebase maintainer,
I WANT `aggregateGenCodeDesc` to handle the reference scale (1K commits × 100 files × 10K lines),
SO THAT the tool is usable on production-sized repositories.

### AC-008-1: [Performance] AlgA completes within acceptable time

```gherkin
Scenario: [Performance] AlgA at reference scale
  GIVEN 1,000 commits in [startTime, endTime]
  AND 100 files per commit, 10,000 lines per file
  AND ~10,000 distinct files at endTime
  WHEN aggregateGenCodeDesc runs AlgA (live blame)
  THEN the tool completes (correctness over speed — fork documents actual time)
  AND peak memory stays below 1 GB for sequential processing
```

### AC-008-2: [Performance] AlgC processes 200 GB genCodeDesc data

```gherkin
Scenario: [Performance] AlgC streaming at reference scale
  GIVEN 1,000 genCodeDesc files totaling ~200 GB
  AND each file has ~1M DETAIL entries
  WHEN aggregateGenCodeDesc runs AlgC (embedded blame)
  THEN files are streamed in timestamp order (not all loaded at once)
  AND peak memory is bounded by surviving set size (~6 GB)
```

### AC-008-3: [Edge] Zero commits in the window

```gherkin
Scenario: [Edge] Empty time window
  GIVEN [startTime, endTime] contains 0 commits
  WHEN aggregateGenCodeDesc runs
  THEN the result is 0.0% for all modes
  AND totalLines is 0
  AND the tool completes without error
```

### AC-008-4: [Robust] Tool recovers from mid-stream I/O failure

```gherkin
Scenario: [Robust] Disk read fails on one genCodeDesc file
  GIVEN 1,000 genCodeDesc files to process
  AND file #500 is unreadable (disk error)
  WHEN aggregateGenCodeDesc encounters the I/O error
  THEN the error is reported with the file path and revisionId
  AND the tool either aborts with a clear error OR continues with degraded result (fork-defined policy)
  AND no partial/corrupt output is written
```

---

## US-009: Algorithm-Specific Behavior

AS A codebase maintainer,
I WANT each algorithm (A, B, C) to handle its unique line-origin discovery correctly,
SO THAT the metric result is accurate regardless of which algorithm the fork implements.

### AlgA — Live Blame

#### AC-009-1: [Typical] Blame traces through rename via -M

```gherkin
Scenario: [Typical] AlgA follows renamed file via git blame -M
  GIVEN file "old_name.py" was renamed to "new_name.py" in commit C1
  AND line 10 of "new_name.py" was originally written in commit C0
  WHEN aggregateGenCodeDesc runs AlgA with git blame on "new_name.py"
  THEN blame reports line 10's origin as commit C0 (not C1)
  AND genRatio comes from C0's genCodeDesc
```

#### AC-009-2: [Edge] Cross-file move detected via -C -C

```gherkin
Scenario: [Edge] AlgA detects code moved from another file
  GIVEN 30 lines were cut from "source.py" and pasted into "target.py" in commit C1
  AND git blame -C -C is enabled
  WHEN aggregateGenCodeDesc runs AlgA on "target.py"
  THEN the 30 moved lines are attributed to the original commit that wrote them in "source.py"
  AND the fork documents the -C -C behavior and its performance cost
```

#### AC-009-3: [Fault] VCS server unreachable during AlgA analysis

```gherkin
Scenario: [Fault] Remote VCS is down when AlgA runs blame
  GIVEN the target repository is hosted on a remote Git server
  AND the server is unreachable at analysis time
  WHEN aggregateGenCodeDesc runs AlgA and attempts git blame
  THEN the tool reports a clear connection error with the server URL
  AND no partial metric result is written
  AND the tool suggests retrying or using AlgC (no VCS access needed)
```

### AlgB — Diff Replay

#### AC-009-4: [Typical] Sequential multi-file diff replay in topological order

```gherkin
Scenario: [Typical] AlgB replays multi-file, multi-hunk diffs in correct commit order
  GIVEN 5 commits (C1→C2→C3→C4→C5) in [startTime, endTime]
  AND at least one commit patch contains diff sections for both "main.py" and "helper.py"
  AND at least one file diff section contains multiple hunks (`@@ ... @@`)
  WHEN aggregateGenCodeDesc runs AlgB
  THEN diffs are replayed in topological order (C1, C2, C3, C4, C5)
  AND every file diff section and hunk in each commit patch is replayed
  AND directory order, filename sorting, and patch file modification time do not control replay order
  AND the final line-to-origin mapping matches the live file state at endTime
```

#### AC-009-5: [Edge] Line-position tracking through chained renames

```gherkin
Scenario: [Edge] AlgB tracks lines across rename chain
  GIVEN file "v1.py" was renamed to "v2.py" in commit C2
  AND "v2.py" was renamed to "v3.py" in commit C4
  AND line 15 was untouched through both renames
  WHEN aggregateGenCodeDesc runs AlgB replaying diffs C1→C2→C3→C4→C5
  THEN line 15 in "v3.py" at endTime is attributed to the commit that originally wrote it
  AND the rename graph correctly maps v1.py → v2.py → v3.py
```

#### AC-009-6: [Fault] One diff in the chain is missing

```gherkin
Scenario: [Fault] AlgB cannot retrieve diff for commit C3
  GIVEN 5 commits (C1→C2→C3→C4→C5) in [startTime, endTime]
  AND the diff for commit C3 is unavailable (network error or deleted ref)
  WHEN aggregateGenCodeDesc runs AlgB
  THEN the tool reports the missing diff with commit C3's revisionId
  AND the tool either aborts with a chain-break error OR skips C3 with degraded accuracy (fork-defined policy)
  AND no silently incorrect result is produced
```

### AlgC — Embedded Blame (v26.04)

#### AC-009-7: [Typical] Add/delete operations build correct surviving set

```gherkin
Scenario: [Typical] AlgC accumulates surviving lines from add/delete entries
  GIVEN 3 genCodeDesc files (for C1, C2, C3) processed in timestamp order
  AND C1 adds 100 lines to "app.py"
  AND C2 deletes 20 lines and adds 30 lines to "app.py"
  AND C3 deletes 10 lines from "app.py"
  WHEN aggregateGenCodeDesc runs AlgC
  THEN the surviving set for "app.py" has exactly 100 lines (100 - 20 + 30 - 10)
  AND each surviving line's genRatio matches its add entry's genCodeDesc
```

#### AC-009-8: [Edge] Duplicate add entry for same file+line

```gherkin
Scenario: [Edge] AlgC encounters duplicate add for the same line position
  GIVEN genCodeDesc for C1 has an add entry for "app.py" line 42
  AND genCodeDesc for C2 also has an add entry for "app.py" line 42 without a preceding delete
  WHEN aggregateGenCodeDesc runs AlgC
  THEN the duplicate is detected
  AND the tool either rejects the second entry with a warning OR overwrites with the later entry (fork-defined policy)
  AND the inconsistency is logged
```

#### AC-009-9: [Fault] SUMMARY lineCount mismatches actual DETAIL entries

```gherkin
Scenario: [Fault] AlgC detects mismatch between SUMMARY and DETAIL
  GIVEN a genCodeDesc file's SUMMARY claims lineCount 500
  AND the actual DETAIL section contains 487 entries
  WHEN aggregateGenCodeDesc validates the file during AlgC processing
  THEN the mismatch is detected (expected 500, found 487)
  AND the tool reports the discrepancy with the file's revisionId
  AND processing either aborts or continues with a warning (fork-defined policy)
```

---

## US-010: Diagnostics and Logging

AS A tool developer,
I WANT `aggregateGenCodeDesc` to support `--logLevel` with levels DEBUG, INFO, WARN, ERROR,
SO THAT I can inspect runtime behavior and diagnose bugs.

### AC-010-1: [Typical] Default log level is INFO with load/process/summary phases

```gherkin
Scenario: [Typical] Running without --logLevel shows INFO progress
  GIVEN aggregateGenCodeDesc is invoked without --logLevel
  AND the tool processes 10 genCodeDesc files covering 5 files
  WHEN the tool runs
  THEN log output shows three phases with progress:
    - LOAD phase: each genCodeDesc file loaded ("LOAD [3/10] revisionId=abc123 entries=1500")
    - PROCESS phase: each file's line-origin resolution with per-line state
      ("PROCESS file=auth.py line=42 state=ADDED origin=abc123 genRatio=100")
      ("PROCESS file=auth.py line=43 state=DELETED origin=def456")
    - SUMMARY phase: final metric result per file and aggregate
      ("SUMMARY file=auth.py totalLines=100 weighted=58.0% fullyAI=50.0% mostlyAI=80.0%")
      ("SUMMARY aggregate totalLines=500 weighted=65.0% fullyAI=42.0% mostlyAI=71.0%")
  AND log output does NOT include DEBUG-level messages
```

### AC-010-2: [Typical] DEBUG level shows per-file and per-line detail

```gherkin
Scenario: [Typical] --logLevel DEBUG reveals detailed processing steps
  GIVEN aggregateGenCodeDesc is invoked with --logLevel DEBUG
  WHEN the tool processes a genCodeDesc file for commit C1
  THEN log output includes:
    - which algorithm is running (AlgA/B/C)
    - each file being processed with line count
    - each genCodeDesc file loaded with revisionId and entry count
    - line-origin resolution decisions (blame result / diff replay step / add-delete operation)
  AND all DEBUG messages include a timestamp
```

### AC-010-3: [Typical] WARN level logs non-fatal anomalies

```gherkin
Scenario: [Typical] Warnings logged for degraded but non-fatal conditions
  GIVEN aggregateGenCodeDesc encounters a genCodeDesc with SUMMARY/DETAIL mismatch
  AND the fork policy is to continue with warning
  WHEN the tool processes the file
  THEN a WARN-level message is emitted with:
    - the revisionId of the problematic file
    - the nature of the anomaly (e.g., "expected 500 entries, found 487")
  AND processing continues
```

### AC-010-4: [Typical] ERROR level logs fatal failures

```gherkin
Scenario: [Typical] Errors logged when processing must abort
  GIVEN aggregateGenCodeDesc encounters an unreadable genCodeDesc file
  AND the fork policy is to abort on I/O errors
  WHEN the tool processes the file
  THEN an ERROR-level message is emitted with:
    - the file path and revisionId
    - the OS-level error description
  AND the tool exits with a non-zero exit code
  AND no partial output is written
```

### AC-010-5: [Edge] --logLevel ERROR suppresses INFO and WARN

```gherkin
Scenario: [Edge] Minimal output with --logLevel ERROR
  GIVEN aggregateGenCodeDesc is invoked with --logLevel ERROR
  AND processing encounters WARN-level anomalies but no errors
  WHEN the tool completes successfully
  THEN log output contains NO messages (no INFO, no WARN)
  AND only the final metric result is written to stdout
```

### AC-010-6: [Observability] Structured log format for machine parsing

```gherkin
Scenario: [Observability] Log output is structured and parseable
  GIVEN aggregateGenCodeDesc is invoked with --logLevel DEBUG
  WHEN log messages are emitted
  THEN each log line includes: timestamp, level, component, message
  AND the format is consistent (e.g., "2026-04-14T10:30:00Z [DEBUG] [AlgC] Loading genCodeDesc revisionId=abc123 entries=1000")
  AND log output goes to stderr (not mixed with metric result on stdout)
```

### AC-010-7: [Testability] Log level is configurable in tests without CLI

```gherkin
Scenario: [Testability] Unit tests can set log level programmatically
  GIVEN a unit test imports the aggregateGenCodeDesc library
  WHEN the test sets log level to DEBUG via API (not CLI flag)
  THEN DEBUG-level messages are captured in the test output
  AND no global state leaks between test cases
```

| US | Title | AC Count | Categories Covered |
|----|-------|----------|--------------------|
| US-001 | Core Metric Calculation | 7 | Typical, Edge |
| US-002 | File-Level Conditions | 4 | Typical, Edge |
| US-003 | Commit-Level Conditions | 6 | Typical, Edge |
| US-004 | Line-Level Conditions | 6 | Typical, Edge |
| US-005 | Branch and History Conditions | 5 | Typical, Edge |
| US-006 | Destructive and Edge Conditions | 6 | Fault, Misuse, Typical |
| US-007 | Git vs SVN Differences | 5 | Typical, Edge |
| US-008 | Scale and Performance | 4 | Performance, Edge, Robust |
| US-009 | Algorithm-Specific Behavior | 9 | Typical, Edge, Fault |
| US-010 | Diagnostics and Logging | 7 | Typical, Edge, Observability, Testability |
| US-011 | Deployment Topology (12 cells) | 5 | Typical, Edge |
| **Total** | | **64 AC** | |

---

## US-011: Deployment Topology — 12 VCS × Access × Algorithm Cells

AS A codebase maintainer,
I WANT `aggregateGenCodeDesc` to run correctly in every deployment scenario defined in the UserGuide,
SO THAT the tool works across local/remote repos, Git/SVN VCS, and all three algorithms.

### Context

The [UserGuide](README_UserGuide.md) §4 defines 12 deployment cells on axes:
**VCS** = `git` | `svn` · **Access** = `local` | `remote` · **Algorithm** = `A` | `B` | `C`.

Each cell represents a distinct runtime topology. Cells 3, 6, 9, 12 (AlgC) are VCS-free and share the same code path.
The remaining 8 cells require distinct VCS-specific integration.

### Coverage Matrix

| # | Cell | Status | Priority |
|---|------|:---:|----------|
| 1 | git · local · A | ✅ | — |
| 2 | git · local · B | ✅ | — |
| 3 | git · local · C | ✅ | — |
| 4 | git · remote · A | ✅ | — |
| 5 | git · remote · B | ✅ | — |
| 6 | git · remote · C | ✅ | — |
| 7 | svn · local · A | ✅ | — |
| 8 | svn · local · B | ✅ | — |
| 9 | svn · local · C | ✅ | — |
| 10 | svn · remote · A | ✅ | — |
| 11 | svn · remote · B | ✅ | — |
| 12 | svn · remote · C | ✅ | — |

### AC-011-1: [Typical] git · remote · A — auto-clone remote then blame

```gherkin
Scenario: [Typical] Remote Git repo with AlgA
  GIVEN a remote Git repository URL (https:// or git@)
  AND --algorithm A --repoPath is not provided
  WHEN aggregateGenCodeDesc runs
  THEN the tool auto-clones the remote to a temp directory
  AND runs git blame on the cloned working copy
  AND computes metrics correctly
```

### AC-011-2: [Typical] git · remote · B — patches + VCS ordering, no live repo

```gherkin
Scenario: [Typical] Remote Git repo with AlgB and commitPatchDir
  GIVEN --commitPatchDir with per-revision .patch files
  AND --algorithm B
  AND no live repository access (--repoPath not needed)
  WHEN aggregateGenCodeDesc runs
  THEN commits are ordered via git log --topo-order
  AND patches are replayed in correct topological sequence
  AND the final line-to-origin mapping matches the live state at endTime
```

### AC-011-3: [Typical] svn · local · B — SVN diff replay with ascending revision order

```gherkin
Scenario: [Typical] Local SVN repo with AlgB
  GIVEN an SVN working copy at --repoPath
  AND --commitPatchDir with per-revision .patch files named by SVN revision number
  AND --algorithm B
  WHEN aggregateGenCodeDesc runs
  THEN patches are ordered by ascending SVN revision number
  AND every patch is replayed to build the surviving-line set
```

### AC-011-4: [Edge] svn · remote · A — svn blame via remote URL

```gherkin
Scenario: [Edge] Remote SVN with AlgA
  GIVEN an SVN repository URL (svn:// or https://)
  AND --algorithm A
  WHEN aggregateGenCodeDesc runs svn blame
  THEN the tool runs svn blame against the remote URL
  AND the fork documents known SVN merge blame imprecision
```

### AC-011-5: [Edge] svn · remote · B — offline SVN patches, no VCS access

```gherkin
Scenario: [Edge] Remote SVN with AlgB offline patches
  GIVEN --commitPatchDir with pre-exported svn diff patches
  AND --algorithm B
  AND no SVN server access at runtime
  WHEN aggregateGenCodeDesc runs
  THEN patches are processed by ascending revision number
  AND metrics are computed correctly
```

### Updated AC Count

| US | Title | AC Count |
|----|-------|----------|
| US-001 ~ US-010 | Previous | 59 |
| US-011 | Deployment Topology (12 cells) | 5 |
| **Total** | | **64 AC** |

> Cells marked P0 must pass before release. Cells marked P1 are edge scenarios with known SVN limitations (remote SVN blame imprecision).

---

## How Forks Use This Document

1. Fork this repo for a specific CodeAgent & LLM combination.
2. Each AC above becomes a test case via `test-driven-development` skill.
3. **RED** — write a failing test from the GIVEN/WHEN/THEN scenario.
4. **GREEN** — implement minimal code to pass.
5. **REFACTOR** — clean up.
6. When all 64 ACs pass → your implementation is correct per the BASE specification.

> **Not every AC applies to every fork.** Git-only conditions (rebase, amend, shallow clone)
> can be skipped by SVN forks. AlgC-specific ACs can be skipped by AlgA-only forks.
> Document which ACs are skipped and why.

---

## Appendix: VCS and Algorithm Coverage Matrix

### Coverage Scope

The ACs are written **Git-first**. Git is the modern standard and the primary target.
SVN is legacy — supported to the extent that the protocol allows, but with known limitations.

### VCS Coverage Per AC

| AC | Git | SVN | Notes |
|----|-----|-----|-------|
| **US-001 (Core Metric)** | | | |
| AC-001-1 ~ AC-001-7 | ✅ | ✅ | VCS-agnostic — pure math on genRatio values and sparse DETAIL semantics |
| **US-002 (File-Level)** | | | |
| AC-002-1 ~ AC-002-2 (rename) | ✅ | ✅ | Git: heuristic `-M`. SVN: explicit `svn move` — more reliable |
| AC-002-3 (delete) | ✅ | ✅ | Same behavior |
| AC-002-4 (copy) | ✅ | ⚠️ | SVN `svn copy` semantics differ from Git — fork must adapt |
| **US-003 (Commit-Level)** | | | |
| AC-003-1 (merge) | ✅ | ⚠️ | SVN has no true merge commit — `svn:mergeinfo` based, blame may be imprecise |
| AC-003-2 (squash) | ✅ | ✅ | SVN squash is manual but same concept |
| AC-003-3 (cherry-pick) | ✅ | ⚠️ | SVN `svn merge -c` — mergeinfo may confuse blame |
| AC-003-4 (revert) | ✅ | ✅ | Same behavior |
| AC-003-5 (amend/force-push) | ✅ | ❌ N/A | SVN history is immutable — skip |
| AC-003-6 (rebase) | ✅ | ❌ N/A | Does not exist in SVN — skip |
| **US-004 (Line-Level)** | | | |
| AC-004-1 ~ AC-004-6 | ✅ | ✅ | VCS-agnostic — per-line ownership logic |
| AC-004-3 (whitespace) | ✅ | ⚠️ | `svn blame` has no `-w` equivalent — whitespace is always significant |
| **US-005 (Branch/History)** | | | |
| AC-005-1 ~ AC-005-2 | ✅ | ✅ | Standard blame behavior |
| AC-005-3 (long-lived branch) | ✅ | ⚠️ | SVN blame on long-diverged branches may be imprecise via mergeinfo |
| AC-005-4 (shallow clone) | ✅ | ❌ N/A | SVN has no shallow clone — always full history via server |
| AC-005-5 (submodule) | ✅ | ⚠️ | SVN uses `svn:externals` — different semantics, additional path-resolution complexity |
| **US-006 (Destructive/Edge)** | | | |
| AC-006-1 ~ AC-006-3 | ✅ | ✅ | VCS-agnostic — genCodeDesc validation |
| AC-006-4 (clock skew) | ✅ | ❌ N/A | SVN timestamps are server-assigned, monotonic — no skew risk |
| AC-006-5 (invalid genRatio) | ✅ | ✅ | VCS-agnostic — input validation |
| AC-006-6 (CLI arguments) | ✅ | ✅ | VCS-agnostic — CLI parsing |
| **US-007 (Git vs SVN)** | | | |
| AC-007-1 ~ AC-007-5 | ✅ | ✅ | Dedicated to documenting differences |
| **US-008 (Scale/Perf)** | | | |
| AC-008-1 ~ AC-008-4 | ✅ | ✅ | Same scale model applies to both |

**Legend:** ✅ = fully applicable, ⚠️ = applicable with known limitations, ❌ N/A = not applicable (skip)

### Algorithm Coverage Per AC

| AC | AlgA (live blame) | AlgB (diff replay) | AlgC (embedded blame) |
|----|-------------------|---------------------|----------------------|
| **US-001 ~ US-004** | ✅ | ✅ | ✅ |
| AC-005-4 (shallow clone) | ✅ boundary hit | ✅ diffs unavailable beyond depth | ❌ N/A (self-sufficient) |
| AC-006-1 (missing genCodeDesc) | ✅ genRatio=0 | ✅ genRatio=0 | ⚠️ chain break |
| AC-006-4 (clock skew) | ❌ N/A (order-independent) | ❌ N/A (topological order) | ✅ sorts by timestamp |
| AC-008-1 (AlgA perf) | ✅ | ❌ N/A | ❌ N/A |
| AC-008-2 (AlgC perf) | ❌ N/A | ❌ N/A | ✅ |
| **AC-009-1 (rename -M)** | ✅ | ❌ N/A | ❌ N/A |
| **AC-009-2 (cross-file -C -C)** | ✅ | ❌ N/A | ❌ N/A |
| **AC-009-3 (VCS unreachable)** | ✅ | ❌ N/A | ❌ N/A |
| **AC-009-4 (topological multi-file replay)** | ❌ N/A | ✅ | ❌ N/A |
| **AC-009-5 (chained renames)** | ❌ N/A | ✅ | ❌ N/A |
| **AC-009-6 (missing diff)** | ❌ N/A | ✅ | ❌ N/A |
| **AC-009-7 (surviving set)** | ❌ N/A | ❌ N/A | ✅ |
| **AC-009-8 (duplicate add)** | ❌ N/A | ❌ N/A | ✅ |
| **AC-009-9 (SUMMARY mismatch)** | ❌ N/A | ❌ N/A | ✅ |

> **For SVN forks:** Skip all ❌ N/A rows. Document ⚠️ rows as known limitations in your fork README.
>
> **For single-algorithm forks:** Implement only the ACs for your chosen algorithm.
> A fork that only implements AlgA can skip AlgC-specific ACs (AC-008-2, AC-006-4).
