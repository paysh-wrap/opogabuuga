"""D88: token-based auto-update for the Windows desktop app.

Flow: check GitHub release `desktop-latest` (read-only fine-grained token) → banner → user clicks Install →
download Paytience-Windows.zip to paytience-data/updates/ → verify size + sha256 → extract to staging → write a
small .bat that swaps the app files after Paytience exits, starts the new exe and restores the backup if the new
app does not report healthy. paytience-data is never touched by the swap. The token is never logged or returned.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

REPO = "paysh-wrap/opogabuuga"
TAG = "desktop-latest"
ASSET = "Paytience-Windows.zip"
RELEASE_URL = f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}"
HEALTHY_FLAG = "healthy.flag"
FAILED_FLAG = "update-failed.txt"
EXPECTED_FILE = "expected-commit.txt"  # D97: commit the NEW app must report before it counts as healthy
UNHEALTHY_FLAG = "unhealthy.flag"  # D97: written by a new app that runs the WRONG commit -> the .bat rolls back
_SHA = re.compile(r"commit:\s*([0-9a-f]{7,40})", re.IGNORECASE)


class UpdateError(Exception):
    """Any update failure: shown as a banner + logged; the old version keeps running."""


@dataclass(frozen=True)
class Version:
    commit: str
    built_at: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def load_version(path: str | Path | None = None) -> Version:
    p = Path(path or os.environ.get("PAYTIENCE_VERSION_FILE", "") or "/nonexistent")
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return Version(str(d.get("commit") or "dev"), str(d.get("built_at") or ""))
    except (OSError, ValueError):
        return Version("dev", "")


def release_commit(release: dict[str, Any]) -> str | None:
    m = _SHA.search(str(release.get("body") or ""))
    if m:
        return m.group(1).lower()
    tc = str(release.get("target_commitish") or "")
    return tc.lower() if re.fullmatch(r"[0-9a-f]{40}", tc, re.IGNORECASE) else None


def _ts(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_newer(current: Version, commit: str | None, published: str) -> bool:
    """Commits can't be ordered, so: different commit AND release built after this build. Dev builds never update."""
    if not commit or current.commit in ("", "dev"):
        return False
    a, b = current.commit.lower(), commit.lower()
    if a.startswith(b) or b.startswith(a):
        return False
    built, pub = _ts(current.built_at), _ts(published)
    if built is None or pub is None:
        return True
    return pub > built


def block_reason(open_positions: int, armed_accounts: int, mode: str) -> str | None:
    if open_positions:
        return f"{open_positions} open position(s) — close them before updating"
    if armed_accounts:
        return f"{armed_accounts} account(s) armed — disarm before updating"
    if mode != "OFF":
        return f"Automation is {mode} — switch it OFF before updating"
    return None


def _headers(token: str, accept: str = "application/vnd.github+json") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}


async def check(http: httpx.AsyncClient, token: str | None, current: Version) -> dict[str, Any]:
    if not token:
        return {"available": False, "error": "", "reason": "no_token"}
    try:
        r = await http.get(RELEASE_URL, headers=_headers(token))
    except httpx.HTTPError as e:
        raise UpdateError(f"GitHub unreachable ({type(e).__name__})") from e
    if r.status_code in (401, 403):
        raise UpdateError(f"GitHub token rejected (HTTP {r.status_code})")
    if r.status_code == 404:
        raise UpdateError("Release desktop-latest not found (or token has no access to the repo)")
    if r.status_code != 200:
        raise UpdateError(f"GitHub HTTP {r.status_code}")
    rel = r.json()
    asset = next((a for a in rel.get("assets", []) if a.get("name") == ASSET), None)
    commit = release_commit(rel)
    published = str(rel.get("updated_at") or rel.get("published_at") or "")
    if asset is not None:
        published = str(asset.get("updated_at") or published)
    return {
        "available": asset is not None and is_newer(current, commit, published),
        "commit": commit,
        "published_at": published,
        "asset": {k: asset.get(k) for k in ("url", "size", "digest", "name")} if asset else None,
        "error": "",
    }


def _expected_sha(asset: dict[str, Any]) -> str | None:
    d = str(asset.get("digest") or "")
    return d.split(":", 1)[1].lower() if d.lower().startswith("sha256:") else None


async def download(http: httpx.AsyncClient, token: str, asset: dict[str, Any], dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / ASSET
    h = hashlib.sha256()
    size = 0
    try:
        async with http.stream(
            "GET", str(asset["url"]), headers=_headers(token, "application/octet-stream"), follow_redirects=True
        ) as r:
            if r.status_code != 200:
                raise UpdateError(f"Download failed (HTTP {r.status_code})")
            with out.open("wb") as f:
                async for chunk in r.aiter_bytes():
                    f.write(chunk)
                    h.update(chunk)
                    size += len(chunk)
    except httpx.HTTPError as e:
        out.unlink(missing_ok=True)
        raise UpdateError(f"Download failed ({type(e).__name__})") from e
    except UpdateError:
        out.unlink(missing_ok=True)
        raise
    want = asset.get("size")
    if want is not None and int(want) != size:
        out.unlink(missing_ok=True)
        raise UpdateError(f"Size mismatch: got {size} bytes, expected {want}")
    exp = _expected_sha(asset)
    if exp is not None and h.hexdigest() != exp:
        out.unlink(missing_ok=True)
        raise UpdateError("Checksum mismatch (sha256) — download discarded")
    return out


def extract(zip_path: Path, staging: Path) -> Path:
    """Extract and return the folder holding Paytience.exe + _internal. Rejects unsafe paths."""
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    root = staging.resolve()
    try:
        with zipfile.ZipFile(zip_path) as z:
            for n in z.namelist():
                if not (root / n).resolve().is_relative_to(root):
                    raise UpdateError(f"Unsafe path in update zip: {n}")
            z.extractall(staging)
    except zipfile.BadZipFile as e:
        raise UpdateError("Update zip is corrupt") from e
    for cand in (staging / "Paytience", staging):
        if (cand / "Paytience.exe").is_file() and (cand / "_internal").is_dir():
            return cand
    raise UpdateError("Update zip has no Paytience.exe + _internal")


def commits_match(a: str, b: str) -> bool:
    """Short and full SHAs compare by prefix; an empty or 'dev' commit never matches anything."""
    a, b = a.strip().lower(), b.strip().lower()
    if a in ("", "dev") or b in ("", "dev"):
        return False
    return a.startswith(b) or b.startswith(a)


def updater_script(
    app_dir: Path,
    new_dir: Path,
    backup: Path,
    updates_dir: Path,
    pid: int,
    wait_s: int = 120,
    expected_commit: str = "",
    port: int = 8000,
) -> str:
    """Windows batch file. Swaps only Paytience.exe + _internal; never touches paytience-data."""
    log = updates_dir / "update.log"
    flag = updates_dir / HEALTHY_FLAG
    failed = updates_dir / FAILED_FLAG
    unhealthy = updates_dir / UNHEALTHY_FLAG
    want = re.sub(r"[^0-9a-f]", "", expected_commit.lower())[:7]  # hex only: safe inside the batch file
    # D97: after the app says "healthy", /api/health must ALSO report the new commit (skipped if curl is missing)
    if want:
        verify = [
            ":verify",
            "where curl >nul 2>&1 || goto ok",
            f"curl -s --max-time 3 http://127.0.0.1:{port}/api/health"
            f' | findstr /R /C:"commit.:.{want}" >nul && goto ok',
            f'echo [%date% %time%] /api/health does not report the new commit {want} >> "%LOG%"',
            "goto stopnew",
        ]
        healthy_target = "verify"
    else:
        verify, healthy_target = [], "ok"
    lines = [
        "@echo off",
        "setlocal",
        f'set "LOG={log}"',
        'echo [%date% %time%] update started >> "%LOG%"',
        "set /a w=0",
        ":wait",
        f'tasklist /FI "PID eq {pid}" /NH 2>nul | findstr /R /C:" {pid} " >nul || goto exited',
        "set /a w+=1",
        'if %w% equ 15 echo [%date% %time%] old app still running, force-closing >> "%LOG%"',
        f"if %w% equ 15 taskkill /PID {pid} /T /F >nul 2>&1",
        'if %w% geq 45 (echo [%date% %time%] old app would not close >> "%LOG%" & goto fail)',
        "timeout /t 1 /nobreak >nul",
        "goto wait",
        ":exited",
        'echo [%date% %time%] old app exited >> "%LOG%"',
        f'del "{flag}" 2>nul',
        f'del "{unhealthy}" 2>nul',
        f'mkdir "{backup}" || goto fail',
        f'move "{app_dir}\\Paytience.exe" "{backup}\\" >> "%LOG%" 2>&1 || goto restore',
        f'move "{app_dir}\\_internal" "{backup}\\" >> "%LOG%" 2>&1 || goto restore',
        f'move "{new_dir}\\Paytience.exe" "{app_dir}\\" >> "%LOG%" 2>&1 || goto restore',
        f'move "{new_dir}\\_internal" "{app_dir}\\" >> "%LOG%" 2>&1 || goto restore',
        'echo [%date% %time%] files swapped, starting new app >> "%LOG%"',
        f'start "" "{app_dir}\\Paytience.exe"',
        "set /a n=0",
        ":health",
        f'if exist "{unhealthy}" goto stopnew',
        f'if exist "{flag}" goto {healthy_target}',
        "set /a n+=1",
        f"if %n% geq {wait_s} goto stopnew",
        "timeout /t 1 /nobreak >nul",
        "goto health",
        *verify,
        ":ok",
        'echo [%date% %time%] new app healthy, update done >> "%LOG%"',
        "exit /b 0",
        ":stopnew",
        'echo [%date% %time%] new app did not become healthy, restoring >> "%LOG%"',
        "taskkill /IM Paytience.exe /F >nul 2>&1",
        "timeout /t 2 /nobreak >nul",
        ":restore",
        'echo [%date% %time%] restoring backup >> "%LOG%"',
        f'if exist "{backup}\\Paytience.exe" (del /f "{app_dir}\\Paytience.exe" 2>nul & '
        f'move "{backup}\\Paytience.exe" "{app_dir}\\" >> "%LOG%" 2>&1)',
        f'if exist "{backup}\\_internal" (rmdir /s /q "{app_dir}\\_internal" 2>nul & '
        f'move "{backup}\\_internal" "{app_dir}\\" >> "%LOG%" 2>&1)',
        ":fail",
        f'echo Update failed at %date% %time% - old version restored. See update.log > "{failed}"',
        'echo [%date% %time%] update FAILED, old version kept >> "%LOG%"',
        f'start "" "{app_dir}\\Paytience.exe"',
        "exit /b 1",
    ]
    return "\r\n".join(lines) + "\r\n"


def on_healthy_start(updates_dir: Path, running_commit: str | None = None) -> str | None:
    """Called by the new app once ITS OWN /api/health answers: confirm to the .bat, drop backups, report a failure.

    D97: after an install the .bat left `expected-commit.txt`; the app only confirms when the commit it is actually
    running matches. A mismatch (old UI/server still around, wrong files) writes `unhealthy.flag` instead, so the .bat
    restores the backup and sets the failed flag.
    """
    if not updates_dir.is_dir():
        return None
    exp_file = updates_dir / EXPECTED_FILE
    if exp_file.exists() and running_commit is not None:
        expected = exp_file.read_text(encoding="utf-8").strip()
        if not commits_match(running_commit, expected):
            (updates_dir / UNHEALTHY_FLAG).write_text("mismatch", encoding="utf-8")
            return f"Update check failed: this app runs build {running_commit[:7]} but {expected[:7]} was expected"
        exp_file.unlink(missing_ok=True)
    (updates_dir / HEALTHY_FLAG).write_text("ok", encoding="utf-8")
    for old in updates_dir.glob("old-*"):
        shutil.rmtree(old, ignore_errors=True)
    failed = updates_dir / FAILED_FLAG
    return failed.read_text(encoding="utf-8").strip() if failed.exists() else None
