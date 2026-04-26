from aggregateGenCodeDesc.models import (
    Blame,
    DetailAddEntry,
    DetailDeleteEntry,
    DetailFileV2604,
    GenCodeDescV2604,
    RepositoryV2604,
    Summary,
)
from aggregateGenCodeDesc.alg_c import accumulate_surviving_set


def _r(rev_id, ts, files):
    return GenCodeDescV2604(
        SUMMARY=Summary(0, 0, 0, 0, 0, 0),
        DETAIL=files,
        REPOSITORY=RepositoryV2604("git", "https://example.com/repo", "main", rev_id, ts),
    )


class TestOwnershipTransfer:
    def test_ai_to_human(self):
        """AC-004-1: AI line edited by human → ownership transfers to human commit."""
        records = [
            _r("c1", "2026-01-01T00:00:00Z", [
                DetailFileV2604("auth.py", codeLines=[
                    DetailAddEntry("add", lineLocation=42, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c1", "auth.py", 42, timestamp="2026-01-01T00:00:00Z")),
                ]),
            ]),
            _r("c2", "2026-01-15T00:00:00Z", [
                DetailFileV2604("auth.py", codeLines=[
                    DetailDeleteEntry("delete", blame=Blame("c1", "auth.py", 42)),
                    DetailAddEntry("add", lineLocation=42, genRatio=0, genMethod="Manual",
                                   blame=Blame("c2", "auth.py", 42, timestamp="2026-01-15T00:00:00Z")),
                ]),
            ]),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].gen_ratio == 0

    def test_human_to_ai(self):
        """AC-004-2: Human line rewritten by AI → ownership transfers to AI commit."""
        records = [
            _r("c1", "2026-01-01T00:00:00Z", [
                DetailFileV2604("utils.py", codeLines=[
                    DetailAddEntry("add", lineLocation=10, genRatio=0, genMethod="Manual",
                                   blame=Blame("c1", "utils.py", 10, timestamp="2026-01-01T00:00:00Z")),
                ]),
            ]),
            _r("c2", "2026-02-01T00:00:00Z", [
                DetailFileV2604("utils.py", codeLines=[
                    DetailDeleteEntry("delete", blame=Blame("c1", "utils.py", 10)),
                    DetailAddEntry("add", lineLocation=10, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c2", "utils.py", 10, timestamp="2026-02-01T00:00:00Z")),
                ]),
            ]),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].gen_ratio == 100


class TestReAddIdentical:
    def test_re_add_identical_new_origin(self):
        """AC-004-5: Identical content re-added → new origin, same text doesn't mean same attribution."""
        records = [
            _r("c1", "2026-01-01T00:00:00Z", [
                DetailFileV2604("main.py", codeLines=[
                    DetailAddEntry("add", lineLocation=1, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c1", "main.py", 1, timestamp="2026-01-01T00:00:00Z")),
                ]),
            ]),
            _r("c2", "2026-01-10T00:00:00Z", [
                DetailFileV2604("main.py", codeLines=[
                    DetailDeleteEntry("delete", blame=Blame("c1", "main.py", 1)),
                ]),
            ]),
            _r("c3", "2026-01-20T00:00:00Z", [
                DetailFileV2604("main.py", codeLines=[
                    DetailAddEntry("add", lineLocation=1, genRatio=0, genMethod="Manual",
                                   blame=Blame("c3", "main.py", 1, timestamp="2026-01-20T00:00:00Z")),
                ]),
            ]),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].blame_revision_id == "c3"
        assert surviving[0].gen_ratio == 0


class TestLineMove:
    def test_line_move_new_attribution(self):
        """AC-004-6: Line moved within file → attributed to move commit."""
        records = [
            _r("c1", "2026-01-01T00:00:00Z", [
                DetailFileV2604("app.py", codeLines=[
                    DetailAddEntry("add", lineLocation=10, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c1", "app.py", 10, timestamp="2026-01-01T00:00:00Z")),
                ]),
            ]),
            _r("c2", "2026-01-15T00:00:00Z", [
                DetailFileV2604("app.py", codeLines=[
                    DetailDeleteEntry("delete", blame=Blame("c1", "app.py", 10)),
                    DetailAddEntry("add", lineLocation=50, genRatio=100, genMethod="vibeCoding",
                                   blame=Blame("c2", "app.py", 50, timestamp="2026-01-15T00:00:00Z")),
                ]),
            ]),
        ]
        surviving = accumulate_surviving_set(records, end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].blame_revision_id == "c2"
        assert surviving[0].original_line == 50
