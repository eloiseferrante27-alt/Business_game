#!/usr/bin/env python3
"""Local Codex/Kimi dispatcher. Task data lives outside checkouts in Git common dir."""
from __future__ import annotations

import argparse
import ctypes
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import tomllib
import uuid

SOURCE = Path(__file__).resolve().parents[1]
REFERENCES = ("docs/Mon monde v3 - blocs, agents et assets.md",
              "docs/Cahier des charges - configurations et interface.md")

try:
    import fcntl
except ModuleNotFoundError:  # pragma: no cover - Windows-only fallback
    class _WindowsFcntl:
        LOCK_EX = 1
        LOCK_NB = 2

        @staticmethod
        def flock(handle, mode):
            name = os.path.abspath(getattr(handle, "name", str(handle)))
            mutex_name = "gmix-lock-" + re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
            mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
            if not mutex:
                raise OSError("CreateMutexW failed")
            existing = getattr(handle, "_gmix_mutex", None)
            if existing is None:
                handle._gmix_mutex = mutex
            else:
                ctypes.windll.kernel32.CloseHandle(mutex)
                mutex = existing
            wait = ctypes.windll.kernel32.WaitForSingleObject(mutex, 0 if mode & _WindowsFcntl.LOCK_NB else 0xFFFFFFFF)
            if wait == 0x00000102:
                raise BlockingIOError("lock unavailable")
            if wait not in (0x00000000, 0x00000080):
                raise OSError(f"WaitForSingleObject failed: {wait}")

        @staticmethod
        def unlock(handle):
            mutex = getattr(handle, "_gmix_mutex", None)
            if mutex:
                ctypes.windll.kernel32.ReleaseMutex(mutex)
                ctypes.windll.kernel32.CloseHandle(mutex)
                delattr(handle, "_gmix_mutex")

    fcntl = _WindowsFcntl()

if not hasattr(os, "killpg"):
    def _killpg(pid: int, sig: int) -> None:
        if sig == 0 and os.name == "nt":
            handle = ctypes.windll.kernel32.OpenProcess(0x100000, False, pid)
            if not handle:
                raise ProcessLookupError(pid)
            ctypes.windll.kernel32.CloseHandle(handle)
            return
        os.kill(pid, sig)
    os.killpg = _killpg  # type: ignore[attr-defined]


class CoordinationError(Exception):
    pass


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise CoordinationError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def config(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def board(text: str) -> dict[str, dict]:
    result = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 5 and re.fullmatch(r"[A-Z]+-?\d+", cells[0]):
            result[cells[0]] = dict(title=cells[1], depends=cells[2], owner=cells[3], status=cells[4])
    return result


def claim(text: str, task: str, agent: str) -> str:
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if re.match(rf"^\|\s*{re.escape(task)}\s*\|", line):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            cells[3:5] = [agent.capitalize(), "in progress"]
            lines[index] = "| " + " | ".join(cells) + " |\n"
            return "".join(lines)
    raise CoordinationError(f"Tâche inconnue dans AGENTS.md : {task}")


def scope_path(value: str, allowed: list[str]) -> str:
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or ".." in path.parts or path == PurePosixPath(".")
            or any(part in {".git", ".env"} or part.startswith(".env.") for part in path.parts)
            or any(char in value for char in "*?[]\\\n\r")):
        raise CoordinationError(f"Périmètre invalide : {value!r}")
    normalized = path.as_posix() + ("/" if value.endswith("/") else "")
    if not any(inside(normalized, root) for root in allowed):
        raise CoordinationError(f"Périmètre hors du rôle de l’agent : {value}")
    return normalized


def inside(path: str, scope: str) -> bool:
    return path == scope.rstrip("/") or (scope.endswith("/") and path.startswith(scope))


def overlap(left: list[str], right: list[str]) -> bool:
    return any(inside(a, b) or inside(b, a) for a in left for b in right if a != "AGENTS.md" and b != "AGENTS.md")


class Store:
    def __init__(self, repo: Path):
        self.root = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "gmix-orchestration"
        self.root.mkdir(mode=0o700, exist_ok=True)

    @contextmanager
    def locked(self):
        with (self.root / "lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            path = self.root / "tasks.json"
            state = json.loads(path.read_text()) if path.exists() else {}
            try:
                yield state
            finally:
                temporary = path.with_suffix(".tmp")
                temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
                temporary.replace(path)
                if hasattr(fcntl, "unlock"):
                    fcntl.unlock(handle)

    @contextmanager
    def execution(self, task):
        """Inherited by workers: coordinator death must not release their reservation."""
        with (self.root / f"execution-{task}.lock").open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, OSError) as error:
                raise CoordinationError("Ancienne exécution encore active ; aucun second agent lancé") from error
            try:
                yield handle.fileno()
            finally:
                if hasattr(fcntl, "unlock"):
                    fcntl.unlock(handle)


def executable(cfg: dict, agent: str) -> str:
    command = cfg["agents"][agent]["command"]
    expanded = os.path.expanduser(command)
    if os.path.isabs(expanded) and os.path.exists(expanded) and os.access(expanded, os.X_OK):
        return expanded
    found = shutil.which(expanded)
    # IDE/background processes do not always inherit the interactive shell PATH.
    if not found and agent == "kimi" and command == "kimi":
        installed = Path.home() / ".kimi-code/bin/kimi"
        if installed.is_file() and os.access(installed, os.X_OK):
            found = str(installed)
    if not found:
        raise CoordinationError(f"CLI introuvable : {command}")
    return found


def command(cfg: dict, agent: str, worktree: Path, output: Path, prompt: str, *, readonly=False, probe=False) -> list[str]:
    profile = cfg["agents"][agent]
    model = ["--model", profile["model"]] if profile.get("model") else []
    if agent == "codex":
        return [executable(cfg, agent), "-a", "never", "exec", *model,
                "--sandbox", "read-only" if readonly or probe else "workspace-write",
                "--ephemeral", "--color", "never", "--cd", str(worktree),
                "--output-last-message", str(output), "-"]
    agent_file = SOURCE / (".agents/agents/gmix-probe.md" if probe else profile["profile"])
    return [executable(cfg, agent), *model, "--agent-file", str(agent_file),
            "--output-format", "text", "--prompt", prompt]


def _terminate_process_group(pid: int, signum: int) -> None:
    if hasattr(os, "killpg"):
        os.killpg(pid, signum)
    else:
        try:
            os.kill(pid, signum)
        except OSError:
            pass


def _normalize_argv(argv: list[str]) -> list[str]:
    if os.name != "nt" or not argv:
        return argv
    target = argv[0]
    if not os.path.exists(target) or not os.path.isfile(target):
        return argv
    try:
        with open(target, "rb") as handle:
            header = handle.read(64)
    except OSError:
        return argv
    if not header.startswith(b"#!"):
        return argv
    if sys.executable:
        return [sys.executable, target, *argv[1:]]
    shell = shutil.which("bash") or shutil.which("sh")
    if shell:
        return [shell, target, *argv[1:]]
    return argv


def process(argv: list[str], cwd: Path, folder: Path, timeout: int, prompt: str | None = None, *, execution_fd=None, run_id=None) -> int:
    argv = _normalize_argv(argv)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    process_kwargs = dict(
        cwd=cwd,
        stdin=subprocess.PIPE if prompt else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    if execution_fd is not None and os.name != "nt":
        try:
            process_kwargs["pass_fds"] = (execution_fd,)
        except TypeError:
            pass
    with (folder / "stdout.log").open("w") as stdout, (folder / "stderr.log").open("w") as stderr:
        process_kwargs["stdout"] = stdout
        process_kwargs["stderr"] = stderr
        child = subprocess.Popen(argv, **process_kwargs)
        # Durable process-group evidence; the inherited lock covers the spawn/write gap.
        (folder / "process.json").write_text(json.dumps(dict(pgid=child.pid, run_id=run_id)) + "\n")
        try:
            child.communicate(input=prompt, timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            _terminate_process_group(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _terminate_process_group(child.pid, signal.SIGKILL)
                child.wait()
            raise CoordinationError(f"Exécution interrompue ou délai dépassé ; logs : {folder}")
    return child.returncode


def changes(worktree: Path, base: str) -> list[str]:
    paths = set(git(worktree, "diff", "--no-renames", "--name-only", "-z", base).split("\0"))
    paths.update(git(worktree, "ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    return sorted(path for path in paths if path)


def snapshot(worktree: Path, base: str, *, bind_head=True) -> str:
    digest = hashlib.sha256(git(worktree, "rev-parse", "HEAD").encode() if bind_head else b"")
    for name in changes(worktree, base):
        path = worktree / name
        digest.update(name.encode())
        digest.update(str(path.lstat().st_mode if path.exists() or path.is_symlink() else 0).encode())
        digest.update(b"SYMLINK" + os.readlink(path).encode() if path.is_symlink()
                      else path.read_bytes() if path.is_file() else b"DELETED")
    return digest.hexdigest()


def prepare(args, repo: Path, cfg: dict, store: Store):
    task = args.task
    if not re.fullmatch(r"[A-Z]+-?\d+", task):
        raise CoordinationError("Identifiant de tâche invalide")
    base = cfg["base_branch"]
    git(repo, "rev-parse", "--verify", base)
    try:
        instructions = git(repo, "show", f"{base}:AGENTS.md") + "\n"
    except CoordinationError as error:
        raise CoordinationError(f"AGENTS.md absent de {base} ; intégrer les instructions avant préparation") from error
    tasks = board(instructions)
    if task not in tasks:
        raise CoordinationError(f"Tâche absente d’AGENTS.md : {task}")
    if tasks[task]["status"] != "todo":
        raise CoordinationError(f"{task} est déjà {tasks[task]['status']} ; ne pas reprendre un autre agent")
    # Dependencies must be explicit: the board uses grouped/ranged expressions.
    dependency_text = tasks[task]["depends"]
    listed = re.findall(r"(?<![A-Z0-9-])[A-Z]+-?\d+(?![A-Z0-9-])", dependency_text)
    remaining = re.sub(r"(?<![A-Z0-9-])[A-Z]+-?\d+(?![A-Z0-9-])", "", dependency_text)
    if remaining.strip(" ,;—\t"):
        raise CoordinationError("Dépendances non explicites : détailler les identifiants dans AGENTS.md")
    if any(char in tasks[task]["depends"] for char in ("–", "+")):
        raise CoordinationError("Dépendances groupées : détailler la ligne de tâche dans AGENTS.md avant lancement")
    pending = [dep for dep in listed if tasks.get(dep, {}).get("status") != "done"]
    if pending:
        raise CoordinationError("Dépendances non terminées : " + ", ".join(pending))
    profile = cfg["agents"][args.agent]
    scopes = [scope_path(value, profile["allowed_roots"]) for value in args.scope]
    brief = Path(args.brief).resolve().read_text(encoding="utf-8")
    for reference in REFERENCES:
        try:
            git(repo, "cat-file", "-e", f"{base}:{reference}")
        except CoordinationError as error:
            raise CoordinationError(f"Référence absente de {base} : {reference}. Intégrer les documents avant préparation.") from error
    root = (repo / cfg["worktree_directory"]).resolve()
    worktree = root / f"{args.agent}-{task}"
    with store.locked() as state:
        existing = state.get(task)
        if existing and existing["status"] != "prepare_failed":
            raise CoordinationError("Tâche déjà enregistrée")
        if existing and (existing["agent"] != args.agent or existing["scope"] != scopes
                         or existing["worktree"] != str(worktree)):
            raise CoordinationError("Préparation interrompue : réutiliser le même agent et périmètre")
        for other, record in state.items():
            if other != task and record["status"] != "done" and overlap(scopes, record["scope"]):
                raise CoordinationError(f"Périmètre réservé par {other}")
        root.mkdir(parents=True, exist_ok=True)
        branch = f"{args.agent}/{task}-work"
        if not existing and git(repo, "branch", "--list", branch):
            raise CoordinationError("Branche déjà existante ; consulter status au lieu de l’écraser")
        state[task] = dict(existing or {}, agent=args.agent, scope=scopes, brief=brief, branch=branch,
                           worktree=str(worktree), base=base, status="prepare_failed")
        if not existing or not worktree.exists():
            if existing and git(repo, "branch", "--list", branch):
                git(repo, "worktree", "add", str(worktree), branch)
            else:
                git(repo, "worktree", "add", "-b", branch, str(worktree), base)
        if Path(git(worktree, "rev-parse", "--path-format=absolute", "--git-common-dir")) != store.root.parent:
            raise CoordinationError("Ce chemin appartient à un autre dépôt ; aucune récupération automatique")
        if git(worktree, "branch", "--show-current") != branch:
            raise CoordinationError("Préparation interrompue sur une branche inattendue ; récupération manuelle requise")
        if any(path != "AGENTS.md" for path in changes(worktree, base)):
            raise CoordinationError("Préparation interrompue avec modifications métier ; les conserver et examiner avant reprise")
        agents = worktree / "AGENTS.md"
        agents.write_text(claim(instructions, task, args.agent), encoding="utf-8")
        git(worktree, "add", "AGENTS.md")
        if git(worktree, "diff", "--cached", "--name-only"):
            git(worktree, "commit", "-m", f"docs: claim {task} for {args.agent}")
        state[task].update(start=git(worktree, "rev-parse", "HEAD"), status="prepared")
    print(json.dumps(state[task], ensure_ascii=False, indent=2))


def run_task(args, repo: Path, cfg: dict, store: Store):
    with store.execution(args.task) as fd:
        return _run_task(args, repo, cfg, store, fd)


def _run_task(args, repo: Path, cfg: dict, store: Store, fd):
    with store.locked() as state:
        if args.task not in state:
            raise CoordinationError("Tâche non préparée")
        record = state[args.task]
        if record["status"] != "prepared":
            raise CoordinationError(f"État {record['status']} ; exécution attendue depuis prepared uniquement")
        running = [r for r in state.values() if r["status"] in {"running", "review_running"}]
        if len(running) >= cfg["max_parallel"] or any(
                ("codex" if r["status"] == "review_running" else r["agent"]) == record["agent"] for r in running):
            raise CoordinationError("Agent déjà occupé ou limite de parallélisme atteinte")
        worktree = Path(record["worktree"])
        if ((git(worktree, "status", "--porcelain") and not record.get("allow_dirty"))
                or git(worktree, "branch", "--show-current") != record["branch"]):
            raise CoordinationError("Worktree modifié avant lancement ou branche inattendue")
        run_id = uuid.uuid4().hex
        folder = store.root / "runs" / args.task / run_id
        record.update(status="running", pid=os.getpid(), run_id=run_id, execution_folder=str(folder))
    folder.mkdir(parents=True, mode=0o700)
    prompt = (f"Tu es {record['agent']}. Rôle : {cfg['agents'][record['agent']]['role']}.\n"
              f"Tâche {args.task}. Travail exclusivement dans {worktree}.\n"
              "La prise en charge est déjà commitée. Lis AGENTS.md et les deux références docs/.\n"
              f"Fichiers autorisés : {', '.join(record['scope'])}, plus AGENTS.md pour ta ligne et ton handoff.\n"
              "N’édite aucun autre worktree, ne change pas de branche, ne délègue pas.\n"
              "Ne lis pas de secrets/.env. Ne pousse pas et ne crée pas de PR pendant ce run ; "
              "le coordinateur effectuera la publication après contrôle. Aucune fusion.\n"
              "Respecte les règles de calcul moteur et les droits serveur. Valeur manquante : signaler.\n"
              "Exécute pytest et les vérifications pertinentes. Mets à jour ta tâche et le handoff.\n"
              "Tu peux committer localement. Termine avec changements, tests, risques et questions.\n\n"
              + record["brief"])
    (folder / "prompt.txt").write_text(prompt)
    outcome = "failed"
    details = {}
    try:
        output = folder / "answer.txt"
        argv = command(cfg, record["agent"], worktree, output, prompt)
        code = process(argv, worktree, folder, cfg["timeout_seconds"], prompt if record["agent"] == "codex" else None, execution_fd=fd, run_id=run_id)
        if record["agent"] == "kimi":
            shutil.copyfile(folder / "stdout.log", output)
        changed = changes(worktree, record["start"])
        outside = [path for path in changed if path != "AGENTS.md" and not any(inside(path, scope) for scope in record["scope"])]
        # Symlinks may redirect a nominally allowed edit outside the task tree.
        symlinks = [path for path in changed if (worktree / path).is_symlink()]
        details = dict(exit_code=code, changed=changed, outside_scope=outside, symlinks=symlinks)
        if code or outside or symlinks:
            raise CoordinationError(f"Agent en échec ou périmètre non respecté : {details}")
        if git(worktree, "branch", "--show-current") != record["branch"]:
            raise CoordinationError("L’agent a changé de branche")
        python = repo / ".venv/bin/python"
        check = [str(python) if token == "{python}" and python.exists() else sys.executable if token == "{python}" else token
                 for token in cfg["checks"]["pytest"]]
        checked = process(check, worktree, folder / "pytest", cfg["timeout_seconds"], execution_fd=fd, run_id=run_id)
        details["pytest_exit_code"] = checked
        if checked:
            raise CoordinationError(f"pytest échoue ; logs : {folder / 'pytest'}")
        task_status = board((worktree / "AGENTS.md").read_text()).get(args.task, {}).get("status")
        if task_status == "blocked":
            outcome = "blocked"
            raise CoordinationError("Agent bloqué sur une question ; consulter son handoff avant de relancer")
        if task_status not in {"done", "review"}:
            raise CoordinationError("Agent n’ayant pas terminé la tâche dans AGENTS.md")
        # Checks can generate files; inspect the final state too.
        final_changed = changes(worktree, record["start"])
        if any(path != "AGENTS.md" and not any(inside(path, s) for s in record["scope"]) for path in final_changed):
            raise CoordinationError("Vérifications ayant modifié un fichier hors périmètre")
        if any((worktree / path).is_symlink() for path in final_changed):
            raise CoordinationError("Vérifications ayant créé un lien symbolique")
        tested_content = snapshot(worktree, record["start"], bind_head=False)
        if final_changed:
            git(worktree, "add", "--", *final_changed)
            if git(worktree, "diff", "--cached", "--name-only"):
                git(worktree, "commit", "-m", f"feat: complete {args.task} with {record['agent']}")
        if (git(worktree, "status", "--porcelain")
                or snapshot(worktree, record["start"], bind_head=False) != tested_content):
            raise CoordinationError("Contenu modifié par un hook de commit : relancer les vérifications")
        details.update(changed=final_changed, fingerprint=snapshot(worktree, record["start"]))
        outcome = "review"
    finally:
        with store.locked() as state:
            state[args.task].update(status=outcome, logs=str(folder), **details)
            state[args.task].pop("pid", None)
        (folder / "handoff.json").write_text(json.dumps(dict(task=args.task, status=outcome, **details), indent=2) + "\n")
        print(f"{args.task}: {outcome} ; compte rendu : {folder}")


def review(args, repo: Path, cfg: dict, store: Store):
    with store.execution(args.task) as fd:
        return _review(args, repo, cfg, store, fd)


def _review(args, repo: Path, cfg: dict, store: Store, fd):
    with store.locked() as state:
        if args.task not in state or state[args.task]["status"] != "review":
            raise CoordinationError("Tâche non prête pour revue")
        record = dict(state[args.task])
        running = [r for r in state.values() if r["status"] in {"running", "review_running"}]
        if len(running) >= cfg["max_parallel"] or any(
                r["status"] == "review_running" or r["agent"] == "codex" for r in running):
            raise CoordinationError("Codex déjà occupé ou limite de parallélisme atteinte")
        if snapshot(Path(record["worktree"]), record["start"]) != record["fingerprint"]:
            raise CoordinationError("Changements depuis les tests : relancer les vérifications avant revue")
        run_id = uuid.uuid4().hex
        folder = Path(record["logs"]) / f"review-{run_id}"
        state[args.task].update(status="review_running", pid=os.getpid(), run_id=run_id, execution_folder=str(folder))
    worktree = Path(record["worktree"])
    prompt = ("Revue uniquement, sans modifier aucun fichier ni déléguer. Lis AGENTS.md et les références.\n"
              f"Évalue le diff depuis {record['start']} et les fichiers non suivis de la tâche {args.task}.\n"
              f"Périmètre : {record['scope']}. Vérifie spec, calculs uniquement moteur, droits, compatibilité et tests.\n"
              "Rapporte les défauts concrets avec fichiers, gravité et correction attendue ; sinon dis aucun défaut trouvé.\n"
              f"Consignes de la tâche : {record['brief']}")
    successful = False
    try:
        folder.mkdir(parents=True, exist_ok=True)
        argv = command(cfg, "codex", worktree, folder / "answer.txt", prompt, readonly=True)
        code = process(argv, worktree, folder, cfg["review"]["timeout_seconds"], prompt, execution_fd=fd, run_id=run_id)
        if code or not (folder / "answer.txt").is_file() or snapshot(worktree, record["start"]) != record["fingerprint"]:
            raise CoordinationError(f"Revue échouée ou fichiers modifiés ; logs : {folder}")
        successful = True
    finally:
        with store.locked() as state:
            state[args.task]["status"] = "review"
            state[args.task].pop("pid", None)
            state[args.task].pop("review_report", None)
            if successful:
                state[args.task]["review_report"] = str(folder / "answer.txt")
    print(f"Revue disponible : {folder / 'answer.txt'} ; lecture humaine requise avant PR/fusion.")


def doctor(args, repo: Path, cfg: dict):
    for agent in cfg["agents"]:
        result = subprocess.run([executable(cfg, agent), "--version"], capture_output=True, text=True, timeout=15)
        print(f"{agent}: {result.stdout.strip()} ; modèle {cfg['agents'][agent]['model'] or 'configuration utilisateur'}")
        if result.returncode:
            raise CoordinationError(f"Version {agent} indisponible")
    for argv in ([executable(cfg, "codex"), "login", "status"], [executable(cfg, "kimi"), "doctor"]):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        print((result.stdout + result.stderr).strip())
        if result.returncode:
            raise CoordinationError("Connexion/configuration CLI à corriger")
    if args.live:
        with tempfile.TemporaryDirectory(prefix="gmix-cli-probe-") as temporary:
            scratch = Path(temporary)
            git(scratch, "init", "-q")
            # No project source or credentials in this scratch repository.
            for agent in cfg["agents"]:
                marker = f"GMIX_{agent.upper()}_OK"
                prompt = f"Sans outil, sans lecture ni écriture de fichier, réponds uniquement : {marker}"
                folder = scratch / f"result-{agent}"
                folder.mkdir()
                output = folder / "answer.txt"
                argv = command(cfg, agent, scratch, output, prompt, probe=True)
                code = process(argv, scratch, folder, 90, prompt if agent == "codex" else None)
                result = output.read_text() if agent == "codex" and output.exists() else (folder / "stdout.log").read_text()
                if code or marker not in result:
                    diagnostic = (folder / "stderr.log").read_text()[-2000:]
                    raise CoordinationError(f"Test réel {agent} échoué (code {code}) : {diagnostic}")
                print(f"{agent}: connexion réelle OK")


def _process_exists(pid: int) -> bool:
    try:
        if hasattr(os, "killpg"):
            os.killpg(pid, 0)
        else:
            os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError):
        return False


def ensure_stopped(record, *, confirm_stopped=False):
    folder = Path(record["execution_folder"]) if record.get("execution_folder") else None
    evidence = list(folder.rglob("process.json")) if folder and folder.exists() else []
    if record["status"] in {"running", "review_running"} and not evidence and not confirm_stopped:
        raise CoordinationError("Exécution interrompue sans preuve d’arrêt : inspecter les processus puis retry --confirm-stopped")
    for path in evidence:
        entry = json.loads(path.read_text())
        if entry.get("run_id") != record.get("run_id"):
            raise CoordinationError("Identifiant d’exécution incohérent ; inspection manuelle requise")
        if not _process_exists(entry["pgid"]):
            continue
        raise CoordinationError(f"Ancien groupe encore actif (PGID {entry['pgid']}) ; arrêter ce groupe avant reprise")


def restore_branch(record):
    tree = Path(record["worktree"])
    if git(tree, "branch", "--show-current") == record["branch"]:
        return
    if f"branch refs/heads/{record['branch']}" in git(tree, "worktree", "list", "--porcelain").splitlines():
        raise CoordinationError("Branche attendue utilisée par un autre worktree ; aucune modification")
    expected = git(tree, "rev-parse", f"refs/heads/{record['branch']}")
    current = git(tree, "rev-parse", "HEAD")
    try:
        git(tree, "merge-base", "--is-ancestor", expected, current)
    except CoordinationError as error:
        raise CoordinationError("Branche divergente : conserver la branche actuelle, intégrer ses commits dans "
                                f"{record['branch']} puis réessayer ; aucun commit écrasé") from error
    # Preserve even detached commits and only fast-forward the task branch atomically.
    recovery = f"recovery/{record['branch']}-{uuid.uuid4().hex[:10]}"
    git(tree, "branch", recovery, current)
    git(tree, "update-ref", f"refs/heads/{record['branch']}", current, expected)
    git(tree, "switch", record["branch"])
    record["recovery_branch"] = recovery


def verify_integrated(repo, tree, record, integrated):
    git(repo, "merge-base", "--is-ancestor", integrated, record["base"])
    patch = subprocess.run(["git", "-C", str(tree), "diff", "--binary", record["start"], "HEAD"],
                           capture_output=True, check=True).stdout
    with tempfile.TemporaryDirectory(prefix="gmix-integration-") as folder:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(folder) / "index"))
        subprocess.run(["git", "-C", str(repo), "read-tree", integrated], env=env, check=True, capture_output=True)
        result = subprocess.run(["git", "-C", str(repo), "apply", "--cached", "--reverse", "--check"],
                                input=patch, env=env, capture_output=True)
        if result.returncode:
            raise CoordinationError("Le commit intégré ne contient pas les changements testés : "
                                    + result.stderr.decode().strip())


def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=SOURCE / "config/orchestration.toml")
    sub = parser.add_subparsers(dest="action", required=True)
    diagnostic = sub.add_parser("doctor")
    diagnostic.add_argument("--live", action="store_true", help="Deux appels modèle minimaux via les connexions existantes")
    sub.add_parser("status")
    prep = sub.add_parser("prepare")
    prep.add_argument("task")
    prep.add_argument("--agent", choices=("codex", "kimi"), required=True)
    prep.add_argument("--brief", required=True, help="Fichier UTF-8 de consignes et critères de validation")
    prep.add_argument("--scope", action="append", required=True, help="Fichier exact ou répertoire terminé par / ; répéter")
    for action in ("run", "review"):
        sub.add_parser(action).add_argument("task")
    closing = sub.add_parser("close")
    closing.add_argument("task")
    closing.add_argument("--integrated-commit", help="Commit intégré vérifiable après squash/rebase")
    retry = sub.add_parser("retry")
    retry.add_argument("task")
    retry.add_argument("--confirm-stopped", action="store_true", help="Confirmer après inspection manuelle l’arrêt d’une exécution sans métadonnées")
    retry.add_argument("--brief", type=Path, help="Consignes complétées avec réponses ou corrections de revue")
    args = parser.parse_args(argv)
    try:
        cfg = config(args.config)
        repo = Path(git(args.repo.resolve(), "rev-parse", "--show-toplevel"))
        if args.action == "doctor":
            doctor(args, repo, cfg)
            return 0
        store = Store(repo)
        if args.action == "prepare":
            prepare(args, repo, cfg, store)
        elif args.action == "run":
            run_task(args, repo, cfg, store)
        elif args.action == "review":
            review(args, repo, cfg, store)
        elif args.action == "status":
            with store.locked() as state:
                print(json.dumps(state, ensure_ascii=False, indent=2))
        elif args.action == "retry":
            with store.execution(args.task), store.locked() as state:
                if args.task not in state:
                    raise CoordinationError("Tâche inconnue")
                record = state[args.task]
                if record["status"] in {"running", "review_running"}:
                    try:
                        os.kill(record["pid"], 0)
                    except (ProcessLookupError, OSError):
                        pass
                    else:
                        raise CoordinationError("Coordinateur encore actif ; attendre sa fin")
                elif record["status"] not in {"failed", "blocked", "review"}:
                    raise CoordinationError("Seule une tâche interrompue, bloquée ou à corriger peut être relancée")
                ensure_stopped(record, confirm_stopped=args.confirm_stopped)
                restore_branch(record)
                record.update(status="prepared", allow_dirty=True)
                if args.brief:
                    record["brief"] = args.brief.read_text(encoding="utf-8")
                for key in ("pid", "fingerprint", "review_report"):
                    record.pop(key, None)
                print(f"{args.task}: reprise préparée, modifications existantes conservées")
        elif args.action == "close":
            with store.locked() as state:
                if args.task not in state:
                    raise CoordinationError("Tâche inconnue")
                record = state[args.task]
                tree = Path(record["worktree"])
                if git(tree, "status", "--porcelain"):
                    raise CoordinationError("Worktree non commité")
                if record["status"] != "review" or not record.get("review_report"):
                    raise CoordinationError("Revue non effectuée")
                if snapshot(tree, record["start"]) != record["fingerprint"]:
                    raise CoordinationError("Tête modifiée depuis les tests/revue")
                if args.integrated_commit:
                    integrated = git(repo, "rev-parse", "--verify", f"{args.integrated_commit}^{{commit}}")
                    verify_integrated(repo, tree, record, integrated)
                    record["integrated_commit"] = integrated
                else:
                    git(repo, "merge-base", "--is-ancestor", git(tree, "rev-parse", "HEAD"), record["base"])
                record["status"] = "done"
                print(f"{args.task}: fusion constatée dans {record['base']}, réservation libérée")
        return 0
    except (CoordinationError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
