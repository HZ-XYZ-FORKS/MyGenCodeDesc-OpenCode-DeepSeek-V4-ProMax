import json
import time
import os
import random
import pytest

from aggregateGenCodeDesc.alg_c import stream_accumulate_surviving_set

random.seed(42)

COMMITS = 200
FILES = 10
LINES_PER_FILE = 10000
MIN_BLOCKS_PER_COMMIT = 5
MAX_BLOCKS_PER_COMMIT = 50
LINES_PER_BLOCK = 20
TOTAL_ENTRIES = COMMITS * ((MIN_BLOCKS_PER_COMMIT + MAX_BLOCKS_PER_COMMIT) // 2) * LINES_PER_BLOCK


class LineTracker:
    """Track which line ranges have been added, so we can simulate real modify/delete/add patterns."""
    def __init__(self):
        self.ranges = {}  # file_name -> {line_num -> revision_id}

    def add_block(self, fname, start, count, rev_id):
        for i in range(count):
            ln = start + i
            if fname not in self.ranges:
                self.ranges[fname] = {}
            self.ranges[fname][ln] = rev_id

    def get_owner(self, fname, ln):
        return self.ranges.get(fname, {}).get(ln)


def _synthetic_gendesc(rev_num, ts, tracker):
    detail = []
    num_blocks = random.randint(MIN_BLOCKS_PER_COMMIT, MAX_BLOCKS_PER_COMMIT)

    entries_by_file = {}
    for _ in range(num_blocks):
        f_idx = random.randint(0, FILES - 1)
        fname = f"module_{f_idx}.py"

        # 80% chance: add at a NEW unused position (growing file)
        # 20% chance: overwrite a previously-added block
        if random.random() < 0.8 or rev_num == 0:
            # Find an unused range — scan forward from a random position
            for attempt in range(20):
                start_line = random.randint(1, LINES_PER_FILE - LINES_PER_BLOCK)
                any_used = any(
                    tracker.get_owner(fname, start_line + i) is not None
                    for i in range(LINES_PER_BLOCK)
                )
                if not any_used:
                    break
        else:
            start_line = random.randint(1, LINES_PER_FILE - LINES_PER_BLOCK)

        if fname not in entries_by_file:
            entries_by_file[fname] = []

        for i in range(LINES_PER_BLOCK):
            ln = start_line + i
            prev_owner = tracker.get_owner(fname, ln)
            if prev_owner is not None:
                entries_by_file[fname].append({
                    "changeType": "delete",
                    "blame": {
                        "revisionId": prev_owner,
                        "originalFilePath": fname,
                        "originalLine": ln,
                    },
                })

        entries_by_file[fname].append({
            "changeType": "add",
            "lineRange": {"from": start_line, "to": start_line + LINES_PER_BLOCK - 1},
            "genRatio": (rev_num * 7 + f_idx * 13) % 101,
            "genMethod": "vibeCoding",
            "blame": {
                "revisionId": f"rev_{rev_num:05d}",
                "originalFilePath": fname,
                "originalLine": start_line,
                "timestamp": ts,
            },
        })
        tracker.add_block(fname, start_line, LINES_PER_BLOCK, f"rev_{rev_num:05d}")

    # Merge per-file entries into DETAIL
    detail = []
    for fname, entries in entries_by_file.items():
        detail.append({"fileName": fname, "codeLines": entries})

    add_count = sum(
        LINES_PER_BLOCK
        for lst in entries_by_file.values()
        for e in lst
        if e["changeType"] == "add"
    )
    return {
        "protocolVersion": "26.04",
        "REPOSITORY": {
            "revisionId": f"rev_{rev_num:05d}",
            "revisionTimestamp": ts,
            "vcsType": "git",
            "repoURL": "https://example.com/perf",
            "repoBranch": "main",
        },
        "DETAIL": detail,
        "SUMMARY": {
            "totalCodeLines": add_count,
            "fullGeneratedCodeLines": 0,
            "partialGeneratedCodeLines": 0,
            "totalDocLines": 0,
            "fullGeneratedDocLines": 0,
            "partialGeneratedDocLines": 0,
        },
    }


@pytest.fixture(scope="module")
def scale_gencode_dir(tmp_path_factory):
    """Generate 200 commits, each with 5-50 sparse modification blocks (20 lines each).
    Commits overwrite previous lines + add new ones, simulating real incremental edits.
    Expected: ~180K surviving lines with realistic collision/ownership patterns.
    """
    d = tmp_path_factory.mktemp("scale_gencode")
    tracker = LineTracker()
    for rev in range(COMMITS):
        hour = rev % 24
        day = 1 + rev // 24
        ts = f"2026-01-{day:02d}T{hour:02d}:00:00Z"
        record = _synthetic_gendesc(rev, ts, tracker)
        (d / f"rev_{rev:05d}.json").write_text(json.dumps(record))
    return d


class TestScale200K:
    def test_throughput(self, scale_gencode_dir):
        """AC-008-2: Throughput at realistic scale with sparse modification blocks."""
        t0 = time.monotonic()
        surviving, warnings = stream_accumulate_surviving_set(
            str(scale_gencode_dir),
            end_time="2026-12-31T23:59:59Z",
            return_warnings=True,
        )
        elapsed = time.monotonic() - t0

        assert len(surviving) > 50_000, f"Too few surviving lines: {len(surviving):,}"
        assert elapsed < 30, f"Timeout: {elapsed:.1f}s"
        throughput = len(surviving) / max(elapsed, 0.001)
        print(f"\n    200K scale: {len(surviving):,} surviving | {elapsed:.2f}s | {throughput:,.0f} ops/s")

    def test_memory_bounded(self, scale_gencode_dir):
        """Surviving set stays well under budget."""
        surviving, _ = stream_accumulate_surviving_set(
            str(scale_gencode_dir),
            end_time="2026-12-31T23:59:59Z",
            return_warnings=True,
        )
        assert len(surviving) < 500_000, f"Surviving set too large: {len(surviving):,}"

    def test_disk_size(self, scale_gencode_dir):
        total = sum(os.path.getsize(str(f)) for f in scale_gencode_dir.glob("*.json"))
        assert total < 2_000_000_000, f"Disk: {total / 1e6:.1f} MB"

    def test_realistic_collision_pattern(self, scale_gencode_dir):
        """Delete-then-add eliminates collisions; 20% overwrites work cleanly."""
        _, warnings = stream_accumulate_surviving_set(
            str(scale_gencode_dir),
            end_time="2026-12-31T23:59:59Z",
            return_warnings=True,
        )
        collisions = [w for w in warnings if "collision" in w.lower()]
        assert len(collisions) == 0, "Delete-then-add should produce zero collisions"

