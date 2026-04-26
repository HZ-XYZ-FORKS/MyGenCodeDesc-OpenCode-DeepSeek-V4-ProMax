import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class CommitOrderError(Exception):
    pass


def get_git_commit_order(
    repo_path: str,
    repo_branch: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> List[str]:
    cmd = [
        "git", "log", "--topo-order", "--reverse",
        "--pretty=format:%H",
    ]
    if start_time:
        cmd.append(f"--after={start_time}")
    if end_time:
        cmd.append(f"--before={end_time}")
    cmd.append(repo_branch)

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        raise CommitOrderError("Git executable not found. Ensure git is installed and on PATH.")

    if result.returncode != 0:
        raise CommitOrderError(f"git log failed: {result.stderr.strip()}")

    commits = [line.strip() for line in result.stdout.split("\n") if line.strip()]
    return commits


def load_ordered_patches(
    commit_patch_dir: str,
    ordered_commits: List[str],
) -> List[Tuple[str, str]]:
    patch_dir = Path(commit_patch_dir)
    if not patch_dir.is_dir():
        raise CommitOrderError(f"commitPatchDir is not a directory: {commit_patch_dir}")

    seq: List[Tuple[str, str]] = []
    for rev_id in ordered_commits:
        patch_file = patch_dir / f"{rev_id}.patch"
        if not patch_file.is_file():
            raise CommitOrderError(
                f"Missing patch for revision {rev_id}: expected {patch_file}"
            )
        seq.append((patch_file.read_text(), rev_id))
    return seq


def get_ordered_patch_sequence(
    repo_path: str,
    repo_branch: str,
    commit_patch_dir: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    ordered_commits = get_git_commit_order(
        repo_path, repo_branch,
        start_time=start_time,
        end_time=end_time,
    )
    patch_seq = load_ordered_patches(commit_patch_dir, ordered_commits)
    result: List[Tuple[str, str, str]] = []
    for patch_text, rev_id in patch_seq:
        result.append((patch_text, rev_id, ""))
    return result
