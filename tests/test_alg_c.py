from datetime import datetime

from aggregateGenCodeDesc.models import (
    Blame,
    DetailAddEntry,
    DetailDeleteEntry,
    DetailFileV2604,
    GenCodeDescV2604,
    LineRange,
    RepositoryV2604,
    Summary,
    ValidationError,
)
from aggregateGenCodeDesc.alg_c import (
    accumulate_surviving_set,
    SurvivingLine,
    compute_alg_c_metrics,
)


def _make_add_entry(
    line_location: int,
    revision_id: str,
    file_path: str,
    original_line: int,
    timestamp: str,
    gen_ratio: int = 100,
    gen_method: str = "vibeCoding",
) -> DetailAddEntry:
    return DetailAddEntry(
        changeType="add",
        lineLocation=line_location,
        genRatio=gen_ratio,
        genMethod=gen_method,
        blame=Blame(
            revisionId=revision_id,
            originalFilePath=file_path,
            originalLine=original_line,
            timestamp=timestamp,
        ),
    )


def _make_add_line_range(
    from_: int,
    to_: int,
    revision_id: str,
    file_path: str,
    original_line_start: int,
    timestamp: str,
    gen_ratio: int = 100,
    gen_method: str = "vibeCoding",
) -> DetailAddEntry:
    return DetailAddEntry(
        changeType="add",
        lineRange=LineRange(from_=from_, to_=to_, genRatio=gen_ratio, genMethod=gen_method),
        genRatio=gen_ratio,
        genMethod=gen_method,
        blame=Blame(
            revisionId=revision_id,
            originalFilePath=file_path,
            originalLine=original_line_start,
            timestamp=timestamp,
        ),
    )


def _make_delete_entry(
    revision_id: str,
    file_path: str,
    original_line: int,
) -> DetailDeleteEntry:
    return DetailDeleteEntry(
        changeType="delete",
        blame=Blame(
            revisionId=revision_id,
            originalFilePath=file_path,
            originalLine=original_line,
        ),
    )


def _make_delete_range_entry(
    revision_id: str,
    file_path: str,
    from_: int,
    to_: int,
) -> DetailDeleteEntry:
    return DetailDeleteEntry(
        changeType="delete",
        blame=Blame(
            revisionId=revision_id,
            originalFilePath=file_path,
            originalLineRange=LineRange(from_=from_, to_=to_, genRatio=0, genMethod="Manual"),
        ),
    )


def _make_v2604_record(
    revision_id: str,
    timestamp: str,
    detail_files: list,
    summary_override: dict | None = None,
) -> GenCodeDescV2604:
    total_code = sum(
        sum(1 for e in df.codeLines if isinstance(e, DetailAddEntry))
        for df in detail_files
    )
    full_gen = 0
    partial_gen = 0
    for df in detail_files:
        for e in df.codeLines:
            if isinstance(e, DetailAddEntry):
                if e.genRatio == 100:
                    full_gen += 1
                elif e.genRatio > 0:
                    partial_gen += 1
    if summary_override:
        s = Summary(**summary_override)
    else:
        s = Summary(
            totalCodeLines=total_code,
            fullGeneratedCodeLines=full_gen,
            partialGeneratedCodeLines=partial_gen,
            totalDocLines=0,
            fullGeneratedDocLines=0,
            partialGeneratedDocLines=0,
        )
    return GenCodeDescV2604(
        SUMMARY=s,
        DETAIL=detail_files,
        REPOSITORY=RepositoryV2604(
            vcsType="git",
            repoURL="https://example.com/repo",
            repoBranch="main",
            revisionId=revision_id,
            revisionTimestamp=timestamp,
        ),
    )


class TestAccumulateSurvivingSet:
    def test_basic_add_only(self):
        record = _make_v2604_record(
            "abc123", "2026-01-01T00:00:00Z",
            [
                DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(1, "abc123", "app.py", 1, "2026-01-01T00:00:00Z"),
                        _make_add_entry(2, "abc123", "app.py", 2, "2026-01-01T00:00:00Z"),
                        _make_add_entry(3, "abc123", "app.py", 3, "2026-01-01T00:00:00Z"),
                    ],
                )
            ],
        )
        surviving = accumulate_surviving_set([record], end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 3

    def test_add_then_delete(self):
        records = [
            _make_v2604_record(
                "c1", "2026-01-01T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(1, "c1", "app.py", 1, "2026-01-01T00:00:00Z"),
                        _make_add_entry(2, "c1", "app.py", 2, "2026-01-01T00:00:00Z"),
                        _make_add_entry(3, "c1", "app.py", 3, "2026-01-01T00:00:00Z"),
                    ],
                )],
            ),
            _make_v2604_record(
                "c2", "2026-01-02T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_delete_entry("c1", "app.py", 2),
                    ],
                )],
            ),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 2
        lines_remaining = {(s.blame_revision_id, s.original_file_path, s.original_line) for s in surviving}
        assert ("c1", "app.py", 1) in lines_remaining
        assert ("c1", "app.py", 3) in lines_remaining

    def test_add_delete_add(self):
        records = [
            _make_v2604_record(
                "c1", "2026-01-01T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(1, "c1", "app.py", 1, "2026-01-01T00:00:00Z"),
                        _make_add_entry(2, "c1", "app.py", 2, "2026-01-01T00:00:00Z"),
                        _make_add_entry(3, "c1", "app.py", 3, "2026-01-01T00:00:00Z"),
                    ],
                )],
            ),
            _make_v2604_record(
                "c2", "2026-01-02T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_delete_entry("c1", "app.py", 2),
                        _make_add_entry(2, "c2", "app.py", 2, "2026-01-02T00:00:00Z", gen_ratio=50),
                    ],
                )],
            ),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 3
        replaced_line = [s for s in surviving if s.original_line == 2 and s.original_file_path == "app.py"]
        assert len(replaced_line) == 1
        assert replaced_line[0].blame_revision_id == "c2"
        assert replaced_line[0].gen_ratio == 50

    def test_delete_before_add_in_same_record(self):
        record = _make_v2604_record(
            "c1", "2026-01-01T00:00:00Z",
            [DetailFileV2604(
                fileName="app.py",
                codeLines=[
                    _make_delete_entry("c0", "app.py", 5),
                    _make_add_entry(5, "c1", "app.py", 5, "2026-01-01T00:00:00Z", gen_ratio=80),
                ],
            )],
        )
        surviving = accumulate_surviving_set([record], end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].gen_ratio == 80

    def test_line_range_expansion(self):
        record = _make_v2604_record(
            "c1", "2026-01-01T00:00:00Z",
            [DetailFileV2604(
                fileName="app.py",
                codeLines=[
                    _make_add_line_range(1, 5, "c1", "app.py", 1, "2026-01-01T00:00:00Z", gen_ratio=100),
                ],
            )],
        )
        surviving = accumulate_surviving_set([record], end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 5
        for i in range(1, 6):
            assert any(s.original_line == i for s in surviving)

    def test_delete_range_expansion(self):
        records = [
            _make_v2604_record(
                "c1", "2026-01-01T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_line_range(1, 10, "c1", "app.py", 1, "2026-01-01T00:00:00Z", gen_ratio=100),
                    ],
                )],
            ),
            _make_v2604_record(
                "c2", "2026-01-02T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_delete_range_entry("c1", "app.py", 3, 7),
                    ],
                )],
            ),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 5
        remaining_lines = {s.original_line for s in surviving}
        assert remaining_lines == {1, 2, 8, 9, 10}

    def test_timestamp_sorting(self):
        records = [
            _make_v2604_record(
                "c3", "2026-01-03T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_delete_entry("c1", "app.py", 1),
                    ],
                )],
            ),
            _make_v2604_record(
                "c1", "2026-01-01T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(1, "c1", "app.py", 1, "2026-01-01T00:00:00Z"),
                        _make_add_entry(2, "c1", "app.py", 2, "2026-01-01T00:00:00Z"),
                    ],
                )],
            ),
            _make_v2604_record(
                "c2", "2026-01-02T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(3, "c2", "app.py", 3, "2026-01-02T00:00:00Z"),
                    ],
                )],
            ),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 2
        remaining_lines = {s.original_line for s in surviving}
        assert remaining_lines == {2, 3}

    def test_records_after_end_time_ignored(self):
        records = [
            _make_v2604_record(
                "c1", "2026-01-01T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(1, "c1", "app.py", 1, "2026-01-01T00:00:00Z"),
                    ],
                )],
            ),
            _make_v2604_record(
                "c2", "2026-06-01T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_delete_entry("c1", "app.py", 1),
                        _make_add_entry(1, "c2", "app.py", 1, "2026-06-01T00:00:00Z"),
                    ],
                )],
            ),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-03-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].blame_revision_id == "c1"


class TestDuplicateAddEntry:
    def test_duplicate_add_reported(self):
        records = [
            _make_v2604_record(
                "c1", "2026-01-01T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(1, "c1", "app.py", 1, "2026-01-01T00:00:00Z"),
                    ],
                )],
            ),
            _make_v2604_record(
                "c2", "2026-01-02T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(1, "c2", "app.py", 1, "2026-01-02T00:00:00Z", gen_ratio=80),
                    ],
                )],
            ),
        ]
        surviving, warnings = accumulate_surviving_set(
            records, end_time="2026-12-31T23:59:59Z", return_warnings=True,
        )
        assert len(surviving) == 1
        assert len(warnings) >= 1
        assert any("collision" in w.lower() or "duplicate" in w.lower() for w in warnings)


class TestSummaryMismatch:
    def test_summary_mismatch_detected(self):
        record = _make_v2604_record(
            "c1", "2026-01-01T00:00:00Z",
            [DetailFileV2604(
                fileName="app.py",
                codeLines=[
                    _make_add_entry(1, "c1", "app.py", 1, "2026-01-01T00:00:00Z"),
                    _make_add_entry(2, "c1", "app.py", 2, "2026-01-01T00:00:00Z"),
                ],
            )],
            summary_override={
                "totalCodeLines": 500,
                "fullGeneratedCodeLines": 300,
                "partialGeneratedCodeLines": 100,
                "totalDocLines": 0,
                "fullGeneratedDocLines": 0,
                "partialGeneratedDocLines": 0,
            },
        )
        surviving, warnings = accumulate_surviving_set(
            [record], end_time="2026-12-31T23:59:59Z", return_warnings=True,
        )
        mismatch_warnings = [w for w in warnings if "SUMMARY" in w]
        assert len(mismatch_warnings) >= 1


class TestComputeAlgCMetrics:
    def test_in_window_filtering(self):
        records = [
            _make_v2604_record(
                "c1", "2026-01-01T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(1, "c1", "app.py", 1, "2026-01-01T00:00:00Z", gen_ratio=100),
                        _make_add_entry(2, "c1", "app.py", 2, "2026-01-01T00:00:00Z", gen_ratio=0),
                    ],
                )],
            ),
            _make_v2604_record(
                "c2", "2026-03-15T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(3, "c2", "app.py", 3, "2026-03-15T00:00:00Z", gen_ratio=80),
                    ],
                )],
            ),
        ]
        result = compute_alg_c_metrics(
            records,
            start_time="2026-02-01T00:00:00Z",
            end_time="2026-12-31T23:59:59Z",
            threshold=60,
        )
        assert len(result.surviving_lines) >= 1
        assert result.metrics.weighted.value > 0.0


class TestStreaming:
    def test_streaming_matches_in_memory(self, tmp_path):
        from aggregateGenCodeDesc.alg_c import stream_accumulate_surviving_set
        import json

        records = [
            _make_v2604_record(
                "c1", "2026-01-01T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_add_entry(1, "c1", "app.py", 1, "2026-01-01T00:00:00Z", gen_ratio=100),
                        _make_add_entry(2, "c1", "app.py", 2, "2026-01-01T00:00:00Z", gen_ratio=80),
                    ],
                )],
            ),
            _make_v2604_record(
                "c2", "2026-01-02T00:00:00Z",
                [DetailFileV2604(
                    fileName="app.py",
                    codeLines=[
                        _make_delete_entry("c1", "app.py", 2),
                        _make_add_entry(2, "c2", "app.py", 2, "2026-01-02T00:00:00Z", gen_ratio=50),
                    ],
                )],
            ),
        ]
        in_mem = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(in_mem) == 2

        gcd_dir = tmp_path / "gcd"
        gcd_dir.mkdir()
        for i, r in enumerate(records):
            d = {
                "protocolVersion": "26.04",
                "REPOSITORY": {"revisionId": r.REPOSITORY.revisionId, "revisionTimestamp": r.REPOSITORY.revisionTimestamp},
                "DETAIL": [
                    {"fileName": df.fileName, "codeLines": [
                        {"changeType": e.changeType, "genRatio": getattr(e, "genRatio", 0), "genMethod": getattr(e, "genMethod", "Manual"),
                         "lineLocation": e.lineLocation, "blame": {"revisionId": e.blame.revisionId, "originalFilePath": e.blame.originalFilePath, "originalLine": e.blame.originalLine, "timestamp": e.blame.timestamp or ""}}
                        for e in df.codeLines
                    ]}
                    for df in r.DETAIL
                ],
            }
            (gcd_dir / f"{r.REPOSITORY.revisionId}.json").write_text(json.dumps(d))

        streamed = stream_accumulate_surviving_set(str(gcd_dir), end_time="2026-12-31T23:59:59Z")
        assert len(streamed) == len(in_mem)

        in_mem_ratios = {s.gen_ratio for s in in_mem}
        streamed_ratios = {s.gen_ratio for s in streamed}
        assert in_mem_ratios == streamed_ratios

    def test_io_error_on_one_file_continues(self, tmp_path):
        """AC-008-4: Mid-stream I/O failure — unreadable file skipped, others processed."""
        from aggregateGenCodeDesc.alg_c import stream_accumulate_surviving_set
        import json

        gcd_dir = tmp_path / "gcd"
        gcd_dir.mkdir()

        record = _make_v2604_record(
            "c1", "2026-01-01T00:00:00Z",
            [DetailFileV2604(
                fileName="app.py",
                codeLines=[_make_add_entry(1, "c1", "app.py", 1, "2026-01-01T00:00:00Z", gen_ratio=100)],
            )],
        )
        d = {
            "protocolVersion": "26.04",
            "REPOSITORY": {"revisionId": "c1", "revisionTimestamp": "2026-01-01T00:00:00Z"},
            "DETAIL": [{"fileName": "app.py", "codeLines": [{
                "changeType": "add", "genRatio": 100, "genMethod": "vibeCoding",
                "lineLocation": 1,
                "blame": {"revisionId": "c1", "originalFilePath": "app.py", "originalLine": 1, "timestamp": "2026-01-01T00:00:00Z"},
            }]}],
        }

        (gcd_dir / "good.json").write_text(json.dumps(d))
        (gcd_dir / "bad.json").write_text("not valid json {{{")

        streamed, warnings = stream_accumulate_surviving_set(
            str(gcd_dir), end_time="2026-12-31T23:59:59Z", return_warnings=True,
        )
        assert len(streamed) == 1
        assert any("bad.json" in w for w in warnings)
