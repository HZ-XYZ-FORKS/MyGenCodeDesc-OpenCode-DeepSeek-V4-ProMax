import json
import pytest
from pathlib import Path

from aggregateGenCodeDesc.models import (
    Blame,
    DetailAddEntry,
    DetailDeleteEntry,
    DetailFileV2603,
    DetailFileV2604,
    GenCodeDescV2603,
    GenCodeDescV2604,
    LineLocation,
    LineRange,
    Repository,
    RepositoryV2604,
    Summary,
    ValidationError,
)
from aggregateGenCodeDesc.loader import (
    load_gen_code_desc,
    load_gen_code_desc_dir,
    ProtocolVersion,
)


V2603_JSON = """{
    "protocolName": "generatedTextDesc",
    "protocolVersion": "26.03",
    "codeAgent": "HuayanCoder",
    "SUMMARY": {
        "totalCodeLines": 99,
        "fullGeneratedCodeLines": 8,
        "partialGeneratedCodeLines": 2,
        "totalDocLines": 50,
        "fullGeneratedDocLines": 10,
        "partialGeneratedDocLines": 5
    },
    "DETAIL": [
        {
            "fileName": "src/main.cxx",
            "codeLines": [
                {"lineLocation": 15, "genRatio": 100, "genMethod": "codeCompletion"},
                {"lineLocation": 16, "genRatio": 95, "genMethod": "vibeCoding"},
                {"lineRange": {"from": 20, "to": 26}, "genRatio": 100, "genMethod": "vibeCoding"}
            ],
            "docLines": [
                {"lineLocation": 15, "genRatio": 90, "genMethod": "vibeCoding"}
            ]
        }
    ],
    "CREDENTIAL": {
        "accessToken": "1234567890abcdef"
    },
    "REPOSITORY": {
        "vcsType": "git",
        "repoURL": "https://yfgitlab/PATH/2/nameOfRepo",
        "repoBranch": "main",
        "revisionId": "1234567890abcdef"
    }
}"""


V2604_JSON = """{
    "protocolName": "generatedTextDesc",
    "protocolVersion": "26.04",
    "codeAgent": "HuayanCoder",
    "SUMMARY": {
        "totalCodeLines": 24,
        "fullGeneratedCodeLines": 8,
        "partialGeneratedCodeLines": 2,
        "totalDocLines": 14,
        "fullGeneratedDocLines": 10,
        "partialGeneratedDocLines": 4
    },
    "DETAIL": [
        {
            "fileName": "src/main.cxx",
            "codeLines": [
                {
                    "changeType": "delete",
                    "blame": {"revisionId": "fedcba9876543210", "originalFilePath": "src/main.cxx", "originalLine": 8}
                },
                {
                    "changeType": "add",
                    "lineLocation": 15, "genRatio": 100, "genMethod": "codeCompletion",
                    "blame": {"revisionId": "1234567890abcdef", "originalFilePath": "src/main.cxx", "originalLine": 15, "timestamp": "2026-03-15T10:30:00Z"}
                }
            ]
        }
    ],
    "REPOSITORY": {
        "vcsType": "git",
        "repoURL": "https://yfgitlab/PATH/2/nameOfRepo",
        "repoBranch": "main",
        "revisionId": "1234567890abcdef",
        "revisionTimestamp": "2026-03-15T10:30:00Z"
    }
}"""


V2604_WITH_LINE_RANGE_JSON = """{
    "protocolName": "generatedTextDesc",
    "protocolVersion": "26.04",
    "codeAgent": "HuayanCoder",
    "SUMMARY": {
        "totalCodeLines": 14,
        "fullGeneratedCodeLines": 0,
        "partialGeneratedCodeLines": 0,
        "totalDocLines": 0,
        "fullGeneratedDocLines": 0,
        "partialGeneratedDocLines": 0
    },
    "DETAIL": [
        {
            "fileName": "src/main.cxx",
            "codeLines": [
                {
                    "changeType": "add",
                    "lineRange": {"from": 2, "to": 14}, "genRatio": 0, "genMethod": "Manual",
                    "blame": {"revisionId": "abcdef", "originalFilePath": "src/main.cxx", "originalLine": 2, "timestamp": "2026-01-10T09:00:00Z"}
                }
            ]
        }
    ],
    "REPOSITORY": {
        "vcsType": "git",
        "repoURL": "https://example.com/repo",
        "repoBranch": "main",
        "revisionId": "abcdef",
        "revisionTimestamp": "2026-01-10T09:00:00Z"
    }
}"""


V2604_DELETE_RANGE_JSON = """{
    "protocolName": "generatedTextDesc",
    "protocolVersion": "26.04",
    "codeAgent": "HuayanCoder",
    "SUMMARY": {
        "totalCodeLines": 0,
        "fullGeneratedCodeLines": 0,
        "partialGeneratedCodeLines": 0,
        "totalDocLines": 0,
        "fullGeneratedDocLines": 0,
        "partialGeneratedDocLines": 0
    },
    "DETAIL": [
        {
            "fileName": "src/main.cxx",
            "codeLines": [
                {
                    "changeType": "delete",
                    "blame": {"revisionId": "fedcba", "originalFilePath": "src/main.cxx", "originalLineRange": {"from": 9, "to": 14}}
                }
            ]
        }
    ],
    "REPOSITORY": {
        "vcsType": "git",
        "repoURL": "https://example.com/repo",
        "repoBranch": "main",
        "revisionId": "abcdef",
        "revisionTimestamp": "2026-01-10T09:00:00Z"
    }
}"""


class TestLoadV2603:
    def test_load_basic_v2603(self, tmp_path):
        filepath = tmp_path / "test.json"
        filepath.write_text(V2603_JSON)
        record = load_gen_code_desc(str(filepath))
        assert isinstance(record, GenCodeDescV2603)
        assert record.protocolVersion == "26.03"
        assert record.SUMMARY.totalCodeLines == 99
        assert record.REPOSITORY.revisionId == "1234567890abcdef"

    def test_load_v2603_detail_content(self, tmp_path):
        filepath = tmp_path / "test.json"
        filepath.write_text(V2603_JSON)
        record = load_gen_code_desc(str(filepath))
        assert len(record.DETAIL) == 1
        detail = record.DETAIL[0]
        assert detail.fileName == "src/main.cxx"
        assert len(detail.codeLines) == 3
        assert isinstance(detail.codeLines[0], LineLocation)
        assert detail.codeLines[0].genRatio == 100
        assert isinstance(detail.codeLines[2], LineRange)
        assert detail.codeLines[2].from_ == 20
        assert len(detail.docLines) == 1

    def test_load_v2603_repo_mismatch_rejected(self, tmp_path):
        data = json.loads(V2603_JSON)
        data["REPOSITORY"]["repoURL"] = "https://other-repo.com"
        filepath = tmp_path / "test.json"
        filepath.write_text(json.dumps(data))
        with pytest.raises(ValidationError, match="REPOSITORY.repoURL mismatch"):
            load_gen_code_desc(str(filepath), expected_repo_url="https://expected.com")

    def test_load_v2603_repo_branch_mismatch(self, tmp_path):
        data = json.loads(V2603_JSON)
        data["REPOSITORY"]["repoBranch"] = "develop"
        filepath = tmp_path / "test.json"
        filepath.write_text(json.dumps(data))
        with pytest.raises(ValidationError, match="REPOSITORY.repoBranch mismatch"):
            load_gen_code_desc(str(filepath), expected_repo_branch="main")

    def test_load_v2603_without_credential(self, tmp_path):
        data = json.loads(V2603_JSON)
        del data["CREDENTIAL"]
        filepath = tmp_path / "test.json"
        filepath.write_text(json.dumps(data))
        record = load_gen_code_desc(str(filepath))
        assert record.SUMMARY.totalCodeLines == 99


class TestLoadV2604:
    def test_load_basic_v2604(self, tmp_path):
        filepath = tmp_path / "test.json"
        filepath.write_text(V2604_JSON)
        record = load_gen_code_desc(str(filepath))
        assert isinstance(record, GenCodeDescV2604)
        assert record.protocolVersion == "26.04"
        assert record.REPOSITORY.revisionTimestamp == "2026-03-15T10:30:00Z"

    def test_load_v2604_add_entry(self, tmp_path):
        filepath = tmp_path / "test.json"
        filepath.write_text(V2604_JSON)
        record = load_gen_code_desc(str(filepath))
        detail = record.DETAIL[0]
        add_entries = [e for e in detail.codeLines if isinstance(e, DetailAddEntry)]
        assert len(add_entries) == 1
        assert add_entries[0].genRatio == 100
        assert add_entries[0].blame.revisionId == "1234567890abcdef"

    def test_load_v2604_delete_entry(self, tmp_path):
        filepath = tmp_path / "test.json"
        filepath.write_text(V2604_JSON)
        record = load_gen_code_desc(str(filepath))
        detail = record.DETAIL[0]
        delete_entries = [e for e in detail.codeLines if isinstance(e, DetailDeleteEntry)]
        assert len(delete_entries) == 1
        assert delete_entries[0].blame.revisionId == "fedcba9876543210"

    def test_load_v2604_add_with_line_range(self, tmp_path):
        filepath = tmp_path / "test.json"
        filepath.write_text(V2604_WITH_LINE_RANGE_JSON)
        record = load_gen_code_desc(str(filepath))
        detail = record.DETAIL[0]
        add_entry = detail.codeLines[0]
        assert isinstance(add_entry, DetailAddEntry)
        assert add_entry.lineRange.from_ == 2
        assert add_entry.lineRange.to_ == 14
        assert add_entry.blame.originalLine == 2

    def test_load_v2604_delete_with_line_range(self, tmp_path):
        filepath = tmp_path / "test.json"
        filepath.write_text(V2604_DELETE_RANGE_JSON)
        record = load_gen_code_desc(str(filepath))
        detail = record.DETAIL[0]
        delete_entry = detail.codeLines[0]
        assert isinstance(delete_entry, DetailDeleteEntry)
        assert delete_entry.blame.originalLineRange.from_ == 9
        assert delete_entry.blame.originalLineRange.to_ == 14

    def test_load_v2604_revision_id_mismatch(self, tmp_path):
        data = json.loads(V2604_JSON)
        data["REPOSITORY"]["revisionId"] = "wrong"
        filepath = tmp_path / "test.json"
        filepath.write_text(json.dumps(data))
        with pytest.raises(ValidationError, match="REPOSITORY.revisionId mismatch"):
            load_gen_code_desc(str(filepath), expected_revision_id="expected_id")

    def test_auto_detect_protocol_version(self, tmp_path):
        v2603_file = tmp_path / "v2603.json"
        v2604_file = tmp_path / "v2604.json"
        v2603_file.write_text(V2603_JSON)
        v2604_file.write_text(V2604_JSON)
        r3 = load_gen_code_desc(str(v2603_file))
        r4 = load_gen_code_desc(str(v2604_file))
        assert isinstance(r3, GenCodeDescV2603)
        assert isinstance(r4, GenCodeDescV2604)


class TestLoadDir:
    def test_load_dir_mixed_versions_rejected(self, tmp_path):
        dirpath = tmp_path / "gcd"
        dirpath.mkdir()
        (dirpath / "a.json").write_text(V2603_JSON)
        (dirpath / "b.json").write_text(V2604_JSON)
        with pytest.raises(ValidationError, match="Mixed protocol versions"):
            load_gen_code_desc_dir(str(dirpath))

    def test_load_dir_all_v2603(self, tmp_path):
        dirpath = tmp_path / "gcd"
        dirpath.mkdir()
        (dirpath / "a.json").write_text(V2603_JSON)
        (dirpath / "b.json").write_text(V2603_JSON)
        records = load_gen_code_desc_dir(str(dirpath))
        assert len(records) == 2
        assert all(isinstance(r, GenCodeDescV2603) for r in records)

    def test_load_dir_all_v2604(self, tmp_path):
        dirpath = tmp_path / "gcd"
        dirpath.mkdir()
        (dirpath / "a.json").write_text(V2604_JSON)
        (dirpath / "b.json").write_text(V2604_JSON)
        records = load_gen_code_desc_dir(str(dirpath))
        assert len(records) == 2
        assert all(isinstance(r, GenCodeDescV2604) for r in records)

    def test_load_dir_repo_validation(self, tmp_path):
        dirpath = tmp_path / "gcd"
        dirpath.mkdir()
        (dirpath / "a.json").write_text(V2603_JSON)
        data = json.loads(V2603_JSON)
        data["REPOSITORY"]["repoURL"] = "https://other.com/repo"
        (dirpath / "b.json").write_text(json.dumps(data))
        with pytest.raises(ValidationError, match="REPOSITORY.repoURL mismatch"):
            load_gen_code_desc_dir(str(dirpath), expected_repo_url="https://yfgitlab/PATH/2/nameOfRepo")
