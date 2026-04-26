from aggregateGenCodeDesc.models import (
    Blame,
    DetailAddEntry,
    DetailFileV2604,
    GenCodeDescV2604,
    RepositoryV2604,
    Summary,
    ValidationError,
)
from aggregateGenCodeDesc.loader import load_gen_code_desc, load_gen_code_desc_dir
from aggregateGenCodeDesc.alg_c import accumulate_surviving_set

import json
import pytest


def _make_v2604(revision_id, timestamp, repo_url="https://example.com/repo"):
    return {
        "protocolName": "generatedTextDesc",
        "protocolVersion": "26.04",
        "codeAgent": "HuayanCoder",
        "SUMMARY": {
            "totalCodeLines": 1,
            "fullGeneratedCodeLines": 1,
            "partialGeneratedCodeLines": 0,
            "totalDocLines": 0,
            "fullGeneratedDocLines": 0,
            "partialGeneratedDocLines": 0,
        },
        "DETAIL": [{
            "fileName": "app.py",
            "codeLines": [{
                "changeType": "add",
                "lineLocation": 1,
                "genRatio": 100,
                "genMethod": "vibeCoding",
                "blame": {
                    "revisionId": revision_id,
                    "originalFilePath": "app.py",
                    "originalLine": 1,
                    "timestamp": timestamp,
                },
            }],
        }],
        "REPOSITORY": {
            "vcsType": "git",
            "repoURL": repo_url,
            "repoBranch": "main",
            "revisionId": revision_id,
            "revisionTimestamp": timestamp,
        },
    }


class TestAmendOrphaned:
    def test_amended_commit_ignored(self, tmp_path):
        """AC-003-5: Amend → old revisionId's genCodeDesc is orphaned. Only new rev used."""
        old_file = tmp_path / "old.json"
        new_file = tmp_path / "new.json"
        old_file.write_text(json.dumps(_make_v2604("aaa", "2026-01-01T00:00:00Z")))
        new_file.write_text(json.dumps(_make_v2604("bbb", "2026-01-02T00:00:00Z")))

        old = load_gen_code_desc(str(old_file))
        new = load_gen_code_desc(str(new_file))

        assert isinstance(old, GenCodeDescV2604)
        assert isinstance(new, GenCodeDescV2604)
        assert old.REPOSITORY.revisionId == "aaa"
        assert new.REPOSITORY.revisionId == "bbb"

        surviving = accumulate_surviving_set([new], end_time="2026-12-31T23:59:59Z")
        assert len(surviving) == 1
        assert surviving[0].blame_revision_id == "bbb"


class TestCherryPickNewGenCode:
    def test_cherry_pick_needs_own_gen_code_desc(self, tmp_path):
        """AC-003-3: Cherry-pick → new commit gets independent genCodeDesc."""
        c1 = json.dumps(_make_v2604("c1_original", "2026-01-01T00:00:00Z"))
        c2 = json.dumps(_make_v2604("c2_cherrypick", "2026-01-02T00:00:00Z"))

        f1 = tmp_path / "c1.json"
        f2 = tmp_path / "c2.json"
        f1.write_text(c1)
        f2.write_text(c2)

        r1 = load_gen_code_desc(str(f1))
        r2 = load_gen_code_desc(str(f2))
        assert r1.REPOSITORY.revisionId == "c1_original"
        assert r2.REPOSITORY.revisionId == "c2_cherrypick"

    def test_wrong_revision_id_rejected(self, tmp_path):
        """AC-003-5: Amend check — wrong revisionId causes REPOSITORY rejection."""
        f = tmp_path / "record.json"
        f.write_text(json.dumps(_make_v2604("aaa", "2026-01-01T00:00:00Z")))
        with pytest.raises(ValidationError, match="revisionId mismatch"):
            load_gen_code_desc(str(f), expected_revision_id="bbb")


class TestRebaseNewRevision:
    def test_rebased_records_all_have_new_ids(self, tmp_path):
        """AC-003-6: Rebase → every replayed commit gets new revisionId."""
        r1 = json.dumps(_make_v2604("111", "2026-01-01T00:00:00Z"))
        r2 = json.dumps(_make_v2604("222", "2026-01-02T00:00:00Z"))
        r3 = json.dumps(_make_v2604("333", "2026-01-03T00:00:00Z"))
        for i, data in enumerate([r1, r2, r3]):
            (tmp_path / f"r{i}.json").write_text(data)

        records = load_gen_code_desc_dir(str(tmp_path))
        ids = {r.REPOSITORY.revisionId for r in records}
        assert ids == {"111", "222", "333"}
        assert len(records) == 3
