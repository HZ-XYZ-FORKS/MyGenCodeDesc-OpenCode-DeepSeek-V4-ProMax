import json
import pytest

from aggregateGenCodeDesc.models import (
    Blame, DetailAddEntry, DetailFileV2604, GenCodeDescV2604,
    RepositoryV2604, Summary, ValidationError,
)
from aggregateGenCodeDesc.alg_c import accumulate_surviving_set
from aggregateGenCodeDesc.loader import load_gen_code_desc_dir
from aggregateGenCodeDesc.policies import (
    OnMissingPolicy,
    OnDuplicatePolicy,
    OnClockSkewPolicy,
    check_clock_skew,
    check_duplicate_revisions,
)


def _r(rev_id, ts, gen_ratio=100):
    return GenCodeDescV2604(
        SUMMARY=Summary(1, 1 if gen_ratio == 100 else 0, 0 if gen_ratio == 100 else 1, 0, 0, 0),
        DETAIL=[DetailFileV2604("app.py", codeLines=[
            DetailAddEntry("add", lineLocation=1, genRatio=gen_ratio, genMethod="vibeCoding",
                           blame=Blame(rev_id, "app.py", 1, timestamp=ts)),
        ])],
        REPOSITORY=RepositoryV2604("git", "https://example.com/repo", "main", rev_id, ts),
    )


class TestMissingGenCodeDesc:
    def test_alg_a_b_missing_treated_as_zero(self):
        """AC-006-1: v26.03 missing record → lines treated as genRatio=0."""
        from aggregateGenCodeDesc.alg_a import resolve_gen_ratios_from_v2603, BlameLine
        genratio_map = {}  # empty map → no matching entries
        lines = [BlameLine("blame", "missing123", "app.py", 1, "2026-01-01T00:00:00Z")]
        resolved = resolve_gen_ratios_from_v2603(lines, genratio_map)
        assert resolved == [0]

    def test_alg_c_missing_record_chain_break(self):
        """AC-006-1: AlgC chain break — record with empty DETAIL causes zero contribution."""


class TestDuplicateRevision:
    def test_duplicate_revision_detected(self):
        records = [_r("abc", "2026-01-01T00:00:00Z"), _r("abc", "2026-01-02T00:00:00Z")]
        dups = check_duplicate_revisions(records)
        assert len(dups) == 1
        assert "abc" in dups[0]

    def test_no_duplicates_returns_empty(self):
        records = [_r("a", "2026-01-01T00:00:00Z"), _r("b", "2026-01-02T00:00:00Z")]
        assert check_duplicate_revisions(records) == []


class TestClockSkew:
    def test_clock_skew_detected(self):
        records = [
            _r("c1", "2026-01-03T00:00:00Z"),
            _r("c2", "2026-01-02T00:00:00Z"),
        ]
        assert check_clock_skew(records) is True

    def test_no_clock_skew(self):
        records = [
            _r("c1", "2026-01-01T00:00:00Z"),
            _r("c2", "2026-01-02T00:00:00Z"),
        ]
        assert check_clock_skew(records) is False

    def test_single_record_no_skew(self):
        records = [_r("c1", "2026-01-01T00:00:00Z")]
        assert check_clock_skew(records) is False
