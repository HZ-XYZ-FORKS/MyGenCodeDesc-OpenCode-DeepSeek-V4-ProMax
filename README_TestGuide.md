# Test Guide - `aggregateGenCodeDesc`

This guide defines the testing model every fork of MyGenCodeDescBase should follow.
Each fork may choose Python, C++, or Rust, but the test intent stays the same:

> UserStory + UserGuide -> AcceptanceCriteria -> TestCase -> Verified implementation.

This is the repo's CaTDD (Comment-alive Test-Driven Development) flow. In this guide, UnitTesting, SysTesting, and UserTesting are three verification layers over the same CaTDD chain, not three unrelated test styles.

The test suite is divided into three layers:

| Layer | Purpose | Main audience | Typical location |
| --- | --- | --- | --- |
| UnitTesting | Verify small deterministic logic in isolation. | Tool developer | `tests/unit/` |
| SysTesting | Verify complete CLI/tool behavior across realistic repositories and protocol files. | Tool developer / maintainer | `tests/system/` |
| UserTesting | Verify user-facing workflows from the guide and user stories. | Codebase maintainer / reviewer | `tests/user/` or `tests/demo/` |

All tests should run inside the Dev Container described by [README_ForkWorkflow.md](README_ForkWorkflow.md), so code agents can execute them in a safe and reproducible environment.

## 0. CaTDD Reference

CaTDD keeps intent, verification design, and executable checks connected:

| CaTDD artifact | Meaning | Primary test layer |
| --- | --- | --- |
| UserStory | Defines the user value and required behavior. | UserTesting, SysTesting |
| UserGuide | Defines the documented command flow and user-facing contract. | UserTesting, SysTesting |
| AcceptanceCriteria | Converts stories into verifiable Given/When/Then scenarios. | UnitTesting, SysTesting, UserTesting |
| TestCase | Turns each AC into one or more executable or manual checks. | UnitTesting, SysTesting, UserTesting |
| Verified implementation | Confirms the implementation satisfies the base contract. | All layers |

Each test should preserve a visible traceability chain:

```text
US -> AC -> TC -> implementation/test assertion -> result
```

Use the three layers this way:

| Layer | CaTDD role |
| --- | --- |
| UnitTesting | Proves a single rule, parser behavior, formula, or policy decision behind one AC. |
| SysTesting | Proves a complete AC or user-story path through the real CLI and real artifacts. |
| UserTesting | Proves a maintainer can follow the UserGuide and recognize the expected result. |

When a test is written or reviewed, it should be clear which US and AC it protects. If that link is missing, the test is not yet CaTDD-aligned.

### 0.1 CaTDD Priority Categories

CaTDD also classifies every test case by priority and category. The test layer says where the test runs; the CaTDD category says what kind of risk or behavior it protects.

| Priority | Category | What it protects | Common layer |
| --- | --- | --- | --- |
| P1 Functional | Typical | Mainline behavior that users expect to work. | UnitTesting, SysTesting, UserTesting |
| P1 Functional | Boundary | Edge values, limits, empty inputs, thresholds, and zero denominators. | UnitTesting, SysTesting |
| P1 Functional | Misuse | Invalid inputs, unsupported argument combinations, and user mistakes. | UnitTesting, SysTesting, UserTesting |
| P1 Functional | Fault | Corrupt files, missing revisions, duplicate records, and external command failures. | UnitTesting, SysTesting |
| P2 Design | State | Stateful transitions such as add/delete replay, rename tracking, and surviving-line state. | UnitTesting, SysTesting |
| P2 Design | Capability | Optional modes and supported feature combinations such as Algorithm A/B/C and Scope A/B/C/D. | SysTesting |
| P2 Design | Concurrency | Parallel blame, sharded replay, cache behavior, and race-sensitive processing. | UnitTesting, SysTesting |
| P3 Quality | Performance | Large windows, large files, streaming, and memory-bounded processing. | SysTesting |
| P3 Quality | Robust | Recovery behavior, degraded modes, deterministic diagnostics, and repeatability. | SysTesting, UserTesting |
| P3 Quality | Compatibility | Git vs SVN, host OS differences through Dev Container, and protocol version compatibility. | SysTesting, UserTesting |
| P3 Quality | Configuration | CLI options and policy settings such as `onMissing`, `onDuplicate`, and `onClockSkew`. | UnitTesting, SysTesting |
| P4 Addons | Demo/Example | Documentation examples, maintainer demos, and guided acceptance walkthroughs. | UserTesting |

Every CaTDD test case should declare both fields:

```text
@[Priority]: P1 Functional
@[Category]: Typical
```

This category is independent from UnitTesting/SysTesting/UserTesting. For example, a `Boundary` case may be a UnitTesting case for the metric formula and also a SysTesting case for the CLI output.

---

## 1. UnitTesting

UnitTesting verifies the smallest meaningful pieces of the implementation without relying on live Git/SVN repositories, network access, external services, or large fixture directories.

### 1.1 CaTDD Role

In CaTDD, UnitTesting is the lowest-cost proof that a specific rule in an AC works correctly. A unit test should usually map to one formula, parser rule, validation rule, policy branch, or helper behavior.

Good UnitTesting answers:

- Which US and AC does this small behavior support?
- What exact rule is being verified?
- What input, behavior, and expected output make the rule observable?
- Is the test independent enough to fail close to the root cause?

Recommended CaTDD test-case shape:

```text
[@AC-001-1,US-001]
TC-Unit-001:
  @[Name]: verifyWeightedRatio_byMixedGenRatio_expectSeventySevenPercent
  @[Priority]: P1 Functional
  @[Category]: Typical
  @[Purpose]: Protect the weighted metric formula.
  @[Brief]: Given 10 live lines with mixed genRatio values, compute weighted ratio.
  @[Expect]: Result is 77.0%.
```

### 1.2 What UnitTesting Must Cover

At minimum, every fork should unit test:

| Area | Required coverage |
| --- | --- |
| Metric formulas | Weighted, Fully AI, and Mostly AI calculations, including zero denominator. |
| Threshold handling | Boundary values `0`, `1`, `60`, `99`, `100`, invalid values outside `0..100`. |
| Protocol parsing | v26.03 and v26.04 valid records, missing fields, wrong types, malformed JSON. |
| Protocol validation | Mixed protocol versions, duplicate `revisionId`, mismatched `repoURL`, `repoBranch`, or `revisionId`. |
| Sparse detail handling | Omitted v26.03 DETAIL lines are treated as effective `genRatio=0`. |
| Line classification | Code vs doc line routing according to the selected scope. |
| Aggregation helpers | Full, partial, manual/unattributed, and mostly-AI line counts. |
| Policy options | `onMissing`, `onDuplicate`, and `onClockSkew` behavior. |

### 1.3 UnitTesting Rules

- Tests must be deterministic and fast.
- Tests must not require a real Git/SVN repository unless the unit under test is explicitly a VCS command adapter.
- Prefer tiny inline fixtures for formula and validation logic.
- Use golden JSON fixtures only when the shape is too large to read clearly inline.
- Test failure messages should name the user story or acceptance criterion being protected.

### 1.4 Recommended Unit Test Naming

Use names that preserve traceability:

```text
test_US001_AC001_1_weighted_mixed_authorship
test_US001_AC001_6_zero_denominator
test_US006_duplicate_revision_rejected
test_protocol_v2604_rejects_missing_embedded_blame
```

The exact naming style may follow the fork's language and test framework, but every test should make the covered behavior obvious.

---

## 2. SysTesting

SysTesting verifies the tool as a complete system. These tests execute the real `aggregateGenCodeDesc` entry point with realistic inputs and validate the generated output artifacts.

### 2.1 CaTDD Role

In CaTDD, SysTesting proves that one or more ACs survive contact with the real tool boundary: CLI arguments, repository fixtures, genCodeDesc files, generated JSON, generated patch output, logs, and exit codes.

Good SysTesting answers:

- Which AC is verified through the real executable path?
- Which algorithm, protocol version, VCS mode, and scope are involved?
- Which artifacts are produced and compared?
- Does the failure point tell a developer whether the problem is parsing, algorithm behavior, output shaping, or diagnostics?

Recommended CaTDD test-case shape:

```text
[@AC-001-1,US-001]
TC-Sys-001:
  @[Name]: verifyAggregateCli_byAlgAWithV2603Fixture_expectWeightedSeventySevenPercent
  @[Priority]: P1 Functional
  @[Category]: Typical
  @[Purpose]: Prove the documented metric is produced by the real CLI.
  @[Brief]: Run aggregateGenCodeDesc on a tiny Git fixture with v26.03 metadata.
  @[Expect]: JSON contains weighted=0.77 and patch artifact is created.
```

### 2.2 What SysTesting Must Cover

At minimum, every fork should system test:

| Area | Required coverage |
| --- | --- |
| CLI argument contract | Required arguments, optional arguments, invalid argument combinations, exit codes. |
| Algorithm A | Live blame against a local Git repository for v26.03 input. |
| Algorithm B | Offline diff replay using `commitPatchDir` for v26.03 input. |
| Algorithm C | Embedded blame replay using v26.04 input without live VCS access. |
| Output artifacts | `genCodeDescV26.03.json` and `commitStart2EndTime.patch` are both produced. |
| Output schema | Aggregate JSON follows the v26.03 envelope plus `AGGREGATE` extensions. |
| Diagnostics | Missing revisions, duplicates, mixed versions, clock skew, and warnings are emitted correctly. |
| Repository behavior | Rename, delete, copy, merge, squash, cherry-pick, revert, rebase/force-push conditions where applicable. |
| Scope behavior | Scope A/B/C/D filters change denominator and output consistently. |

### 2.3 Window Diff and Alive Code Aggregation Contract

System tests must verify that `aggregateGenCodeDesc` aggregates the alive subset of the window diff:

```text
aggregate set = (lines added/modified by startTime..endTime diff) ∩ (lines alive at endTime)
```

The patch artifact and JSON metrics use the same window and scope, but they answer different audit questions:

| Concept | Meaning | Required verification |
| --- | --- | --- |
| `commitStart2EndTime.patch` | The cumulative diff for commits/revisions from `fromCommit >= startTime` through `toCommit <= endTime`, as defined in [README_UserGuide.md](README_UserGuide.md). | Shows which lines changed in the selected window and remains auditable as a patch artifact. |
| Alive subset of the diff | Lines from that diff whose current versions are still alive at `endTime`. | Defines the JSON metric denominator and excludes deleted, reverted, and pre-window-origin lines. |

Required CaTDD-aligned cases:

| TC | Source trace | Expected distinction |
| --- | --- | --- |
| `TC-Sys-WindowDiffDeletedFile` | `[@AC-002-3,US-002]` | Deleted lines may appear as removals in the window diff, but contribute zero to alive-code metrics. |
| `TC-Sys-WindowDiffRevertedLines` | `[@AC-003-4,US-003]` | Reverted lines are visible in the window history, but are absent from the alive snapshot at `endTime`. |
| `TC-Sys-PreWindowAliveLineExcluded` | `[@AC-005-1,US-005]` | A line committed before `startTime` may still be alive at `endTime`, but is excluded from the in-window denominator. |
| `TC-Sys-DiffPatchAndJsonAgreeOnScope` | `[@AC-001-8,US-001]` | `commitStart2EndTime.patch` and `genCodeDescV26.03.json` use the same window and scope filter, while the JSON denominator aggregates only the alive subset of the diff. |

If a test only checks that the patch file exists, it is not enough. It must also prove the JSON metrics are computed from `(startTime..endTime diff) ∩ (alive at endTime)`, not from raw added/deleted diff lines and not from all alive lines in the repository.

### 2.4 System Fixture Strategy

Each fork should keep fixtures small but behavior-rich:

| Fixture type | Recommended content |
| --- | --- |
| Tiny Git repos | Created during test setup with scripted commits and known timestamps. |
| genCodeDesc fixtures | One directory per scenario, with one JSON file per revision. |
| Patch fixtures | One patch file per revision for Algorithm B. |
| Expected outputs | Golden aggregate JSON and patch files for stable scenarios. |

System tests may generate temporary repositories at runtime. If fixture repos are checked in, keep them minimal and document how they were produced.

### 2.5 System Test Exit Criteria

A fork should not claim implementation completeness until system tests prove:

1. The same user story produces matching metrics across all compatible algorithms.
2. Unsupported protocol/algorithm combinations fail with the documented exit code.
3. `stdout` and output files are machine-readable and runtime logs go to `stderr`.
4. Re-running the same test produces byte-stable output where deterministic output is expected.

---

## 3. UserTesting

UserTesting verifies that a codebase maintainer can follow the documented workflow and get the expected result. These tests are acceptance-oriented and may be manual, scripted, or demo-style.

### 3.1 CaTDD Role

In CaTDD, UserTesting proves that the UserStory and UserGuide are true from a maintainer's perspective. It is allowed to be less granular than UnitTesting and less implementation-focused than SysTesting, but it must demonstrate the user value end to end.

Good UserTesting answers:

- Can a maintainer follow the documented workflow without knowing implementation internals?
- Which US and AC are demonstrated?
- What command or manual steps should be run?
- What result should the maintainer see, and how should they interpret it?

Recommended CaTDD test-case shape:

```text
[@AC-001-1,US-001]
TC-User-001:
  @[Name]: verifyGuideFlow_byDemoRepository_expectReadableAggregateMetrics
  @[Priority]: P4 Addons
  @[Category]: Demo/Example
  @[Purpose]: Demonstrate the guide workflow for a maintainer.
  @[Brief]: Follow README_UserGuide against a prepared demo repository.
  @[Expect]: User can identify Weighted, Fully AI, and Mostly AI results.
```

### 3.2 What UserTesting Must Cover

At minimum, every fork should user test:

| Area | Required coverage |
| --- | --- |
| README_UserGuide flow | A maintainer can run the documented command from the guide. |
| README_UserStories scenarios | Key acceptance criteria are demonstrably satisfied. |
| Safe agent workflow | The test can run inside the Dev Container without host-specific setup. |
| Result interpretation | The user can identify Weighted, Fully AI, and Mostly AI values in the output. |
| Error interpretation | The user can understand common validation failures from stderr/log output. |
| Cross-platform host setup | macOS, Linux, and Windows hosts use the same containerized test workflow. |

### 3.3 UserTesting Forms

A fork may use one or more of these forms:

| Form | When to use |
| --- | --- |
| Manual test script | Best for early forks where implementation is still changing. |
| Demo test case | Best for showing a full user story from setup to expected output. |
| Acceptance test | Best once the CLI and output contract are stable. |
| Release checklist | Best before tagging or comparing multiple agent/LLM forks. |

### 3.4 Required User Test README

Every user-facing demo or manual test should include a short README with:

| Section | Content |
| --- | --- |
| Purpose | Which user story or guide workflow this test demonstrates. |
| Status | Draft, implemented, passing, failing, or blocked. |
| Covered | Specific AC IDs, CaTDD priorities/categories, algorithm modes, protocols, and scopes covered. |
| Manual | Exact commands to run and expected output summary. |

This keeps user tests readable for maintainers and makes code-agent work easier to review.

---

## 4. Test Traceability Matrix

Each fork should maintain traceability from requirements to tests.

| Source | Test layer |
| --- | --- |
| `README_UserStories.md` | CaTDD US/AC source; UnitTesting for atomic rules, SysTesting/UserTesting for complete scenarios. |
| `README_UserGuide.md` | CaTDD user workflow source; SysTesting for CLI contract, UserTesting for documented workflows. |
| `README_Protocol.md` | UnitTesting for schema/validation, SysTesting for real protocol files. |
| `README_AlgABC.md` | UnitTesting for algorithm helpers, SysTesting for full algorithm behavior. |
| `Protocols/*.json` | UnitTesting for schema compatibility and fixture validation. |

A good test case should be able to answer: which user story, which acceptance criterion, which CaTDD priority/category, which protocol version, which algorithm, and which scope does this protect?

---

## 5. Minimum Test Set for a Fork

A fork should start with this minimum set before adding wider coverage:

1. UnitTesting for all three metric formulas, each linked to US/AC IDs.
2. UnitTesting for protocol parsing and validation errors, each linked to US/AC IDs.
3. SysTesting for one happy path per supported algorithm, each linked to US/AC IDs.
4. SysTesting for unsupported protocol/algorithm combinations, each linked to US/AC IDs.
5. UserTesting for one documented end-to-end guide flow, linked to the guide and US/AC IDs.
6. UserTesting that runs inside the Dev Container and proves the safe-agent workflow.

This minimum set gives fast feedback during development and enough confidence that the fork satisfies the base contract.

---

## 6. Running Tests

Because each fork chooses its implementation language, exact commands are fork-specific. Recommended conventions:

| Language | UnitTesting | SysTesting/UserTesting |
| --- | --- | --- |
| Python | `pytest tests/unit` | `pytest tests/system tests/user` |
| C++ | `ctest -R unit` | `ctest -R "system\|user"` |
| Rust | `cargo test unit` | `cargo test system user` |

All commands should run from inside the Dev Container unless a test explicitly documents why it must run elsewhere.

---

## 7. Completion Definition

Testing is considered complete for a fork when:

- UnitTesting covers deterministic logic and validation behavior.
- SysTesting covers the real CLI, output artifacts, and algorithm/protocol compatibility.
- UserTesting proves a maintainer can follow the guide and interpret the result.
- UnitTesting, SysTesting, and UserTesting all preserve CaTDD traceability from US -> AC -> TC -> result.
- Every TC declares a CaTDD priority and category.
- Every failing or skipped test has an explicit reason.
- The test suite can run in the safe container workflow without relying on hidden host state.
