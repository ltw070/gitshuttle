"""--onto-ref import integration tests."""

from __future__ import annotations

import subprocess

from tests.test_import import _add_commit, _git_env


def test_rewrite_import_full_bundle_onto_ref_grafts_root_history(two_git_repos, tmp_path):
    """self-contained full bundle도 --onto-ref가 있으면 기준 ref 위에 붙인다."""
    from gitshuttle.export_ import run_export
    from gitshuttle.git_ops import get_commits
    from gitshuttle.import_ import run_import

    source, target = two_git_repos
    env = _git_env()

    _add_commit(source, "feature.txt", "feature change", "feat: feature only")
    source_commits = get_commits(source)
    source_count = len(source_commits)
    target_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()
    target_tip = subprocess.run(
        ["git", "rev-parse", target_branch],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()

    bundle_path = run_export(
        repo_path=source,
        commits=source_commits,
        output_dir=tmp_path,
        branch="HEAD",
        filename="full_bundle_onto_ref",
        bundle_scope="full",
    ).bundle

    result = run_import(
        bundle_path,
        target,
        target_branch="migration/full",
        timestamp_mode="original",
        on_conflict="force",
        onto_ref=target_branch,
    )

    target_is_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", target_tip, "migration/full"],
        cwd=target,
        env=env,
    ).returncode == 0
    ahead_count = subprocess.run(
        ["git", "rev-list", "--count", "migration/full", "--not", target_branch],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()

    assert result.imported == source_count
    assert target_is_ancestor
    assert ahead_count == str(source_count)
    assert (target / "feature.txt").read_text(encoding="utf-8") == "feature change"
