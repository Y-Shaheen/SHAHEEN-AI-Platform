"""Git integration API routes for the AstrBot dashboard."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from astrbot.dashboard.responses import ApiError, ok

from .auth import AuthContext, require_scope

router = APIRouter(tags=["Git"])


async def require_system_scope(request: Request) -> AuthContext:
    return await require_scope(request, "system")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_cwd() -> str:
    return os.getcwd()


async def _run_git(*args: str, cwd: str | None = None) -> tuple[int, str, str]:
    """Run a git command asynchronously and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd or _default_cwd(),
    )
    stdout, stderr = await proc.communicate()
    return (
        proc.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


def _validate_hash(commit_hash: str) -> None:
    """Raise ApiError if hash contains non-hex characters."""
    if not commit_hash or not all(c in "0123456789abcdefABCDEF" for c in commit_hash):
        raise ApiError("Invalid commit hash")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class GitCommitRequest(BaseModel):
    message: str
    files: list[str] | None = None  # None → stage all (git add -A)


class GitCheckoutRequest(BaseModel):
    branch: str
    create: bool = False


class GitCloneRequest(BaseModel):
    url: str
    path: str | None = None
    branch: str | None = None


class GitPushRequest(BaseModel):
    remote: str = "origin"
    branch: str | None = None
    force: bool = False


class GitPullRequest(BaseModel):
    remote: str = "origin"
    branch: str | None = None


class GitFetchRequest(BaseModel):
    remote: str = "origin"
    prune: bool = True


class GitBranchRequest(BaseModel):
    name: str
    delete: bool = False
    force: bool = False


class GitMergeRequest(BaseModel):
    branch: str
    no_ff: bool = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/git/status")
async def git_status(
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Return git working-tree status (porcelain v1)."""
    cwd = path or _default_cwd()
    code, out, err = await _run_git("status", "--porcelain=v1", cwd=cwd)
    if code != 0:
        raise ApiError(err or "git status failed")

    files = []
    for line in out.splitlines():
        if len(line) >= 3:
            xy = line[:2]
            filepath = line[3:]
            files.append({"status": xy.strip(), "xy": xy, "path": filepath})

    code2, branch_out, _ = await _run_git("branch", "--show-current", cwd=cwd)
    branch = branch_out.strip() if code2 == 0 else "unknown"

    # Ahead / behind
    code3, tracking_out, _ = await _run_git(
        "rev-list", "--left-right", "--count", "HEAD...@{upstream}", cwd=cwd
    )
    ahead = behind = 0
    if code3 == 0:
        parts = tracking_out.strip().split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])

    return ok(
        {"files": files, "branch": branch, "cwd": cwd, "ahead": ahead, "behind": behind}
    )


@router.get("/git/log")
async def git_log(
    path: str | None = Query(default=None),
    limit: int = Query(default=30, le=500),
    branch: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Return commit log."""
    cwd = path or _default_cwd()
    fmt = "%H\x1f%h\x1f%an\x1f%ae\x1f%ai\x1f%s"
    args = ["log", f"--format={fmt}", f"-{limit}"]
    if branch:
        args.append(branch)
    code, out, err = await _run_git(*args, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git log failed")

    commits = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) >= 6:
            commits.append(
                {
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "author_name": parts[2],
                    "author_email": parts[3],
                    "date": parts[4],
                    "message": parts[5],
                }
            )
    return ok({"commits": commits})


@router.get("/git/diff")
async def git_diff(
    path: str | None = Query(default=None),
    file: str | None = Query(default=None),
    staged: bool = Query(default=False),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Return diff output."""
    cwd = path or _default_cwd()
    args = ["diff"]
    if staged:
        args.append("--cached")
    if file:
        args.extend(["--", file])
    code, out, err = await _run_git(*args, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git diff failed")
    return ok({"diff": out})


@router.get("/git/show")
async def git_show(
    hash: str = Query(...),
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Show a specific commit."""
    _validate_hash(hash)
    cwd = path or _default_cwd()
    code, out, err = await _run_git("show", hash, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git show failed")
    return ok({"output": out})


@router.get("/git/branches")
async def git_branches(
    path: str | None = Query(default=None),
    all: bool = Query(default=False),
    _auth: AuthContext = Depends(require_system_scope),
):
    """List local (and optionally remote) branches."""
    cwd = path or _default_cwd()
    fmt = "%(refname:short)\x1f%(objectname:short)\x1f%(subject)\x1f%(upstream:short)"
    args = ["branch", f"--format={fmt}"]
    if all:
        args.append("-a")

    code, out, err = await _run_git(*args, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git branch failed")

    code2, current_out, _ = await _run_git("branch", "--show-current", cwd=cwd)
    current_branch = current_out.strip() if code2 == 0 else ""

    branches = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        name = parts[0].strip() if parts else ""
        if not name or name.startswith("HEAD"):
            continue
        branches.append(
            {
                "name": name,
                "hash": parts[1] if len(parts) > 1 else "",
                "message": parts[2] if len(parts) > 2 else "",
                "upstream": parts[3] if len(parts) > 3 else "",
                "current": name == current_branch,
            }
        )
    return ok({"branches": branches, "current": current_branch})


@router.post("/git/checkout")
async def git_checkout(
    payload: GitCheckoutRequest,
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Checkout an existing or create a new branch."""
    cwd = path or _default_cwd()
    args = ["checkout"]
    if payload.create:
        args.append("-b")
    args.append(payload.branch)
    code, out, err = await _run_git(*args, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git checkout failed")
    return ok(message=f"Checked out: {payload.branch}")


@router.post("/git/branch")
async def git_branch_op(
    payload: GitBranchRequest,
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Create or delete a branch."""
    cwd = path or _default_cwd()
    if payload.delete:
        flag = "-D" if payload.force else "-d"
        args = ["branch", flag, payload.name]
    else:
        args = ["branch", payload.name]
    code, out, err = await _run_git(*args, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git branch operation failed")
    return ok(message=f"Branch operation completed: {payload.name}")


@router.post("/git/merge")
async def git_merge(
    payload: GitMergeRequest,
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Merge a branch into the current branch."""
    cwd = path or _default_cwd()
    args = ["merge"]
    if payload.no_ff:
        args.append("--no-ff")
    args.append(payload.branch)
    code, out, err = await _run_git(*args, cwd=cwd)
    if code != 0:
        raise ApiError(err + out or "git merge failed")
    return ok({"output": out}, message="Merge completed")


@router.post("/git/commit")
async def git_commit(
    payload: GitCommitRequest,
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Stage files and create a commit."""
    cwd = path or _default_cwd()
    if payload.files:
        for f in payload.files:
            code, _, err = await _run_git("add", "--", f, cwd=cwd)
            if code != 0:
                raise ApiError(f"git add failed for '{f}': {err}")
    else:
        code, _, err = await _run_git("add", "-A", cwd=cwd)
        if code != 0:
            raise ApiError(err or "git add -A failed")

    code, out, err = await _run_git("commit", "-m", payload.message, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git commit failed")
    return ok({"output": out}, message="Committed successfully")


@router.post("/git/pull")
async def git_pull(
    payload: GitPullRequest,
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Pull from a remote."""
    cwd = path or _default_cwd()
    args = ["pull", payload.remote]
    if payload.branch:
        args.append(payload.branch)
    code, out, err = await _run_git(*args, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git pull failed")
    return ok({"output": out + err}, message="Pull completed")


@router.post("/git/push")
async def git_push(
    payload: GitPushRequest,
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Push to a remote."""
    cwd = path or _default_cwd()
    args = ["push", payload.remote]
    if payload.branch:
        args.append(payload.branch)
    if payload.force:
        args.append("--force-with-lease")
    code, out, err = await _run_git(*args, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git push failed")
    return ok({"output": out + err}, message="Push completed")


@router.post("/git/fetch")
async def git_fetch(
    payload: GitFetchRequest,
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Fetch from a remote."""
    cwd = path or _default_cwd()
    args = ["fetch", payload.remote]
    if payload.prune:
        args.append("--prune")
    code, out, err = await _run_git(*args, cwd=cwd)
    if code != 0:
        raise ApiError(err or "git fetch failed")
    return ok({"output": out + err}, message="Fetch completed")


@router.post("/git/clone")
async def git_clone(
    payload: GitCloneRequest,
    _auth: AuthContext = Depends(require_system_scope),
):
    """Clone a repository."""
    args = ["clone"]
    if payload.branch:
        args.extend(["-b", payload.branch])
    args.append(payload.url)
    if payload.path:
        args.append(payload.path)
    code, out, err = await _run_git(*args)
    if code != 0:
        raise ApiError(err or "git clone failed")
    return ok({"output": out + err}, message="Clone completed")


@router.get("/git/remotes")
async def git_remotes(
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """List configured remotes."""
    cwd = path or _default_cwd()
    code, out, _ = await _run_git("remote", "-v", cwd=cwd)
    if code != 0:
        return ok({"remotes": []})

    remotes: dict[str, dict] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            name, url = parts[0], parts[1]
            if name not in remotes:
                remotes[name] = {"name": name, "url": url}
    return ok({"remotes": list(remotes.values())})


@router.get("/git/repos")
async def git_list_repos(
    base_path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """List git repositories found under base_path (one level deep)."""
    search_path = Path(base_path or os.getcwd())
    repos = []

    if (search_path / ".git").exists():
        repos.append({"path": str(search_path), "name": search_path.name})
    else:
        try:
            for item in sorted(search_path.iterdir()):
                if item.is_dir() and not item.name.startswith(".") and (item / ".git").exists():
                    repos.append({"path": str(item), "name": item.name})
        except PermissionError:
            pass

    return ok({"repos": repos, "base_path": str(search_path)})


@router.get("/git/stash")
async def git_stash_list(
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """List stashes."""
    cwd = path or _default_cwd()
    code, out, err = await _run_git("stash", "list", cwd=cwd)
    if code != 0:
        raise ApiError(err or "git stash list failed")
    entries = [line for line in out.splitlines() if line.strip()]
    return ok({"stashes": entries})


@router.post("/git/stash/push")
async def git_stash_push(
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Stash current changes."""
    cwd = path or _default_cwd()
    code, out, err = await _run_git("stash", "push", cwd=cwd)
    if code != 0:
        raise ApiError(err or "git stash push failed")
    return ok({"output": out}, message="Changes stashed")


@router.post("/git/stash/pop")
async def git_stash_pop(
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Pop the latest stash."""
    cwd = path or _default_cwd()
    code, out, err = await _run_git("stash", "pop", cwd=cwd)
    if code != 0:
        raise ApiError(err or "git stash pop failed")
    return ok({"output": out}, message="Stash applied")


@router.get("/git/conflicts")
async def git_conflicts(
    path: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_system_scope),
):
    """Detect merge conflicts (files with UU / AA / DD markers)."""
    cwd = path or _default_cwd()
    code, out, err = await _run_git("status", "--porcelain=v1", cwd=cwd)
    if code != 0:
        raise ApiError(err or "git status failed")

    conflict_statuses = {"UU", "AA", "DD", "AU", "UA", "DU", "UD"}
    conflicts = []
    for line in out.splitlines():
        if len(line) >= 3:
            xy = line[:2].strip()
            filepath = line[3:]
            if xy in conflict_statuses:
                conflicts.append({"status": xy, "path": filepath})

    return ok({"conflicts": conflicts, "has_conflicts": len(conflicts) > 0})
