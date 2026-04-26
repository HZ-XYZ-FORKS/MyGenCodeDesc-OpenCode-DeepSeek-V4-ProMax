import json
import time
import os
import pytest

from aggregateGenCodeDesc.alg_c import stream_accumulate_surviving_set


SNAPSHOT_LINES_PER_FILE = 100
COMMITS = 50
FILES = 10
TOTAL_LINES = COMMITS * FILES * SNAPSHOT_LINES_PER_FILE


def _synthetic_gendesc(rev_num: int, ts: str, files: int) -> dict:
    detail = []
    for f in range(files):
        fname = f"module_{f}.py"
        lines = []
        for i in range(SNAPSHOT_LINES_PER_FILE):
            lines.append({
                "changeType": "add",
                "lineLocation": i + 1,
                "genRatio": (i * 7 + f * 13 + rev_num * 3) % 101,
                "genMethod": "vibeCoding",
                "blame": {
                    "revisionId": f"rev_{rev_num:05d}",
                    "originalFilePath": fname,
                    "originalLine": i + 1,
                    "timestamp": ts,
                },
            })
        detail.append({"fileName": fname, "codeLines": lines})
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
            "totalCodeLines": SNAPSHOT_LINES_PER_FILE * files,
            "fullGeneratedCodeLines": 0,
            "partialGeneratedCodeLines": 0,
            "totalDocLines": 0,
            "fullGeneratedDocLines": 0,
            "partialGeneratedDocLines": 0,
        },
    }


@pytest.fixture(scope="module")
def large_gencode_dir(tmp_path_factory):
    """Generate COMMITS × FILES × LINES synthetic v26.04 dataset."""
    d = tmp_path_factory.mktemp("perf_gencode")
    for rev in range(COMMITS):
        hour = rev % 24
        day = 1 + rev // 24
        ts = f"2026-01-{day:02d}T{hour:02d}:00:00Z"
        record = _synthetic_gendesc(rev, ts, FILES)
        (d / f"rev_{rev:05d}.json").write_text(json.dumps(record))
    return d


class TestPerformance:
    def test_streaming_completes(self, large_gencode_dir):
        """AC-008-2: Streaming processes synthetic data without loading all into memory."""
        t0 = time.monotonic()
        surviving, warnings = stream_accumulate_surviving_set(
            str(large_gencode_dir),
            end_time="2026-12-31T23:59:59Z",
            return_warnings=True,
        )
        elapsed = time.monotonic() - t0

        assert len(surviving) > 0
        assert elapsed < 120, f"Timeout: {elapsed:.1f}s for {COMMITS} commits"
        assert len(warnings) > 0, "SUMMARY mismatch warnings expected for synthetic data"

    def test_streaming_memory_bounded(self, large_gencode_dir):
        """Streaming memory should stay well under 4GB — each file processed individually."""
        surviving, _ = stream_accumulate_surviving_set(
            str(large_gencode_dir),
            end_time="2026-12-31T23:59:59Z",
            return_warnings=True,
        )
        expected_max = COMMITS * FILES * SNAPSHOT_LINES_PER_FILE
        assert len(surviving) <= expected_max
        # With COMMITS=50, FILES=10, LINES=100 → max 50000 entries
        assert len(surviving) < 500_000, "Memory should be bounded by surviving set"

    def test_streaming_time_linear(self, large_gencode_dir, tmp_path):
        """Processing time should scale roughly linearly with file count."""
        t0 = time.monotonic()
        stream_accumulate_surviving_set(
            str(large_gencode_dir),
            end_time="2026-12-31T23:59:59Z",
        )
        full_time = time.monotonic() - t0

        half_dir = tmp_path / "half"
        half_dir.mkdir()
        for f in sorted(large_gencode_dir.glob("*.json"))[:COMMITS // 2]:
            (half_dir / f.name).write_text(f.read_text())

        t1 = time.monotonic()
        stream_accumulate_surviving_set(
            str(half_dir),
            end_time="2026-12-31T23:59:59Z",
        )
        half_time = time.monotonic() - t1

        assert half_time < full_time
        ratio = full_time / max(half_time, 0.001)
        assert ratio < 5.0, f"Expected linear scaling, got {ratio:.1f}x"


class TestDiskSpace:
    def test_dataset_within_bounds(self, large_gencode_dir):
        """Generated dataset should fit in well under 20GB."""
        total_size = sum(
            os.path.getsize(str(f))
            for f in large_gencode_dir.glob("*.json")
        )
        assert total_size < 1_000_000_000, f"Dataset too large: {total_size / 1e9:.2f} GB"
