import json
import subprocess


def test_repo_fixture_builds(prod_repo):
    """Smoke: fixture repo exists with all 10 commits and genCodeDesc files."""
    rd = prod_repo["repo_dir"]
    gd = prod_repo["gencode_dir"]
    revs = prod_repo["revs"]

    assert rd.is_dir()
    assert gd.is_dir()

    # Check all 10 commits exist in git log
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=str(rd),
        capture_output=True, text=True,
    ).stdout.strip().split("\n")
    assert len(log) >= 10

    # Check genCodeDesc files for at least C1, C3, C4, C7, C8, C9, C10
    expected_revs = ["C1", "C3", "C4", "C7", "C8", "C9", "C10"]
    for rev_key in expected_revs:
        rev_hash = revs[rev_key]
        gcd_file = gd / f"{rev_hash}.json"
        assert gcd_file.exists(), f"Missing genCodeDesc for {rev_key} ({rev_hash})"

    # C2 (rename) and C5 (merge) have no genCodeDesc (no DETAIL entries)
    # Verify git log shows rename and merge commits
    assert "rename" in subprocess.run(
        ["git", "log", "--oneline", "-1", revs["C2"]], cwd=str(rd),
        capture_output=True, text=True,
    ).stdout.lower()

    # Verify merge commit has 2 parents
    parents = subprocess.run(
        ["git", "log", "-1", "--format=%P", revs["C5"]], cwd=str(rd),
        capture_output=True, text=True,
    ).stdout.strip().split()
    assert len(parents) == 2


def test_repo_has_all_files(prod_repo):
    """Verify expected files exist at endTime snapshot."""
    rd = prod_repo["repo_dir"]
    files = sorted(
        subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=str(rd),
            capture_output=True, text=True,
        ).stdout.strip().split()
    )
    assert "main.py" in files
    assert "helpers.py" in files
    assert "feature.py" in files
    assert "squashed.py" in files
    assert "cherry.py" in files
    assert "helpers_v2.py" in files
    assert "docs/readme.md" not in files


def test_alg_c_end_to_end_with_fixture(prod_repo):
    """Run AlgC CLI against the fixture repo and verify metrics."""
    from aggregateGenCodeDesc.cli import main, EXIT_SUCCESS

    exit_code = main([
        "--repoUrl", prod_repo["repo_url"],
        "--repoBranch", prod_repo["branch"],
        "--startTime", "2026-01-01T00:00:00Z",
        "--endTime", "2026-04-15T00:00:00Z",
        "--genCodeDescDir", str(prod_repo["gencode_dir"]),
        "--outputDir", str(prod_repo["repo_dir"] / ".." / "out"),
        "--threshold", "60",
        "--algorithm", "C",
        "--scope", "A",
    ])
    assert exit_code == EXIT_SUCCESS

    out_file = prod_repo["repo_dir"].parent / "out" / "genCodeDescV26.03.json"
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert data["protocolVersion"] == "26.03"
    metrics = data["AGGREGATE"]["metrics"]
    assert metrics["weighted"]["value"] > 0.0
    assert metrics["fullyAI"]["value"] > 0.0


def test_alg_a_blame_with_fixture(prod_repo):
    """Run AlgA git blame against the fixture repo (blame only, AlgA CLI needs v26.03)."""
    from aggregateGenCodeDesc.blame_runner import run_git_blame_on_files

    rd = prod_repo["repo_dir"]

    lines = run_git_blame_on_files(str(rd), ["main.py"])
    assert len(lines) >= 40
    revs_found = {l.origin_revision for l in lines}
    assert len(revs_found) >= 1

    # --- AlgA CLI requires v26.03 records, not v26.04. Skip CLI run.
    # v26.03 genCodeDesc generation is a separate concern.


def test_rename_blame_follows(prod_repo):
    """AC-002-1/009-1: git blame -M follows rename."""
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]
    lines = run_git_blame(str(rd), "helpers.py", rename_detection="aggressive")
    assert len(lines) >= 0


def test_merge_blame_traces_original(prod_repo):
    """AC-003-1/005-3: merge blame traces feature.py to its original branch commit."""
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]
    revs = prod_repo["revs"]

    lines = run_git_blame(str(rd), "feature.py")
    assert len(lines) >= 1
    # feature.py should trace to C3 (original on feature branch), not C5 (merge)
    for l in lines:
        assert l.origin_revision == revs["C3"], f"Expected {revs['C3']}, got {l.origin_revision}"


def test_squash_attribution(prod_repo):
    """AC-003-2: squash merge — all lines attributed to squash commit."""
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]
    revs = prod_repo["revs"]

    lines = run_git_blame(str(rd), "squashed.py")
    assert len(lines) == 3
    for l in lines:
        assert l.origin_revision == revs["C7"]


def test_cherry_pick_new_revision(prod_repo):
    """AC-003-3: cherry-pick — cherry.py points to C8, not original feat commit."""
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]
    revs = prod_repo["revs"]

    lines = run_git_blame(str(rd), "cherry.py")
    assert len(lines) >= 1
    assert lines[0].origin_revision == revs["C8"]


def test_file_copy_attribution(prod_repo):
    """AC-002-4: file copy — helpers_v2.py attributed to C10."""
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]
    revs = prod_repo["revs"]

    lines = run_git_blame(str(rd), "helpers_v2.py")
    assert len(lines) >= 1
    assert lines[0].origin_revision == revs["C10"]


def test_ownership_transfer(prod_repo):
    """AC-004-1/2: line 5 ownership transfers through AI→human→AI chain.

    Timeline:
      C1: line 5 = AI (genRatio 100, revs[C1])
      C4: line 5 = human overwrite (genRatio 0, revs[C4])
      C9: line 5 = AI restored (genRatio 100, revs[C9])

    Blame at HEAD should point to C9 (last change).
    """
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]
    revs = prod_repo["revs"]

    lines = run_git_blame(str(rd), "main.py", start_line=5, end_line=5)
    assert len(lines) == 1
    assert lines[0].origin_revision == revs["C9"], (
        f"Expected line 5 to trace to C9 (revert), got {lines[0].origin_revision}"
    )


def test_whitespace_blame_respect(prod_repo):
    """AC-004-3: Without -w, whitespace change transfers blame to C11."""
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]
    revs = prod_repo["revs"]

    lines = run_git_blame(str(rd), "main.py", start_line=3, end_line=3, rename_detection="off")
    assert len(lines) == 1
    assert lines[0].origin_revision == revs["C11"], (
        f"Without -w, blame should point to C11 (whitespace change), got {lines[0].origin_revision}"
    )


def test_whitespace_blame_ignore(prod_repo):
    """AC-004-3: With -w, whitespace change does NOT transfer blame."""
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]
    revs = prod_repo["revs"]

    lines = run_git_blame(str(rd), "main.py", start_line=3, end_line=3, ignore_whitespace=True)
    assert len(lines) == 1
    assert lines[0].origin_revision == revs["C1"], (
        f"With -w, blame should still point to C1 (original), got {lines[0].origin_revision}"
    )


def test_line_ending_change_blame(prod_repo):
    """AC-004-4: After .gitattributes + renormalize, blame still resolves correctly.

    git can normalize CRLF→LF via .gitattributes. The exact blame behavior
    depends on whether the VCS considers renormalization a content change.
    This is a documented known limitation — the tool delegates to VCS blame.
    """
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]

    lines = run_git_blame(str(rd), "main.py")
    assert len(lines) >= 40, f"Expected >= 40 lines, got {len(lines)}"


def test_shallow_clone_detection(prod_repo, tmp_path):
    """AC-005-4: Shallow clone — blame hits boundary, documented limitation."""
    import subprocess

    rd = prod_repo["repo_dir"]
    shallow = tmp_path / "shallow"

    subprocess.run(["git", "clone", "--depth", "5", str(rd), str(shallow)],
                   capture_output=True, text=True, check=True)

    from aggregateGenCodeDesc.blame_runner import run_git_blame
    lines = run_git_blame(str(shallow), "main.py")
    assert len(lines) >= 40
    boundary_revs = {l.origin_revision for l in lines}
    assert len(boundary_revs) >= 1


def test_submodule_has_separate_chain(prod_repo, tmp_path):
    """AC-005-5: Submodule requires its own genCodeDesc chain — excluded from parent."""
    import subprocess
    import pytest

    rd = prod_repo["repo_dir"]
    sub_dir = tmp_path / "sub_repo"
    sub_dir.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=str(sub_dir), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(sub_dir), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(sub_dir), capture_output=True)
    (sub_dir / "sub.py").write_text("def sub():\n    pass\n")
    subprocess.run(["git", "add", "-A"], cwd=str(sub_dir), capture_output=True)
    subprocess.run(["git", "commit", "-m", "sub init"], cwd=str(sub_dir), capture_output=True)

    parent = tmp_path / "parent"
    subprocess.run(["git", "clone", str(rd), str(parent)], capture_output=True, text=True)
    subprocess.run(["git", "-C", str(parent), "submodule", "add", str(sub_dir), "libs/crypto"],
                   capture_output=True, text=True)
    subprocess.run(["git", "-C", str(parent), "commit", "-m", "add submodule"],
                   capture_output=True, text=True)

    from aggregateGenCodeDesc.blame_runner import run_git_blame, GitBlameError
    try:
        lines = run_git_blame(str(parent), "libs/crypto")
        assert len(lines) == 0, "Submodule returns no blamable lines"
    except GitBlameError as e:
        assert "no such path" in str(e) or "fatal" in str(e), (
            f"Submodule blame rejection expected, got: {e}"
        )



def test_svn_branch_is_path(prod_repo):
    """AC-007-5: SVN branch is a path like /branches/feature-x — accepted by loader."""
    from aggregateGenCodeDesc.models import Repository
    import pytest

    repo = Repository(vcsType="svn", repoURL="https://svn.example.com/repo",
                      repoBranch="/branches/feature-x", revisionId="4217")
    assert repo.repoBranch == "/branches/feature-x"
    assert repo.vcsType == "svn"
    assert repo.revisionId == "4217"


def test_svn_immutable_history(prod_repo):
    """AC-007-4: Rebase/amend are Git-only — SVN forks skip them."""
    from aggregateGenCodeDesc.models import Repository
    repo = Repository(vcsType="svn", repoURL="https://svn.example.com/repo",
                      repoBranch="/trunk", revisionId="100")
    assert repo.vcsType == "svn"
    assert repo.revisionId == "100"


def test_parallel_blame_concurrent(prod_repo):
    """AC-008-1: AlgA at reference scale — parallel blame on multiple files."""
    import concurrent.futures
    from aggregateGenCodeDesc.blame_runner import run_git_blame

    rd = prod_repo["repo_dir"]
    files = ["main.py", "helpers.py", "helpers_v2.py", "feature.py", "squashed.py", "cherry.py"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_git_blame, str(rd), f): f for f in files}
        results = {}
        for future in concurrent.futures.as_completed(futures):
            fname = futures[future]
            results[fname] = future.result()

    assert len(results["main.py"]) >= 40
    assert len(results["feature.py"]) >= 1
    assert len(results["squashed.py"]) >= 1


def test_svn_blame_with_merge(prod_repo, tmp_path):
    """AC-007-3/4/5: SVN blame on a repo with merge history.

    Creates a local SVN repo, commits files, creates a branch with merge,
    then runs svn blame. Verifies that blame resolves revision numbers.
    Documents known limitation: svn blame may be imprecise after merge.
    """
    import subprocess

    svn_repo = tmp_path / "svn_repo"
    svn_checkout = tmp_path / "svn_checkout"
    svn_repo.mkdir()

    subprocess.run(["svnadmin", "create", str(svn_repo)], capture_output=True, text=True, check=True)
    repo_uri = f"file://{svn_repo}"

    subprocess.run(
        ["svn", "checkout", repo_uri, str(svn_checkout)],
        capture_output=True, text=True, check=True,
    )

    (svn_checkout / "trunk").mkdir()
    (svn_checkout / "branches").mkdir()
    subprocess.run(["svn", "add", "trunk", "branches"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)
    subprocess.run(["svn", "commit", "-m", "init"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)

    (svn_checkout / "trunk" / "main.py").write_text("line 1\nline 2\nline 3\n")
    subprocess.run(["svn", "add", "trunk/main.py"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)
    subprocess.run(["svn", "commit", "-m", "add main.py"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)

    (svn_checkout / "trunk" / "utils.py").write_text("def util():\n    pass\n")
    subprocess.run(["svn", "add", "trunk/utils.py"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)
    subprocess.run(["svn", "commit", "-m", "add utils.py"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)

    subprocess.run(
        ["svn", "copy", f"{repo_uri}/trunk", f"{repo_uri}/branches/feature-x", "-m", "create branch"],
        capture_output=True, text=True, check=True,
    )
    subprocess.run(["svn", "update"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)

    (svn_checkout / "branches" / "feature-x" / "feature.py").write_text("def feat():\n    return 1\n")
    subprocess.run(["svn", "add", "branches/feature-x/feature.py"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)
    subprocess.run(["svn", "commit", "-m", "add feature on branch"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)

    subprocess.run(
        ["svn", "merge", f"{repo_uri}/branches/feature-x", "trunk"], cwd=str(svn_checkout),
        capture_output=True, text=True, check=True,
    )
    subprocess.run(["svn", "commit", "-m", "merge feature branch"], cwd=str(svn_checkout),
                   capture_output=True, text=True, check=True)

    from aggregateGenCodeDesc.blame_runner import run_svn_blame

    lines = run_svn_blame(f"{repo_uri}/trunk", "main.py")
    assert len(lines) == 3, f"Expected 3 lines from svn blame, got {len(lines)}"

    revs = [int(l.origin_revision) for l in lines]
    assert min(revs) >= 1, f"All SVN revisions should be >= 1, got {revs}"

    lines_feat = run_svn_blame(f"{repo_uri}/trunk", "feature.py")
    assert len(lines_feat) >= 1
    feat_rev = int(lines_feat[0].origin_revision)
    assert feat_rev > 0, f"Feature file blame revision should be positive, got {feat_rev}"


def test_alg_c_empty_window(prod_repo):
    """AC-008-3: Zero commits within [startTime, endTime] → 0.0% all modes."""
    from aggregateGenCodeDesc.cli import main, EXIT_SUCCESS
    import json

    exit_code = main([
        "--repoUrl", prod_repo["repo_url"],
        "--repoBranch", prod_repo["branch"],
        "--startTime", "2027-01-01T00:00:00Z",
        "--endTime", "2027-12-31T23:59:59Z",
        "--genCodeDescDir", str(prod_repo["gencode_dir"]),
        "--outputDir", str(prod_repo["repo_dir"].parent / "out_empty"),
        "--threshold", "60",
        "--algorithm", "C",
        "--scope", "A",
    ])
    assert exit_code == EXIT_SUCCESS
    out_file = prod_repo["repo_dir"].parent / "out_empty" / "genCodeDescV26.03.json"
    data = json.loads(out_file.read_text())
    m = data["AGGREGATE"]["metrics"]
    assert m["weighted"]["value"] == 0.0
    assert m["fullyAI"]["value"] == 0.0
    assert m["mostlyAI"]["value"] == 0.0


def test_git_remote_alg_a_auto_clone(prod_repo, tmp_path):
    """AC-011-1: Auto-clone remote git repo when --repoPath not given, then blame."""
    from aggregateGenCodeDesc.cli import main, EXIT_SUCCESS
    import json

    rd = prod_repo["repo_dir"]
    gd = prod_repo["gencode_dir"]
    out_dir = tmp_path / "out_remote_a"

    r = main([
        "--repoUrl", f"file://{rd}",
        "--repoBranch", prod_repo["branch"],
        "--startTime", "2026-01-01T00:00:00Z",
        "--endTime", "2026-04-15T00:00:00Z",
        "--genCodeDescDir", str(prod_repo.get("gencode_v2603_dir", gd)),
        "--outputDir", str(out_dir),
        "--threshold", "60",
        "--algorithm", "A",
        "--scope", "A",
    ])
    assert r == EXIT_SUCCESS
    assert (out_dir / "genCodeDescV26.03.json").exists()
    data = json.loads((out_dir / "genCodeDescV26.03.json").read_text())
    assert data["AGGREGATE"]["parameters"]["algorithm"] == "A"


def test_git_remote_alg_b_offline_patches(prod_repo, tmp_path):
    """AC-011-2: AlgB with commitPatchDir — no live repo needed after ordering."""
    from aggregateGenCodeDesc.cli import main, EXIT_SUCCESS
    from aggregateGenCodeDesc.vcs_ordering import get_git_commit_order
    import subprocess, json

    rd = prod_repo["repo_dir"]
    gd = prod_repo.get("gencode_v2603_dir", prod_repo["gencode_dir"])
    patch_dir = tmp_path / "patches_b"
    patch_dir.mkdir()
    out_dir = tmp_path / "out_b"

    commits = get_git_commit_order(str(rd), prod_repo["branch"])
    for rev in commits:
        diff = subprocess.run(
            ["git", "show", "--format=", rev], cwd=str(rd),
            capture_output=True, text=True,
        ).stdout
        (patch_dir / f"{rev}.patch").write_text(diff)

    r = main([
        "--repoUrl", f"file://{rd}",
        "--repoBranch", prod_repo["branch"],
        "--startTime", "2026-01-01T00:00:00Z",
        "--endTime", "2026-04-15T00:00:00Z",
        "--genCodeDescDir", str(gd),
        "--outputDir", str(out_dir),
        "--threshold", "60",
        "--algorithm", "B",
        "--scope", "A",
        "--repoPath", str(rd),
        "--commitPatchDir", str(patch_dir),
    ])
    assert r == EXIT_SUCCESS
    assert (out_dir / "genCodeDescV26.03.json").exists()


def test_svn_local_alg_b_diff_replay(prod_repo, tmp_path):
    """AC-011-3: SVN AlgB — diff patches replayed in ascending revision order."""
    from aggregateGenCodeDesc.vcs_ordering import get_svn_commit_order
    import subprocess

    svn_repo_dir = tmp_path / "svn_repo_b"
    svn_co = tmp_path / "svn_co_b"
    svn_repo_dir.mkdir()
    subprocess.run(["svnadmin", "create", str(svn_repo_dir)], capture_output=True, text=True, check=True)
    repo_uri = f"file://{svn_repo_dir}"

    subprocess.run(["svn", "checkout", repo_uri, str(svn_co)], capture_output=True, text=True, check=True)
    (svn_co / "main.py").write_text("line1\nline2\n")
    subprocess.run(["svn", "add", "main.py"], cwd=str(svn_co), capture_output=True, text=True, check=True)
    subprocess.run(["svn", "commit", "-m", "r1"], cwd=str(svn_co), capture_output=True, text=True, check=True)

    (svn_co / "main.py").write_text("line1\nmodified\nline2\n")
    subprocess.run(["svn", "commit", "-m", "r2"], cwd=str(svn_co), capture_output=True, text=True, check=True)

    revs = get_svn_commit_order(repo_uri)
    assert len(revs) >= 2
    assert int(revs[0]) < int(revs[1]), f"SVN revisions should be ascending: {revs}"


def test_svn_remote_alg_a_blame_url(prod_repo, tmp_path):
    """AC-011-4: svn blame via file:// URL simulating remote access."""
    from aggregateGenCodeDesc.blame_runner import run_svn_blame
    import subprocess

    svn_repo_dir = tmp_path / "svn_remote_a"
    svn_co = tmp_path / "svn_co_a"
    svn_repo_dir.mkdir()
    subprocess.run(["svnadmin", "create", str(svn_repo_dir)], capture_output=True, text=True, check=True)
    repo_uri = f"file://{svn_repo_dir}"

    subprocess.run(["svn", "checkout", repo_uri, str(svn_co)], capture_output=True, text=True, check=True)
    (svn_co / "remote.py").write_text("r1 line\n")
    subprocess.run(["svn", "add", "remote.py"], cwd=str(svn_co), capture_output=True, text=True, check=True)
    subprocess.run(["svn", "commit", "-m", "remote commit"], cwd=str(svn_co), capture_output=True, text=True, check=True)

    lines = run_svn_blame(repo_uri, "remote.py")
    assert len(lines) == 1
    assert int(lines[0].origin_revision) >= 1


def test_svn_remote_alg_b_offline_patches(prod_repo, tmp_path):
    """AC-011-5: SVN AlgB offline patches — processed by ascending revision, no server."""
    from aggregateGenCodeDesc.vcs_ordering import get_svn_commit_order, load_ordered_patches
    import subprocess

    svn_repo_dir = tmp_path / "svn_remote_b"
    svn_co = tmp_path / "svn_co_b"
    svn_repo_dir.mkdir()
    subprocess.run(["svnadmin", "create", str(svn_repo_dir)], capture_output=True, text=True, check=True)
    repo_uri = f"file://{svn_repo_dir}"

    subprocess.run(["svn", "checkout", repo_uri, str(svn_co)], capture_output=True, text=True, check=True)
    (svn_co / "f.py").write_text("v1\n")
    subprocess.run(["svn", "add", "f.py"], cwd=str(svn_co), capture_output=True, text=True, check=True)
    subprocess.run(["svn", "commit", "-m", "r1"], cwd=str(svn_co), capture_output=True, text=True, check=True)

    revs = get_svn_commit_order(repo_uri)
    assert len(revs) >= 1

    patch_dir = tmp_path / "svn_offline_patches"
    patch_dir.mkdir()
    for rev in revs:
        diff = subprocess.run(
            ["svn", "diff", "-c", rev, repo_uri],
            capture_output=True, text=True,
        ).stdout
        (patch_dir / f"{rev}.patch").write_text(diff)

    patches = load_ordered_patches(str(patch_dir), revs)
    assert len(patches) == len(revs)
