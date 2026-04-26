from aggregateGenCodeDesc.models import (
    Blame,
    BlameLineRange,
    GenCodeDescV2603,
    GenCodeDescV2604,
    DetailAddEntry,
    DetailDeleteEntry,
    DetailFileV2603,
    DetailFileV2604,
    LineLocation,
    LineRange,
    Repository,
    RepositoryV2604,
    Summary,
    ValidationError,
    validate_gen_code_desc_v2603,
    validate_gen_code_desc_v2604,
)


class TestLineLocation:
    def test_basic_line_location(self):
        loc = LineLocation(lineLocation=15, genRatio=100, genMethod="codeCompletion")
        assert loc.lineLocation == 15
        assert loc.genRatio == 100
        assert loc.genMethod == "codeCompletion"

    def test_line_location_gen_ratio_zero(self):
        loc = LineLocation(lineLocation=1, genRatio=0, genMethod="Manual")
        assert loc.genRatio == 0
        assert loc.genMethod == "Manual"


class TestLineRange:
    def test_basic_line_range(self):
        rng = LineRange(from_=20, to_=26, genRatio=100, genMethod="vibeCoding")
        assert rng.from_ == 20
        assert rng.to_ == 26
        assert len(rng) == 7

    def test_single_line_range(self):
        rng = LineRange(from_=5, to_=5, genRatio=80, genMethod="codeCompletion")
        assert rng.from_ == 5
        assert rng.to_ == 5
        assert len(rng) == 1


class TestSummary:
    def test_valid_summary(self):
        s = Summary(
            totalCodeLines=99, fullGeneratedCodeLines=8, partialGeneratedCodeLines=2,
            totalDocLines=50, fullGeneratedDocLines=10, partialGeneratedDocLines=5,
        )
        assert s.totalCodeLines == 99
        assert s.fullGeneratedCodeLines == 8
        assert s.partialGeneratedCodeLines == 2

    def test_summary_invariant_code_lines(self):
        valid = Summary(
            totalCodeLines=99, fullGeneratedCodeLines=8, partialGeneratedCodeLines=2,
            totalDocLines=50, fullGeneratedDocLines=10, partialGeneratedDocLines=5,
        )
        assert valid.totalCodeLines >= valid.fullGeneratedCodeLines + valid.partialGeneratedCodeLines

    def test_summary_invariant_equals(self):
        valid = Summary(
            totalCodeLines=10, fullGeneratedCodeLines=5, partialGeneratedCodeLines=5,
            totalDocLines=0, fullGeneratedDocLines=0, partialGeneratedDocLines=0,
        )
        assert valid.totalCodeLines == valid.fullGeneratedCodeLines + valid.partialGeneratedCodeLines


class TestRepository:
    def test_git_repo(self):
        repo = Repository(vcsType="git", repoURL="https://github.com/acme/foo", repoBranch="main", revisionId="1234567890abcdef")
        assert repo.vcsType == "git"
        assert len(repo.revisionId) == 16

    def test_svn_repo(self):
        repo = Repository(vcsType="svn", repoURL="https://svn.example.com/repo", repoBranch="/trunk", revisionId="4217")
        assert repo.vcsType == "svn"
        assert repo.revisionId == "4217"

    def test_v2604_repo_with_timestamp(self):
        repo = RepositoryV2604(
            vcsType="git", repoURL="https://github.com/acme/foo", repoBranch="main",
            revisionId="1234567890abcdef", revisionTimestamp="2026-03-15T10:30:00Z",
        )
        assert repo.revisionTimestamp == "2026-03-15T10:30:00Z"


class TestGenCodeDescV2603:
    def test_valid_v2603_record(self):
        summary = Summary(
            totalCodeLines=99, fullGeneratedCodeLines=8, partialGeneratedCodeLines=2,
            totalDocLines=50, fullGeneratedDocLines=10, partialGeneratedDocLines=5,
        )
        detail = [
            DetailFileV2603(
                fileName="src/main.cxx",
                codeLines=[
                    LineLocation(lineLocation=15, genRatio=100, genMethod="codeCompletion"),
                    LineLocation(lineLocation=16, genRatio=95, genMethod="vibeCoding"),
                    LineRange(from_=20, to_=26, genRatio=100, genMethod="vibeCoding"),
                ],
            ),
        ]
        repo = Repository(vcsType="git", repoURL="https://yfgitlab/PATH/2/nameOfRepo", repoBranch="main", revisionId="1234567890abcdef")
        record = GenCodeDescV2603(SUMMARY=summary, DETAIL=detail, REPOSITORY=repo)
        assert record.protocolVersion == "26.03"
        assert record.SUMMARY.totalCodeLines == 99
        assert len(record.DETAIL) == 1

    def test_v2603_validation_passes(self):
        summary = Summary(
            totalCodeLines=99, fullGeneratedCodeLines=8, partialGeneratedCodeLines=2,
            totalDocLines=50, fullGeneratedDocLines=10, partialGeneratedDocLines=5,
        )
        detail = [
            DetailFileV2603(
                fileName="src/main.cxx",
                codeLines=[LineLocation(lineLocation=15, genRatio=100, genMethod="codeCompletion")],
            ),
        ]
        repo = Repository(vcsType="git", repoURL="https://yfgitlab/PATH/2/nameOfRepo", repoBranch="main", revisionId="1234567890abcdef")
        record = GenCodeDescV2603(SUMMARY=summary, DETAIL=detail, REPOSITORY=repo)
        validate_gen_code_desc_v2603(record)

    def test_v2603_validation_rejects_invalid_gen_ratio_high(self):
        summary = Summary(
            totalCodeLines=99, fullGeneratedCodeLines=8, partialGeneratedCodeLines=2,
            totalDocLines=50, fullGeneratedDocLines=10, partialGeneratedDocLines=5,
        )
        detail = [
            DetailFileV2603(
                fileName="src/main.cxx",
                codeLines=[LineLocation(lineLocation=15, genRatio=150, genMethod="codeCompletion")],
            ),
        ]
        repo = Repository(vcsType="git", repoURL="https://yfgitlab/PATH/2/nameOfRepo", repoBranch="main", revisionId="1234567890abcdef")
        record = GenCodeDescV2603(SUMMARY=summary, DETAIL=detail, REPOSITORY=repo)
        try:
            validate_gen_code_desc_v2603(record)
            assert False, "Expected ValidationError"
        except ValidationError as e:
            assert "genRatio must be 0-100" in str(e)

    def test_v2603_validation_rejects_invalid_gen_ratio_negative(self):
        summary = Summary(
            totalCodeLines=99, fullGeneratedCodeLines=8, partialGeneratedCodeLines=2,
            totalDocLines=50, fullGeneratedDocLines=10, partialGeneratedDocLines=5,
        )
        detail = [
            DetailFileV2603(
                fileName="src/main.cxx",
                codeLines=[LineLocation(lineLocation=15, genRatio=-5, genMethod="codeCompletion")],
            ),
        ]
        repo = Repository(vcsType="git", repoURL="https://yfgitlab/PATH/2/nameOfRepo", repoBranch="main", revisionId="1234567890abcdef")
        record = GenCodeDescV2603(SUMMARY=summary, DETAIL=detail, REPOSITORY=repo)
        try:
            validate_gen_code_desc_v2603(record)
            assert False, "Expected ValidationError"
        except ValidationError as e:
            assert "genRatio must be 0-100" in str(e)


class TestBlame:
    def test_blame_add_entry(self):
        blame = Blame(
            revisionId="1234567890abcdef",
            originalFilePath="relativePath/2/nameOfFileA.cxx",
            originalLine=15,
            timestamp="2026-03-15T10:30:00Z",
            author="jane.doe@example.com",
        )
        assert blame.revisionId == "1234567890abcdef"
        assert blame.originalFilePath == "relativePath/2/nameOfFileA.cxx"
        assert blame.originalLine == 15
        assert blame.timestamp == "2026-03-15T10:30:00Z"

    def test_blame_delete_entry_no_timestamp(self):
        blame = Blame(
            revisionId="fedcba9876543210",
            originalFilePath="relativePath/2/nameOfFileA.cxx",
            originalLine=8,
        )
        assert blame.revisionId == "fedcba9876543210"
        assert blame.timestamp is None

    def test_blame_line_range_delete(self):
        blame = BlameLineRange(
            revisionId="fedcba9876543210",
            originalFilePath="relativePath/2/nameOfFileA.cxx",
            originalLineRange=LineRange(from_=9, to_=14, genRatio=0, genMethod="Manual"),
        )
        assert blame.originalLineRange.from_ == 9
        assert blame.originalLineRange.to_ == 14


class TestGenCodeDescV2604:
    def test_v2604_add_entry(self):
        entry = DetailAddEntry(
            changeType="add",
            lineLocation=15,
            genRatio=100,
            genMethod="codeCompletion",
            blame=Blame(
                revisionId="1234567890abcdef",
                originalFilePath="relativePath/2/nameOfFileA.cxx",
                originalLine=15,
                timestamp="2026-03-15T10:30:00Z",
            ),
        )
        assert entry.changeType == "add"
        assert entry.genRatio == 100

    def test_v2604_delete_entry(self):
        entry = DetailDeleteEntry(
            changeType="delete",
            blame=Blame(
                revisionId="fedcba9876543210",
                originalFilePath="relativePath/2/nameOfFileA.cxx",
                originalLine=8,
            ),
        )
        assert entry.changeType == "delete"

    def test_v2604_add_with_line_range(self):
        entry = DetailAddEntry(
            changeType="add",
            lineRange=LineRange(from_=2, to_=14, genRatio=0, genMethod="Manual"),
            genRatio=0,
            genMethod="Manual",
            blame=Blame(
                revisionId="fedcba9876543210",
                originalFilePath="relativePath/2/nameOfFileA.cxx",
                originalLine=2,
                timestamp="2026-01-10T09:00:00Z",
            ),
        )
        assert entry.lineRange.from_ == 2
        assert entry.lineRange.to_ == 14

    def test_v2604_full_record(self):
        summary = Summary(
            totalCodeLines=24, fullGeneratedCodeLines=8, partialGeneratedCodeLines=2,
            totalDocLines=14, fullGeneratedDocLines=10, partialGeneratedDocLines=4,
        )
        detail = [
            DetailFileV2604(
                fileName="relativePath/2/nameOfFileA.cxx",
                codeLines=[
                    DetailDeleteEntry(
                        changeType="delete",
                        blame=Blame(revisionId="fedcba9876543210", originalFilePath="relativePath/2/nameOfFileA.cxx", originalLine=8),
                    ),
                    DetailAddEntry(
                        changeType="add",
                        lineLocation=15,
                        genRatio=100,
                        genMethod="codeCompletion",
                        blame=Blame(revisionId="1234567890abcdef", originalFilePath="relativePath/2/nameOfFileA.cxx", originalLine=15, timestamp="2026-03-15T10:30:00Z"),
                    ),
                ],
            ),
        ]
        repo = RepositoryV2604(
            vcsType="git", repoURL="https://yfgitlab/PATH/2/nameOfRepo", repoBranch="main",
            revisionId="1234567890abcdef", revisionTimestamp="2026-03-15T10:30:00Z",
        )
        record = GenCodeDescV2604(SUMMARY=summary, DETAIL=detail, REPOSITORY=repo)
        assert record.protocolVersion == "26.04"
        assert record.REPOSITORY.revisionTimestamp == "2026-03-15T10:30:00Z"

    def test_v2604_validation_rejects_invalid_gen_ratio(self):
        summary = Summary(
            totalCodeLines=24, fullGeneratedCodeLines=8, partialGeneratedCodeLines=2,
            totalDocLines=0, fullGeneratedDocLines=0, partialGeneratedDocLines=0,
        )
        detail = [
            DetailFileV2604(
                fileName="test.py",
                codeLines=[
                    DetailAddEntry(
                        changeType="add",
                        lineLocation=1,
                        genRatio=150,
                        genMethod="codeCompletion",
                        blame=Blame(revisionId="abc", originalFilePath="test.py", originalLine=1, timestamp="2026-01-01T00:00:00Z"),
                    ),
                ],
            ),
        ]
        repo = RepositoryV2604(
            vcsType="git", repoURL="https://example.com/repo", repoBranch="main",
            revisionId="abc", revisionTimestamp="2026-01-01T00:00:00Z",
        )
        record = GenCodeDescV2604(SUMMARY=summary, DETAIL=detail, REPOSITORY=repo)
        try:
            validate_gen_code_desc_v2604(record)
            assert False, "Expected ValidationError"
        except ValidationError as e:
            assert "genRatio must be 0-100" in str(e)
