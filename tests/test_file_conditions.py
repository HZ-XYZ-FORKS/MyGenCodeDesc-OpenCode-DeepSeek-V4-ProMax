from aggregateGenCodeDesc.models import (
    Blame,
    DetailAddEntry,
    DetailDeleteEntry,
    DetailFileV2604,
    GenCodeDescV2604,
    LineRange,
    RepositoryV2604,
    Summary,
)
from aggregateGenCodeDesc.alg_c import accumulate_surviving_set, compute_alg_c_metrics


def _make_record(revision_id, timestamp, files):
    total_adds = 0
    for df in files:
        for e in df.codeLines:
            if isinstance(e, DetailAddEntry):
                if e.lineRange:
                    total_adds += e.lineRange.to_ - e.lineRange.from_ + 1
                else:
                    total_adds += 1
    return GenCodeDescV2604(
        SUMMARY=Summary(total_adds, 0, 0, 0, 0, 0),
        DETAIL=files,
        REPOSITORY=RepositoryV2604("git", "https://example.com/repo", "main", revision_id, timestamp),
    )


class TestFileRenameAlgC:
    def test_pure_rename_no_detail_entries(self):
        """AC-002-1: Pure rename — v26.04 record has no DETAIL entries. Surviving set unchanged."""
        records = [
            _make_record("c1", "2026-01-01T00:00:00Z", [
                DetailFileV2604("old.py", codeLines=[
                    DetailAddEntry("add", lineLocation=1, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c1", "old.py", 1, timestamp="2026-01-01T00:00:00Z")),
                ]),
            ]),
            _make_record("c2", "2026-01-02T00:00:00Z", []),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].gen_ratio == 100

    def test_rename_and_modify(self):
        """AC-002-2: Rename + modify — delete old line, add new line with different genRatio."""
        records = [
            _make_record("c1", "2026-01-01T00:00:00Z", [
                DetailFileV2604("old.py", codeLines=[
                    DetailAddEntry("add", lineLocation=1, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c1", "old.py", 1, timestamp="2026-01-01T00:00:00Z")),
                ]),
            ]),
            _make_record("c2", "2026-01-02T00:00:00Z", [
                DetailFileV2604("new.py", codeLines=[
                    DetailDeleteEntry("delete", blame=Blame("c1", "old.py", 1)),
                    DetailAddEntry("add", lineLocation=1, genRatio=0, genMethod="Manual",
                                   blame=Blame("c2", "new.py", 1, timestamp="2026-01-02T00:00:00Z")),
                ]),
            ]),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].gen_ratio == 0
        assert surviving[0].blame_revision_id == "c2"

    def test_file_delete_zero_contribution(self):
        """AC-002-3: Deleted file — all lines removed, zero surviving."""
        records = [
            _make_record("c1", "2026-01-01T00:00:00Z", [
                DetailFileV2604("removed.py", codeLines=[
                    DetailAddEntry("add", lineLocation=1, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c1", "removed.py", 1, timestamp="2026-01-01T00:00:00Z")),
                    DetailAddEntry("add", lineLocation=2, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c1", "removed.py", 2, timestamp="2026-01-01T00:00:00Z")),
                ]),
            ]),
            _make_record("c2", "2026-01-15T00:00:00Z", [
                DetailFileV2604("removed.py", codeLines=[
                    DetailDeleteEntry("delete", blame=Blame("c1", "removed.py", 1)),
                    DetailDeleteEntry("delete", blame=Blame("c1", "removed.py", 2)),
                ]),
            ]),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 0


class TestFileCopyAlgC:
    def test_file_copy_new_attribution(self):
        """AC-002-4: File copy — new lines at new path attributed to copy commit."""
        records = [
            _make_record("c1", "2026-01-01T00:00:00Z", [
                DetailFileV2604("lib.py", codeLines=[
                    DetailAddEntry("add", lineLocation=1, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c1", "lib.py", 1, timestamp="2026-01-01T00:00:00Z")),
                ]),
            ]),
            _make_record("c2", "2026-01-15T00:00:00Z", [
                DetailFileV2604("lib_v2.py", codeLines=[
                    DetailAddEntry("add", lineLocation=1, genRatio=0, genMethod="Manual",
                                   blame=Blame("c2", "lib_v2.py", 1, timestamp="2026-01-15T00:00:00Z")),
                ]),
            ]),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 2
        originals = [s for s in surviving if s.original_file_path == "lib.py"]
        copies = [s for s in surviving if s.original_file_path == "lib_v2.py"]
        assert len(originals) == 1 and originals[0].gen_ratio == 100
        assert len(copies) == 1 and copies[0].gen_ratio == 0
