"""Exercise real Git worktrees and subprocess dispatch without model/network calls."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/orchestrate.py"
spec = importlib.util.spec_from_file_location("orchestrate", MODULE_PATH)
orchestrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orchestrate)


def git(repo, *args):
    return orchestrate.git(repo, *args)


@pytest.fixture
def project(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "contribution_amine")
    git(repo, "config", "user.name", "Orchestration test")
    git(repo, "config", "user.email", "orchestration@example.invalid")
    (repo / "AGENTS.md").write_text(
        "| ID | Task | Depends on | Suggested owner | Status |\n"
        "| T01 | Report | — | Codex | done |\n"
        "| T02 | Config | T01 | Codex | todo |\n"
        "| T03 | Clock | T00 | Codex | todo |\n"
        "| T07 | Tools | — | Kimi | todo |\n"
        "| T12 | Stock | T02–T05 | Codex | todo |\n")
    for name in orchestrate.REFERENCES:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Reference\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "baseline")
    cfg = orchestrate.config(MODULE_PATH.parents[1] / "config/orchestration.toml")
    cfg["worktree_directory"] = str(tmp_path / "worktrees")
    cfg["checks"]["pytest"] = [sys.executable, "-c", "print('test-check-passed')"]
    brief = tmp_path / "brief.txt"
    brief.write_text("Implement only the assigned files; finish the board entry.")
    cli = tmp_path / "fake-agent"
    cli.write_text("#!/usr/bin/env python3\n" + r'''
import os, pathlib, sys, subprocess
prompt = sys.stdin.read() if sys.argv[-1] == '-' else sys.argv[-1]
if '--sandbox' in sys.argv and sys.argv[sys.argv.index('--sandbox')+1] == 'read-only':
    pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text('Review complete')
    sys.exit(0)
if os.environ.get('FAKE_TIMEOUT'):
    import time
    time.sleep(60)
path = pathlib.Path(os.environ.get('FAKE_TARGET', 'backend/app/engine/config.py'))
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text('# worker implementation\n')
board = pathlib.Path('AGENTS.md')
board.write_text(board.read_text().replace('| Codex | in progress |', '| Codex | done |'))
if os.environ.get('FAKE_COMMIT'):
    subprocess.run(['git','add','.'], check=True)
    subprocess.run(['git','commit','-qm','worker implementation'], check=True)
if '--output-last-message' in sys.argv:
    pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text('Worker complete')
print('Worker complete')
''')
    cli.chmod(0o755)
    for agent in cfg["agents"].values():
        agent["command"] = str(cli)
    return repo, cfg, orchestrate.Store(repo), brief


def prepare(project, task="T02", agent="codex", scope=None):
    repo, cfg, store, brief = project
    args = argparse.Namespace(task=task, agent=agent, brief=str(brief),
                              scope=scope or ["backend/app/engine/"])
    orchestrate.prepare(args, repo, cfg, store)
    with store.locked() as records:
        return dict(records[task])


def record(store, task="T02"):
    with store.locked() as state:
        return dict(state[task])


@pytest.mark.parametrize("path", ["../outside", "/tmp/outside", ".env", "backend/.env.local", "backend/*", ".git/config", "."])
def test_scope_rejects_escape_secrets_and_globs(path):
    with pytest.raises(orchestrate.CoordinationError):
        orchestrate.scope_path(path, ["backend/", ".env", ".git/"])


def test_kimi_cannot_claim_engine_files(project):
    with pytest.raises(orchestrate.CoordinationError, match="hors du rôle"):
        prepare(project, "T07", "kimi", ["backend/app/engine/config.py"])


def test_kimi_discovery_works_without_interactive_shell_path(tmp_path, monkeypatch):
    installed = tmp_path / ".kimi-code/bin/kimi"
    installed.parent.mkdir(parents=True)
    installed.write_text("#!/bin/sh\nexit 0\n")
    installed.chmod(0o755)
    monkeypatch.setattr(orchestrate.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(orchestrate.shutil, "which", lambda _: None)
    assert orchestrate.executable({"agents": {"kimi": {"command": "kimi"}}}, "kimi") == str(installed)


def test_prepare_keeps_main_checkout_and_dirty_files(project):
    repo, cfg, store, _ = project
    (repo / "unrelated.txt").write_text("human work")
    item = prepare(project)
    tree = Path(item["worktree"])
    assert git(repo, "branch", "--show-current") == "contribution_amine"
    assert (repo / "unrelated.txt").read_text() == "human work"
    assert "| Codex | todo |" in (repo / "AGENTS.md").read_text()
    assert "| T02 | Config | T01 | Codex | in progress |" in (tree / "AGENTS.md").read_text()
    assert not git(tree, "status", "--porcelain")
    assert git(tree, "log", "-1", "--format=%s") == "docs: claim T02 for codex"


def test_prepare_uses_dependencies_from_base_not_unmerged_checkout(project):
    repo, *_ = project
    current = repo / "AGENTS.md"
    current.write_text(current.read_text().replace("| T03 | Clock | T00 |", "| T03 | Clock | T01 |"))
    with pytest.raises(orchestrate.CoordinationError, match="non terminées"):
        prepare(project, "T03")


@pytest.mark.parametrize("task", ["T03", "T12"])
def test_unresolved_or_grouped_dependencies_do_not_launch(project, task):
    repo, cfg, _, _ = project
    with pytest.raises(orchestrate.CoordinationError, match="[Dd]épendances"):
        prepare(project, task)
    assert not git(repo, "branch", "--list", f"codex/{task}-work")


def test_source_references_must_be_committed_on_base(project):
    repo, *_ = project
    git(repo, "rm", orchestrate.REFERENCES[0])
    git(repo, "commit", "-qm", "missing reference")
    with pytest.raises(orchestrate.CoordinationError):
        prepare(project)
    assert not git(repo, "branch", "--list", "codex/T02-work")


def test_shared_file_reservations_but_separate_agents_allowed(project):
    prepare(project, scope=["backend/tests/"])
    with pytest.raises(orchestrate.CoordinationError, match="réservé"):
        prepare(project, "T07", "kimi", ["backend/tests/test_tablet.py"])
    second = prepare(project, "T07", "kimi", ["backend/app/static/tablet/"])
    assert second["agent"] == "kimi"


def test_run_collects_committed_edits_and_reviewer_uses_readonly(project, monkeypatch):
    repo, cfg, store, _ = project
    prepare(project)
    monkeypatch.setenv("FAKE_COMMIT", "1")
    orchestrate.run_task(argparse.Namespace(task="T02"), repo, cfg, store)
    item = record(store)
    assert item["status"] == "review"
    assert item["pytest_exit_code"] == 0
    assert "backend/app/engine/config.py" in item["changed"]
    assert (Path(item["logs"]) / "handoff.json").exists()
    orchestrate.review(argparse.Namespace(task="T02"), repo, cfg, store)
    assert Path(record(store)["review_report"]).read_text() == "Review complete"


def test_dispatcher_commits_tested_changes_before_review_and_closes_only_after_merge(project, monkeypatch):
    repo, cfg, store, _ = project
    prepare(project)
    orchestrate.run_task(argparse.Namespace(task="T02"), repo, cfg, store)
    item = record(store)
    tree = Path(item["worktree"])
    assert not git(tree, "status", "--porcelain")
    assert git(tree, "log", "-1", "--format=%s") == "feat: complete T02 with codex"
    orchestrate.review(argparse.Namespace(task="T02"), repo, cfg, store)
    monkeypatch.setattr(orchestrate, "config", lambda _: cfg)
    assert orchestrate.main(["--repo", str(repo), "close", "T02"]) == 1
    git(repo, "merge", "--no-ff", item["branch"], "-m", "human integration")
    assert orchestrate.main(["--repo", str(repo), "close", "T02"]) == 0
    assert record(store)["status"] == "done"


def test_out_of_scope_committed_edit_never_reaches_review(project, monkeypatch):
    repo, cfg, store, _ = project
    prepare(project)
    monkeypatch.setenv("FAKE_TARGET", "backend/app/models.py")
    monkeypatch.setenv("FAKE_COMMIT", "1")
    with pytest.raises(orchestrate.CoordinationError, match="périmètre"):
        orchestrate.run_task(argparse.Namespace(task="T02"), repo, cfg, store)
    item = record(store)
    assert item["status"] == "failed"
    assert item["outside_scope"] == ["backend/app/models.py"]
    assert "pid" not in item


def test_failed_checks_and_later_changes_invalidate_readiness(project):
    repo, cfg, store, _ = project
    prepare(project)
    cfg["checks"]["pytest"] = [sys.executable, "-c", "raise SystemExit(7)"]
    with pytest.raises(orchestrate.CoordinationError, match="pytest"):
        orchestrate.run_task(argparse.Namespace(task="T02"), repo, cfg, store)
    assert record(store)["status"] == "failed"
    assert record(store)["pytest_exit_code"] == 7


def test_review_rejects_change_after_checks(project):
    repo, cfg, store, _ = project
    prepare(project)
    orchestrate.run_task(argparse.Namespace(task="T02"), repo, cfg, store)
    item = record(store)
    (Path(item["worktree"]) / "backend/app/engine/config.py").write_text("changed after tests")
    with pytest.raises(orchestrate.CoordinationError, match="Changements"):
        orchestrate.review(argparse.Namespace(task="T02"), repo, cfg, store)


def test_retry_preserves_edits_and_accepts_review_feedback(project, monkeypatch):
    repo, cfg, store, brief = project
    prepare(project)
    orchestrate.run_task(argparse.Namespace(task="T02"), repo, cfg, store)
    item = record(store)
    work = Path(item["worktree"]) / "backend/app/engine/config.py"
    before = work.read_text()
    brief.write_text("Correct the reviewer finding about missing validation.")
    monkeypatch.setattr(orchestrate, "config", lambda _: cfg)
    assert orchestrate.main(["--repo", str(repo), "retry", "T02", "--brief", str(brief)]) == 0
    item = record(store)
    assert item["status"] == "prepared" and item["allow_dirty"]
    assert "missing validation" in item["brief"]
    assert "fingerprint" not in item
    assert work.read_text() == before
    orchestrate.run_task(argparse.Namespace(task="T02"), repo, cfg, store)
    assert record(store)["status"] == "review"


def test_reviewer_respects_codex_concurrency_reservation(project):
    repo, cfg, store, _ = project
    prepare(project)
    orchestrate.run_task(argparse.Namespace(task="T02"), repo, cfg, store)
    with store.locked() as state:
        state["OTHER"] = {"status": "running", "agent": "codex", "scope": ["docs/"]}
    with pytest.raises(orchestrate.CoordinationError, match="occupé"):
        orchestrate.review(argparse.Namespace(task="T02"), repo, cfg, store)
    assert record(store)["status"] == "review"


def test_timeout_marks_task_failed_and_preserves_logs(project, monkeypatch):
    repo, cfg, store, _ = project
    prepare(project)
    monkeypatch.setenv("FAKE_TIMEOUT", "1")
    cfg["timeout_seconds"] = 0.2
    with pytest.raises(orchestrate.CoordinationError, match="délai"):
        orchestrate.run_task(argparse.Namespace(task="T02"), repo, cfg, store)
    item = record(store)
    assert item["status"] == "failed"
    assert "pid" not in item
    assert (Path(item["logs"]) / "handoff.json").exists()


def test_cli_commands_keep_auth_models_and_do_not_disable_sandbox(project):
    repo, cfg, _, _ = project
    codex = orchestrate.command(cfg, "codex", repo, repo / "out", "prompt")
    kimi = orchestrate.command(cfg, "kimi", repo, repo / "out", "prompt")
    assert codex[codex.index("--sandbox") + 1] == "workspace-write"
    assert "--dangerously-bypass-approvals-and-sandbox" not in codex
    assert kimi[kimi.index("--model") + 1] == "kimi-code/k3.1-pro"
    assert "--auto" not in kimi and "--yolo" not in kimi and "--plan" not in kimi
    assert not orchestrate.overlap(["AGENTS.md"], ["AGENTS.md"])


def test_failed_claim_commit_is_recorded_and_prepare_can_resume(project):
    repo, cfg, store, _ = project
    hook = Path(git(repo, 'rev-parse', '--absolute-git-dir')) / 'hooks/pre-commit'
    hook.write_text('#!/bin/sh\nexit 1\n')
    hook.chmod(0o755)
    with pytest.raises(orchestrate.CoordinationError):
        prepare(project)
    failed = record(store)
    assert failed['status'] == 'prepare_failed'
    tree = Path(failed['worktree'])
    assert tree.exists()
    assert git(tree, 'branch', '--show-current') == failed['branch']
    hook.unlink()
    resumed = prepare(project)
    assert resumed['worktree'] == str(tree)
    assert resumed['status'] == 'prepared'
    assert git(tree, 'log', '-1', '--format=%s') == 'docs: claim T02 for codex'


@pytest.mark.parametrize('dependency,status', [('ORCH-00', 'todo'), ('ENV-01', 'done'), ('MISSING-01', None)])
def test_non_t_dependencies_are_enforced(project, dependency, status):
    repo, *_ = project
    board = repo / 'AGENTS.md'
    with board.open('a') as output:
        if status:
            output.write(f'| {dependency} | Dependency | — | Codex | {status} |\n')
        output.write(f'| ORCH-01 | Coordination | {dependency} | Codex | todo |\n')
    git(repo, 'add', 'AGENTS.md')
    git(repo, 'commit', '-qm', 'declare orchestration task')
    if status == 'done':
        assert prepare(project, 'ORCH-01')['status'] == 'prepared'
    else:
        with pytest.raises(orchestrate.CoordinationError, match='non terminées'):
            prepare(project, 'ORCH-01')


def test_retry_restores_unexpected_branch_and_preserves_commits_and_dirty_work(project, monkeypatch):
    repo, cfg, store, _ = project
    item = prepare(project)
    tree = Path(item['worktree'])
    original_process = orchestrate.process

    def branch_changing_agent(*args, **kwargs):
        git(tree, 'switch', '-c', 'detour')
        result = original_process(*args, **kwargs)
        git(tree, 'add', '.')
        git(tree, 'commit', '-qm', 'work committed on unexpected branch')
        return result

    monkeypatch.setattr(orchestrate, 'process', branch_changing_agent)
    with pytest.raises(orchestrate.CoordinationError, match='changé de branche'):
        orchestrate.run_task(argparse.Namespace(task='T02'), repo, cfg, store)
    detached_tip = git(tree, 'rev-parse', 'HEAD')
    dirty = tree / 'backend/app/engine/notes.txt'
    dirty.write_text('Keep these uncommitted notes')
    monkeypatch.setattr(orchestrate, 'process', original_process)
    monkeypatch.setattr(orchestrate, 'config', lambda _: cfg)
    assert orchestrate.main(['--repo', str(repo), 'retry', 'T02']) == 0
    assert git(tree, 'branch', '--show-current') == item['branch']
    assert git(tree, 'rev-parse', 'HEAD') == detached_tip
    assert git(tree, 'rev-parse', 'detour') == detached_tip
    assert git(tree, 'rev-parse', record(store)['recovery_branch']) == detached_tip
    assert dirty.read_text() == 'Keep these uncommitted notes'
    orchestrate.run_task(argparse.Namespace(task='T02'), repo, cfg, store)
    assert record(store)['status'] == 'review'


def test_retry_refuses_divergent_branches_without_losing_either_tip(project, monkeypatch):
    repo, cfg, store, _ = project
    item = prepare(project)
    tree = Path(item['worktree'])
    git(tree, 'commit', '--allow-empty', '-qm', 'expected branch commit')
    expected = git(tree, 'rev-parse', 'HEAD')
    git(tree, 'switch', '-c', 'diverged', item['start'])
    git(tree, 'commit', '--allow-empty', '-qm', 'different work')
    current = git(tree, 'rev-parse', 'HEAD')
    with store.locked() as state:
        state['T02']['status'] = 'failed'
    monkeypatch.setattr(orchestrate, 'config', lambda _: cfg)
    assert orchestrate.main(['--repo', str(repo), 'retry', 'T02']) == 1
    assert record(store)['status'] == 'failed'
    assert git(tree, 'rev-parse', item['branch']) == expected
    assert git(tree, 'rev-parse', 'HEAD') == current


def test_execution_lock_survives_coordinator_crash_and_prevents_second_worker(project, monkeypatch, tmp_path):
    import os
    import signal
    import time

    repo, cfg, store, _ = project
    prepare(project)
    payload = tmp_path / 'configuration.json'
    payload.write_text(json.dumps(cfg))
    script = '''import argparse, importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('worker', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
repo = Path(sys.argv[2])
module.run_task(argparse.Namespace(task='T02'), repo, json.loads(Path(sys.argv[3]).read_text()), module.Store(repo))
'''
    coordinator = subprocess.Popen([sys.executable, '-c', script, str(MODULE_PATH), str(repo), str(payload)],
                                   env=dict(os.environ, FAKE_TIMEOUT='1'), stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
    pgid = None
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            item = record(store)
            metadata = Path(item.get('execution_folder', tmp_path / 'missing')) / 'process.json'
            if metadata.is_file():
                pgid = json.loads(metadata.read_text())['pgid']
                break
            time.sleep(0.02)
        assert pgid is not None
        coordinator.kill()
        coordinator.wait(timeout=5)
        os.killpg(pgid, 0)  # Agent survived the coordinator.
        monkeypatch.setattr(orchestrate, 'config', lambda _: cfg)
        assert orchestrate.main(['--repo', str(repo), 'retry', 'T02']) == 1
        assert record(store)['status'] == 'running'
        # Even a damaged status cannot permit a second run while its worker holds the lock.
        with store.locked() as state:
            state['T02']['status'] = 'prepared'
        with pytest.raises(orchestrate.CoordinationError, match='encore active'):
            orchestrate.run_task(argparse.Namespace(task='T02'), repo, cfg, store)
    finally:
        if coordinator.poll() is None:
            coordinator.kill()
            coordinator.wait(timeout=5)
        if pgid:
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def test_stale_running_without_process_metadata_fails_closed(project, monkeypatch):
    repo, cfg, store, _ = project
    prepare(project)
    with store.locked() as state:
        state['T02'].update(status='running', pid=2**30, run_id='incomplete')
    monkeypatch.setattr(orchestrate, 'config', lambda _: cfg)
    assert orchestrate.main(['--repo', str(repo), 'retry', 'T02']) == 1
    assert record(store)['status'] == 'running'
    assert orchestrate.main(['--repo', str(repo), 'retry', 'T02', '--confirm-stopped']) == 0


@pytest.mark.parametrize('method', ['squash', 'rebase'])
def test_close_with_explicit_integration_proof_supports_squash_and_rebase(project, monkeypatch, method):
    repo, cfg, store, _ = project
    item = prepare(project)
    orchestrate.run_task(argparse.Namespace(task='T02'), repo, cfg, store)
    orchestrate.review(argparse.Namespace(task='T02'), repo, cfg, store)
    task_head = git(Path(item['worktree']), 'rev-parse', 'HEAD')
    baseline = git(repo, 'rev-parse', 'HEAD')
    git(repo, 'commit', '--allow-empty', '-qm', 'unrelated base progress')
    if method == 'squash':
        git(repo, 'merge', '--squash', item['branch'])
        git(repo, 'commit', '-qm', 'human squash integration')
    else:
        git(repo, 'cherry-pick', item['start'], task_head)
    integrated = git(repo, 'rev-parse', 'HEAD')
    monkeypatch.setattr(orchestrate, 'config', lambda _: cfg)
    assert orchestrate.main(['--repo', str(repo), 'close', 'T02']) == 1
    assert orchestrate.main(['--repo', str(repo), 'close', 'T02', '--integrated-commit', baseline]) == 1
    assert record(store)['status'] == 'review'
    assert orchestrate.main(['--repo', str(repo), 'close', 'T02', '--integrated-commit', integrated]) == 0
    assert record(store)['status'] == 'done'
    assert record(store)['integrated_commit'] == integrated
