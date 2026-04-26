from aggregateGenCodeDesc.models import (
    Blame, DetailAddEntry, DetailDeleteEntry, DetailFileV2604,
    GenCodeDescV2604, RepositoryV2604, Summary,
)
from aggregateGenCodeDesc.alg_c import accumulate_surviving_set


def _r(rev_id, ts, files):
    return GenCodeDescV2604(
        SUMMARY=Summary(0, 0, 0, 0, 0, 0),
        DETAIL=files,
        REPOSITORY=RepositoryV2604("git", "https://example.com/repo", "main", rev_id, ts),
    )


class TestMultiMerge:
    def test_lines_from_different_branches_each_have_one_origin(self):
        """AC-005-2: Lines from 3 merged branches each retain distinct origin revision."""
        records = [
            _r("c1", "2026-01-01T00:00:00Z", [
                DetailFileV2604("main.py", codeLines=[
                    DetailAddEntry("add", lineLocation=1, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c1", "main.py", 1, timestamp="2026-01-01T00:00:00Z")),
                ]),
            ]),
            _r("c2", "2026-01-05T00:00:00Z", [
                DetailFileV2604("main.py", codeLines=[
                    DetailAddEntry("add", lineLocation=2, genRatio=80, genMethod="codeCompletion",
                                   blame=Blame("c2", "main.py", 2, timestamp="2026-01-05T00:00:00Z")),
                ]),
            ]),
            _r("c3", "2026-01-10T00:00:00Z", [
                DetailFileV2604("main.py", codeLines=[
                    DetailAddEntry("add", lineLocation=3, genRatio=0, genMethod="Manual",
                                   blame=Blame("c3", "main.py", 3, timestamp="2026-01-10T00:00:00Z")),
                ]),
            ]),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 3
        origins = {s.blame_revision_id for s in surviving}
        assert origins == {"c1", "c2", "c3"}


class TestLongLivedBranch:
    def test_long_lived_branch_lines_traced_to_origin(self):
        """AC-005-3: Lines from branch diverged long ago traced to actual origin."""
        records = [
            _r("c_old_feature", "2025-06-01T00:00:00Z", [
                DetailFileV2604("feature.py", codeLines=[
                    DetailAddEntry("add", lineLocation=1, genRatio=80, genMethod="vibeCoding",
                                   blame=Blame("c_old_feature", "feature.py", 1, timestamp="2025-06-01T00:00:00Z")),
                ]),
            ]),
            _r("c_merge", "2026-01-15T00:00:00Z", []),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].blame_revision_id == "c_old_feature"
        assert surviving[0].gen_ratio == 80
