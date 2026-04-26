import pytest

from aggregateGenCodeDesc.models import (
    DetailFileV2603,
    GenCodeDescV2603,
    LineLocation,
    LineRange,
    Repository,
    Summary,
)
from aggregateGenCodeDesc.alg_a import (
    BlameLine,
    compute_alg_a_metrics,
    mark_window_lines,
    resolve_gen_ratios_from_v2603,
    build_line_to_genratio_map,
)


class TestBuildLineToGenratioMap:
    def test_build_map_from_v2603_records(self):
        records = [
            GenCodeDescV2603(
                SUMMARY=Summary(10, 5, 3, 0, 0, 0),
                DETAIL=[
                    DetailFileV2603(
                        fileName="app.py",
                        codeLines=[
                            LineLocation(lineLocation=1, genRatio=100, genMethod="codeCompletion"),
                            LineLocation(lineLocation=2, genRatio=80, genMethod="vibeCoding"),
                            LineRange(from_=5, to_=7, genRatio=50, genMethod="vibeCoding"),
                        ],
                    ),
                ],
                REPOSITORY=Repository("git", "https://example.com/repo", "main", "abc123"),
            ),
        ]
        m = build_line_to_genratio_map(records)
        assert m[("abc123", "app.py", 1)] == 100
        assert m[("abc123", "app.py", 2)] == 80
        assert m[("abc123", "app.py", 5)] == 50
        assert m[("abc123", "app.py", 6)] == 50
        assert m[("abc123", "app.py", 7)] == 50
        assert ("abc123", "app.py", 3) not in m

    def test_build_map_multiple_files(self):
        records = [
            GenCodeDescV2603(
                SUMMARY=Summary(5, 0, 0, 0, 0, 0),
                DETAIL=[
                    DetailFileV2603(
                        fileName="a.py",
                        codeLines=[LineLocation(lineLocation=1, genRatio=100, genMethod="codeCompletion")],
                    ),
                ],
                REPOSITORY=Repository("git", "https://example.com/repo", "main", "r1"),
            ),
            GenCodeDescV2603(
                SUMMARY=Summary(3, 0, 0, 0, 0, 0),
                DETAIL=[
                    DetailFileV2603(
                        fileName="b.py",
                        codeLines=[LineLocation(lineLocation=3, genRatio=80, genMethod="vibeCoding")],
                    ),
                ],
                REPOSITORY=Repository("git", "https://example.com/repo", "main", "r2"),
            ),
        ]
        m = build_line_to_genratio_map(records)
        assert m[("r1", "a.py", 1)] == 100
        assert m[("r2", "b.py", 3)] == 80


class TestMarkWindowLines:
    def test_filter_by_blame_timestamp(self):
        lines = [
            BlameLine(blame="abc123 a.py 1", origin_revision="abc123", file_path="a.py", line_number=1, origin_timestamp="2026-02-15T00:00:00Z"),
            BlameLine(blame="def456 a.py 2", origin_revision="def456", file_path="a.py", line_number=2, origin_timestamp="2026-03-15T00:00:00Z"),
            BlameLine(blame="ghi789 a.py 3", origin_revision="ghi789", file_path="a.py", line_number=3, origin_timestamp="2026-01-01T00:00:00Z"),
        ]
        in_window, out_window = mark_window_lines(
            lines, start_time="2026-02-01T00:00:00Z", end_time="2026-04-01T00:00:00Z"
        )
        assert len(in_window) == 2
        assert len(out_window) == 1
        in_revs = {l.origin_revision for l in in_window}
        assert "abc123" in in_revs
        assert "def456" in in_revs

    def test_empty_lines(self):
        in_window, out_window = mark_window_lines([], "2026-01-01T00:00:00Z", "2026-06-01T00:00:00Z")
        assert in_window == []
        assert out_window == []


class TestResolveGenRatios:
    def test_resolve_with_existing_map_entries(self):
        genratio_map = {
            ("abc123", "a.py", 1): 100,
            ("abc123", "a.py", 2): 80,
            ("def456", "a.py", 3): 50,
        }
        lines = [
            BlameLine("blame1", "abc123", "a.py", 1, "2026-01-01T00:00:00Z"),
            BlameLine("blame2", "abc123", "a.py", 2, "2026-01-01T00:00:00Z"),
            BlameLine("blame3", "def456", "a.py", 3, "2026-01-01T00:00:00Z"),
            BlameLine("blame4", "xyz999", "a.py", 4, "2026-01-01T00:00:00Z"),
        ]
        resolved = resolve_gen_ratios_from_v2603(lines, genratio_map)
        assert resolved[0] == 100
        assert resolved[1] == 80
        assert resolved[2] == 50
        assert resolved[3] == 0


class TestComputeAlgAMetrics:
    def test_compute_from_blame_lines(self):
        genratio_map = {
            ("abc123", "a.py", 1): 100,
            ("abc123", "a.py", 2): 80,
            ("def456", "a.py", 3): 50,
        }
        lines = [
            BlameLine("blame1", "abc123", "a.py", 1, "2026-03-01T00:00:00Z"),
            BlameLine("blame2", "abc123", "a.py", 2, "2026-03-01T00:00:00Z"),
            BlameLine("blame3", "def456", "a.py", 3, "2026-03-01T00:00:00Z"),
            BlameLine("blame4", "xyz999", "a.py", 4, "2026-03-01T00:00:00Z"),
            BlameLine("blame5", "old123", "a.py", 5, "2025-12-01T00:00:00Z"),
        ]
        result = compute_alg_a_metrics(
            blame_lines=lines,
            genratio_map=genratio_map,
            start_time="2026-02-01T00:00:00Z",
            end_time="2026-04-01T00:00:00Z",
            threshold=60,
        )
        assert len(result.in_window_lines) == 4
        metrics = result.metrics
        assert metrics.weighted.value == pytest.approx(0.575, abs=0.001)
        assert metrics.fully_ai.value == pytest.approx(0.25, abs=0.001)


class TestBlameLine:
    def test_blame_line_parsing(self):
        line = BlameLine(
            blame="abc123 a.py 1",
            origin_revision="abc123",
            file_path="a.py",
            line_number=1,
            origin_timestamp="2026-01-01T00:00:00Z",
        )
        assert line.origin_revision == "abc123"
        assert line.file_path == "a.py"
        assert line.line_number == 1
        assert line.gen_ratio == 0
