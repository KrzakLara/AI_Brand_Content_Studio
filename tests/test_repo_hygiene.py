"""`.gitignore` and the CI guard: NOTHING under `.claude/` (settings, caches, skills) may be tracked."""
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from .conftest import ROOT



def find_bash() -> str | None:
    """A bash that really runs. On Windows, PATH's bash can be the WSL stub, so prefer Git for Windows' own."""
    git_exe = shutil.which("git")
    candidates = []
    if git_exe:
        root = Path(git_exe).resolve().parents[1]
        candidates += [root / "bin" / "bash.exe", root.parent / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"]
    candidates += [Path(p) for p in (shutil.which("bash"), "/bin/bash", "/usr/bin/bash") if p]
    for c in candidates:
        try:
            r = subprocess.run([str(c), "-c", "echo ok"], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0 and r.stdout.strip() == "ok":
            return str(c)
    return None


BASH = find_bash()
pytestmark = pytest.mark.skipif(shutil.which("git") is None or BASH is None, reason="needs git and a working bash")
WORKFLOW = ROOT / ".github" / "workflows" / "no-claude-files.yml"


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


@pytest.mark.parametrize("path", [".claude/settings.local.json", ".claude/sessions/x.json", ".claude/cache/y",
                                  ".claude/settings.json", ".claude/skills/.gitkeep", ".claude/skills/my-skill/SKILL.md"])
def test_everything_under_claude_is_ignored(path):
    assert git("check-ignore", "-q", path).returncode == 0, path


def test_nothing_under_claude_is_tracked_or_trackable():
    # tracked files + untracked-but-not-ignored files: both must be empty
    assert git("ls-files", "-co", "--exclude-standard", ".claude").stdout.split() == []


def guard_script() -> str:
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return next(s["run"] for s in wf["jobs"]["check"]["steps"] if "run" in s)


def run_guard(repo) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, "-c", guard_script()], cwd=repo, capture_output=True, text=True)


def make_repo(tmp_path):
    git("init", "-q", cwd=tmp_path)
    git("config", "user.email", "t@example.invalid", cwd=tmp_path)
    git("config", "user.name", "t", cwd=tmp_path)
    (tmp_path / ".gitignore").write_text((ROOT / ".gitignore").read_text(encoding="utf-8"))
    (tmp_path / "README.md").write_text("x")
    git("add", "-A", cwd=tmp_path)
    return tmp_path


def test_ci_guard_passes_for_a_clean_repo(tmp_path):
    repo = make_repo(tmp_path)
    r = run_guard(repo)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("path", [".claude/settings.local.json", ".claude/sessions/s.json", ".claude/skills/s/SKILL.md",
                                  ".claude/skills/.gitkeep", ".CLAUDE/settings.local.json"])
def test_ci_guard_fails_for_any_force_added_claude_file_including_skills(tmp_path, path):
    repo = make_repo(tmp_path)
    f = repo / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("{}")
    assert git("add", path, cwd=repo).returncode != 0  # a plain add is refused by .gitignore ...
    if path.startswith(".claude/"):
        assert git("add", "-f", path, cwd=repo).returncode == 0  # ... a forced add gets through git ...
        r = run_guard(repo)
        assert r.returncode == 1 and path in r.stdout, r.stdout + r.stderr  # ... and the CI guard catches it
