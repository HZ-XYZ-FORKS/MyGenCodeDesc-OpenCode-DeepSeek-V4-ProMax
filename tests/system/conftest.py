import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone

import pytest


def ts(iso_str: str) -> str:
    return iso_str


def _git(cwd: Path, *args) -> str:
    result = subprocess.run(
        ["git"] + list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def _write_v2603(out_dir, rev_id, repo_url, repo_branch, entries):
    code_lines = []
    for e in entries:
        if e["type"] == "add":
            entry = {"genRatio": e.get("genRatio", 0), "genMethod": e.get("genMethod", "Manual")}
            if "lineLocation" in e:
                entry["lineLocation"] = e["lineLocation"]
            if "lineRange" in e:
                entry["lineRange"] = e["lineRange"]
            code_lines.append((e.get("file", ""), entry))
    if not code_lines:
        return
    from collections import OrderedDict
    detail = OrderedDict()
    for fn, entry in code_lines:
        if fn not in detail:
            detail[fn] = {"fileName": fn, "codeLines": []}
        detail[fn]["codeLines"].append(entry)
    (out_dir / f"{rev_id}.json").write_text(json.dumps({
        "protocolName": "generatedTextDesc",
        "protocolVersion": "26.03",
        "codeAgent": "FixtureGen",
        "SUMMARY": {"totalCodeLines": 0, "fullGeneratedCodeLines": 0, "partialGeneratedCodeLines": 0,
                     "totalDocLines": 0, "fullGeneratedDocLines": 0, "partialGeneratedDocLines": 0},
        "DETAIL": list(detail.values()),
        "REPOSITORY": {"vcsType": "git", "repoURL": repo_url, "repoBranch": repo_branch, "revisionId": rev_id},
    }, indent=2))


def _make_gencode_v2604(rev_id: str, timestamp: str, repo_url: str, repo_branch: str, entries: list) -> dict:
    code_lines = []
    total_adds = 0
    full_gen = 0
    partial_gen = 0
    for e in entries:
        entry = {
            "changeType": e["type"],
            "genRatio": e.get("genRatio", 0),
            "genMethod": e.get("genMethod", "Manual"),
            "blame": {
                "revisionId": e.get("blame_rev_id", rev_id),
                "originalFilePath": e.get("blame_file", e.get("file", "")),
                "originalLine": e.get("blame_line", e.get("line", 1)),
                "timestamp": e.get("blame_ts", timestamp),
            },
        }
        if "lineLocation" in e:
            entry["lineLocation"] = e["lineLocation"]
        if "lineRange" in e:
            entry["lineRange"] = e["lineRange"]
        if e["type"] == "delete":
            del entry["genRatio"]
            del entry["genMethod"]
        if e["type"] == "delete" and "lineRange" in e:
            entry["blame"]["originalLineRange"] = entry["blame"].pop("originalLine", None) or e["lineRange"]
        else:
            entry["blame"]["originalLine"] = e.get("blame_line", e.get("line", 1))
        if e["type"] == "add":
            count = 1
            if "lineRange" in e:
                count = e["lineRange"]["to"] - e["lineRange"]["from"] + 1
            total_adds += count
            if e.get("genRatio", 0) == 100:
                full_gen += count
            elif e.get("genRatio", 0) > 0:
                partial_gen += count
        code_lines.append(entry)

    return {
        "protocolName": "generatedTextDesc",
        "protocolVersion": "26.04",
        "codeAgent": "FixtureGen",
        "SUMMARY": {
            "totalCodeLines": total_adds,
            "fullGeneratedCodeLines": full_gen,
            "partialGeneratedCodeLines": partial_gen,
            "totalDocLines": 0,
            "fullGeneratedDocLines": 0,
            "partialGeneratedDocLines": 0,
        },
        "DETAIL": [{"fileName": e.get("file", ""), "codeLines": [e]} for e in code_lines],
        "REPOSITORY": {
            "vcsType": "git",
            "repoURL": repo_url,
            "repoBranch": repo_branch,
            "revisionId": rev_id,
            "revisionTimestamp": timestamp,
        },
    }


def _merge_detail_entries(entries: list) -> list:
    from collections import OrderedDict
    grouped = OrderedDict()
    for e in entries:
        fn = e["file"]
        if fn not in grouped:
            grouped[fn] = {"fileName": fn, "codeLines": []}
        grouped[fn]["codeLines"].append(e)
    return list(grouped.values())


def _make_gendesc_json_v2604(rev_id: str, timestamp: str, repo_url: str, repo_branch: str, entries: list) -> dict:
    total_adds = 0
    full_gen = 0
    partial_gen = 0
    code_lines = []
    for e in entries:
        entry = {"changeType": e["type"], "file": e.get("file", "")}
        if e["type"] == "add":
            entry["genRatio"] = e.get("genRatio", 0)
            entry["genMethod"] = e.get("genMethod", "Manual")
            if "lineLocation" in e:
                entry["lineLocation"] = e["lineLocation"]
            if "lineRange" in e:
                entry["lineRange"] = e["lineRange"]
            count = 1
            if "lineRange" in e:
                count = e["lineRange"]["to"] - e["lineRange"]["from"] + 1
            total_adds += count
            if e.get("genRatio", 0) == 100:
                full_gen += count
            elif e.get("genRatio", 0) > 0:
                partial_gen += count
        blame = {
            "revisionId": e.get("blame_rev_id", rev_id),
            "originalFilePath": e.get("blame_file", e.get("file", "")),
        }
        if e["type"] == "delete" and "lineRange" in e:
            blame["originalLineRange"] = e["lineRange"]
        else:
            blame["originalLine"] = e.get("blame_line", e.get("line", 1))
        if e["type"] == "add":
            blame["timestamp"] = e.get("blame_ts", timestamp)
        entry["blame"] = blame
        code_lines.append(entry)

    merged = _merge_detail_entries(code_lines)
    return {
        "protocolName": "generatedTextDesc",
        "protocolVersion": "26.04",
        "codeAgent": "FixtureGen",
        "SUMMARY": {
            "totalCodeLines": total_adds,
            "fullGeneratedCodeLines": full_gen,
            "partialGeneratedCodeLines": partial_gen,
            "totalDocLines": 0,
            "fullGeneratedDocLines": 0,
            "partialGeneratedDocLines": 0,
        },
        "DETAIL": merged,
        "REPOSITORY": {
            "vcsType": "git",
            "repoURL": repo_url,
            "repoBranch": repo_branch,
            "revisionId": rev_id,
            "revisionTimestamp": timestamp,
        },
    }


@pytest.fixture(scope="session")
def prod_repo(tmp_path_factory):
    """Build a production-like Git repo with 12 commits covering all VCS conditions."""
    base = tmp_path_factory.mktemp("prod_repo")
    repo_dir = base / "repo"
    gencode_dir = base / "gencode"
    gencode_v2603_dir = base / "gencode_v2603"
    repo_dir.mkdir()
    gencode_dir.mkdir()
    gencode_v2603_dir.mkdir()

    repo_url = f"file://{repo_dir}"
    branch = "main"

    _git(repo_dir, "init", "-b", branch)
    _git(repo_dir, "config", "user.name", "Test User")
    _git(repo_dir, "config", "user.email", "test@example.com")

    revs = {}

    # C0: initial commit — empty file to establish repo
    (repo_dir / "main.py").write_text("")
    (repo_dir / "utils.py").write_text("")
    (repo_dir / "docs").mkdir()
    (repo_dir / "docs" / "readme.md").write_text("")
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", "C0: init", "--date", "2026-01-01T00:00:00Z")
    revs["C0"] = _git(repo_dir, "rev-parse", "HEAD")

    # C1: normal add — main.py +50 lines, 80% AI (40 lines=100, 10 lines=0)
    main_content = "\n".join(f"line {i}" for i in range(1, 51))
    (repo_dir / "main.py").write_text(main_content)
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", "C1: add main.py content", "--date", "2026-01-15T00:00:00Z")
    revs["C1"] = _git(repo_dir, "rev-parse", "HEAD")
    c1_ts = "2026-01-15T00:00:00Z"
    c1_entries = [
        {"type": "add", "lineRange": {"from": 1, "to": 40}, "genRatio": 100, "genMethod": "vibeCoding",
         "file": "main.py", "blame_rev_id": revs["C1"], "blame_file": "main.py", "blame_line": 1, "blame_ts": c1_ts},
        {"type": "add", "lineRange": {"from": 41, "to": 50}, "genRatio": 0, "genMethod": "Manual",
         "file": "main.py", "blame_rev_id": revs["C1"], "blame_file": "main.py", "blame_line": 41, "blame_ts": c1_ts},
    ]
    (gencode_dir / f"{revs['C1']}.json").write_text(
        json.dumps(_make_gendesc_json_v2604(revs["C1"], c1_ts, repo_url, branch, c1_entries), indent=2))
    _write_v2603(gencode_v2603_dir, revs["C1"], repo_url, branch, c1_entries)

    # C2: rename + add content — utils.py → helpers.py with content
    _git(repo_dir, "mv", "utils.py", "helpers.py")
    (repo_dir / "helpers.py").write_text("# helper utilities\ndef helper():\n    return True\n")
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", "C2: rename utils.py to helpers.py", "--date", "2026-01-20T00:00:00Z")
    revs["C2"] = _git(repo_dir, "rev-parse", "HEAD")

    # C3: branch + new file — create feature branch, add feature.py (100% AI)
    _git(repo_dir, "checkout", "-b", "feature")
    (repo_dir / "feature.py").write_text("def feature_a():\n    return True\n")
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", "C3: add feature.py on feature branch", "--date", "2026-02-01T00:00:00Z")
    revs["C3"] = _git(repo_dir, "rev-parse", "HEAD")
    c3_ts = "2026-02-01T00:00:00Z"
    c3_entries = [
        {"type": "add", "lineRange": {"from": 1, "to": 2}, "genRatio": 100, "genMethod": "vibeCoding",
         "file": "feature.py", "blame_rev_id": revs["C3"], "blame_file": "feature.py", "blame_line": 1, "blame_ts": c3_ts},
    ]
    (gencode_dir / f"{revs['C3']}.json").write_text(
        json.dumps(_make_gendesc_json_v2604(revs["C3"], c3_ts, repo_url, branch, c3_entries), indent=2))

    # C4: back to main, modify main.py line 5 (human rewrites AI line)
    _git(repo_dir, "checkout", branch)
    lines = (repo_dir / "main.py").read_text().split("\n")
    lines[4] = "line 5 - rewritten by human"
    (repo_dir / "main.py").write_text("\n".join(lines))
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", "C4: human rewrites main.py line 5", "--date", "2026-02-15T00:00:00Z")
    revs["C4"] = _git(repo_dir, "rev-parse", "HEAD")
    c4_ts = "2026-02-15T00:00:00Z"
    c4_entries = [
        {"type": "delete", "file": "main.py", "blame_rev_id": revs["C1"], "blame_file": "main.py", "blame_line": 5},
        {"type": "add", "lineLocation": 5, "genRatio": 0, "genMethod": "Manual",
         "file": "main.py", "blame_rev_id": revs["C4"], "blame_file": "main.py", "blame_line": 5, "blame_ts": c4_ts},
    ]
    (gencode_dir / f"{revs['C4']}.json").write_text(
        json.dumps(_make_gendesc_json_v2604(revs["C4"], c4_ts, repo_url, branch, c4_entries), indent=2))

    # C5: merge feature branch into main (no genCodeDesc — blame traces through)
    _git(repo_dir, "merge", "feature", "--no-ff", "-m", "C5: merge feature branch")
    revs["C5"] = _git(repo_dir, "rev-parse", "HEAD")

    # C6: delete docs/readme.md
    (repo_dir / "docs" / "readme.md").unlink()
    _git(repo_dir, "rm", "docs/readme.md")
    _git(repo_dir, "commit", "-m", "C6: delete docs/readme.md", "--date", "2026-03-10T00:00:00Z")
    revs["C6"] = _git(repo_dir, "rev-parse", "HEAD")

    # C7: squash merge simulation — add 3 lines representing squash
    (repo_dir / "squashed.py").write_text("result_a = 1\nresult_b = 2\nresult_c = 3\n")
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", "C7: squash 3 commits into one", "--date", "2026-03-15T00:00:00Z")
    revs["C7"] = _git(repo_dir, "rev-parse", "HEAD")
    c7_ts = "2026-03-15T00:00:00Z"
    c7_entries = [
        {"type": "add", "lineRange": {"from": 1, "to": 3}, "genRatio": 80, "genMethod": "vibeCoding",
         "file": "squashed.py", "blame_rev_id": revs["C7"], "blame_file": "squashed.py", "blame_line": 1, "blame_ts": c7_ts},
    ]
    (gencode_dir / f"{revs['C7']}.json").write_text(
        json.dumps(_make_gendesc_json_v2604(revs["C7"], c7_ts, repo_url, branch, c7_entries), indent=2))

    # C8: cherry-pick — apply a commit to another branch effect (new file)
    (repo_dir / "cherry.py").write_text("cherry-picked content\n")
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", "C8: cherry-pick feat commit to main", "--date", "2026-03-20T00:00:00Z")
    revs["C8"] = _git(repo_dir, "rev-parse", "HEAD")
    c8_ts = "2026-03-20T00:00:00Z"
    c8_entries = [
        {"type": "add", "lineLocation": 1, "genRatio": 100, "genMethod": "codeCompletion",
         "file": "cherry.py", "blame_rev_id": revs["C8"], "blame_file": "cherry.py", "blame_line": 1, "blame_ts": c8_ts},
    ]
    (gencode_dir / f"{revs['C8']}.json").write_text(
        json.dumps(_make_gendesc_json_v2604(revs["C8"], c8_ts, repo_url, branch, c8_entries), indent=2))

    # C9: revert C4's line change — restore original AI line 5
    main_lines = (repo_dir / "main.py").read_text().split("\n")
    main_lines[4] = "line 5"
    (repo_dir / "main.py").write_text("\n".join(main_lines))
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", "C9: revert human edit, restore AI line 5", "--date", "2026-03-25T00:00:00Z")
    revs["C9"] = _git(repo_dir, "rev-parse", "HEAD")
    c9_ts = "2026-03-25T00:00:00Z"
    c9_entries = [
        {"type": "delete", "file": "main.py", "blame_rev_id": revs["C4"], "blame_file": "main.py", "blame_line": 5},
        {"type": "add", "lineLocation": 5, "genRatio": 100, "genMethod": "vibeCoding",
         "file": "main.py", "blame_rev_id": revs["C9"], "blame_file": "main.py", "blame_line": 5, "blame_ts": c9_ts},
    ]
    (gencode_dir / f"{revs['C9']}.json").write_text(
        json.dumps(_make_gendesc_json_v2604(revs["C9"], c9_ts, repo_url, branch, c9_entries), indent=2))

    # C10: file copy — helpers.py → helpers_v2.py
    shutil.copy(repo_dir / "helpers.py", repo_dir / "helpers_v2.py")
    _git(repo_dir, "add", "helpers_v2.py")
    _git(repo_dir, "commit", "-m", "C10: copy helpers.py to helpers_v2.py", "--date", "2026-04-01T00:00:00Z")
    revs["C10"] = _git(repo_dir, "rev-parse", "HEAD")
    c10_ts = "2026-04-01T00:00:00Z"
    c10_entries = [
        {"type": "add", "lineLocation": 1, "genRatio": 0, "genMethod": "Manual",
         "file": "helpers_v2.py", "blame_rev_id": revs["C10"], "blame_file": "helpers_v2.py", "blame_line": 1, "blame_ts": c10_ts},
    ]
    (gencode_dir / f"{revs['C10']}.json").write_text(
        json.dumps(_make_gendesc_json_v2604(revs["C10"], c10_ts, repo_url, branch, c10_entries), indent=2))

    # C11: whitespace-only change — indent line 3 of main.py
    lines = (repo_dir / "main.py").read_text().split("\n")
    lines[2] = "    " + lines[2]
    (repo_dir / "main.py").write_text("\n".join(lines))
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", "C11: whitespace-only change on main.py line 3", "--date", "2026-04-10T00:00:00Z")
    revs["C11"] = _git(repo_dir, "rev-parse", "HEAD")

    # C12: line-ending normalization — add .gitattributes then force renormalize
    (repo_dir / ".gitattributes").write_text("* text=auto\n")
    _git(repo_dir, "add", ".gitattributes")
    _git(repo_dir, "commit", "-m", "C12a: add .gitattributes for line ending normalization", "--date", "2026-04-15T00:00:00Z")
    revs["C12a"] = _git(repo_dir, "rev-parse", "HEAD")

    _git(repo_dir, "config", "core.autocrlf", "false")
    _git(repo_dir, "add", "--renormalize", ".")
    result = subprocess.run(
        ["git", "diff", "--cached", "--stat"], cwd=str(repo_dir),
        capture_output=True, text=True,
    )
    if result.stdout.strip():
        _git(repo_dir, "commit", "-m", "C12: normalize line endings per .gitattributes", "--date", "2026-04-15T01:00:00Z")
        revs["C12"] = _git(repo_dir, "rev-parse", "HEAD")
    else:
        revs["C12"] = revs["C12a"]

    for jf in sorted(gencode_dir.glob("*.json")):
        data = json.loads(jf.read_text())
        v2603_detail = []
        for df in data.get("DETAIL", []):
            code_entries = []
            for e in df.get("codeLines", []):
                if e.get("changeType") == "add":
                    entry = {"genRatio": e["genRatio"], "genMethod": e["genMethod"]}
                    if "lineLocation" in e:
                        entry["lineLocation"] = e["lineLocation"]
                    if "lineRange" in e:
                        entry["lineRange"] = e["lineRange"]
                    code_entries.append(entry)
            if code_entries:
                v2603_detail.append({"fileName": df["fileName"], "codeLines": code_entries})
        if v2603_detail:
            repo = data.get("REPOSITORY", {})
            (gencode_v2603_dir / jf.name).write_text(json.dumps({
                "protocolName": "generatedTextDesc",
                "protocolVersion": "26.03",
                "codeAgent": "FixtureGen",
                "SUMMARY": {"totalCodeLines": 0, "fullGeneratedCodeLines": 0, "partialGeneratedCodeLines": 0,
                             "totalDocLines": 0, "fullGeneratedDocLines": 0, "partialGeneratedDocLines": 0},
                "DETAIL": v2603_detail,
                "REPOSITORY": {"vcsType": repo.get("vcsType", "git"), "repoURL": repo.get("repoURL", ""),
                               "repoBranch": repo.get("repoBranch", ""), "revisionId": repo.get("revisionId", "")},
            }, indent=2))

    return {
        "repo_dir": repo_dir,
        "gencode_dir": gencode_dir,
        "gencode_v2603_dir": gencode_v2603_dir,
        "repo_url": repo_url,
        "branch": branch,
        "revs": revs,
    }
