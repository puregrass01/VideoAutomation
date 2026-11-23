"""Creates a clean, portable ZIP archive of the OpticGlass Automation workspace for another PC (DISTRIBUTION.md):
rules and handoff docs (.agents/, AGENTS.md, HANDOFF.md, DISTRIBUTION.md, docs/), session transcripts
(archive/sessions/), portable shared assets (video-automation/assets/), templates, scenarios, the builders, the
thumbnail generator, the patched pyCapCut and requirements.txt.

Left out: build outputs and caches the PC rebuilds (capcut_stage, __pycache__, debug frames),
backups, Drive/agy login tokens, and (light release) the raw .MOV footage and scene clips, which the
pipeline re-downloads from Drive on the first run. API keys and OAuth tokens in text files are masked in the zip.

Usage:
  py create_portable_release.py            # light release (no raw .MOV / scene clips, ~1.3 GB)
  py create_portable_release.py --with-raw # full release including the raw .MOV footage and clips
"""

from __future__ import annotations

import pathlib
import re
import shutil
import sys
import time
import zipfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent
INCLUDE_ROOTS = [
    ".agents", "GEMINI.md", "AGENTS.md", "HANDOFF.md", "DISTRIBUTION.md", "requirements.txt", "docs",
    "setup.bat", "opticglass_gui.exe", "opticglass_gui_launcher.cs", "opticglass_gui.py",
    "run_all_pipeline.bat", "run_opticglass.bat", "create_portable_release.py",
    "archive", "pyCapCut", "옵틱글래스_유튜브_썸네일", "video-automation", "구글드라이브다운파일",
]
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "capcut_stage", "agy_sessions", "tmp_plate",
             "build", "pycapcut.egg-info"}
SKIP_FILES = {"token.json", "credentials.json", ".env"}  # per-account logins never ship (DISTRIBUTION.md 4)
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".py", ".ps1", ".bat", ".cmd", ".yaml", ".yml", ".log", ".csv"}
# Google API keys, OAuth access tokens, GitHub/Anthropic/OpenAI/Slack tokens that past sessions pasted into transcripts
SECRET_RE = re.compile(rb"(?<![0-9A-Za-z_\-])(?:AIza[0-9A-Za-z_\-]{35}|ya29\.[0-9A-Za-z_\-]{20,}|ghp_[0-9A-Za-z]{36}"
                       rb"|sk-ant-[0-9A-Za-z_\-]{20,}|sk-(?:proj-)?[0-9A-Za-z]{20,}|xox[bp]-[0-9A-Za-z\-]{10,})")


def refresh_current_session_archive():
    cur_id = "30c31593-569d-4c92-9a6e-8a9a9fbcba92"
    brain_src = pathlib.Path.home() / ".gemini" / "antigravity" / "brain" / cur_id
    brain_dst = REPO_ROOT / "archive" / "sessions" / "antigravity_brain" / cur_id
    if brain_src.exists():
        (brain_dst / ".system_generated" / "logs").mkdir(parents=True, exist_ok=True)
        for fname in ("transcript.jsonl", "transcript_full.jsonl"):
            s = brain_src / ".system_generated" / "logs" / fname
            if s.exists():
                shutil.copy2(s, brain_dst / ".system_generated" / "logs" / fname)


def shipped(rel: pathlib.Path, with_raw: bool) -> bool:
    if set(rel.parts) & SKIP_DIRS or any(p.startswith("_backup") for p in rel.parts) or rel.name in SKIP_FILES:
        return False
    if rel.suffix.lower() in {".pyc", ".part"}:
        return False
    posix = rel.as_posix()
    if posix.startswith("구글드라이브다운파일/frames/"):  # check sheets and debug frames: every build redraws them
        return False
    if not with_raw:
        # raw camera footage and the scene clips cut from it: the pipeline re-downloads / re-encodes them
        if rel.suffix.lower() == ".mov" or (posix.startswith("구글드라이브다운파일/media/") and rel.suffix.lower() == ".mp4"):
            return False
        if "/gdrive_raw/_frames/" in posix:  # unmasked stills cut from the clips; thumb_photos cuts them again
            return False
    return True


def build_zip(with_raw: bool = False) -> pathlib.Path:
    refresh_current_session_archive()
    out_name = "OpticGlass_Automation_Full_Portable.zip" if with_raw else "OpticGlass_Automation_Portable_Release.zip"
    out_zip = REPO_ROOT / out_name
    tmp_zip = out_zip.with_suffix(".zip.part")  # the old zip stays until the new one is complete

    count = masked = 0
    with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for item_name in INCLUDE_ROOTS:
            target = REPO_ROOT / item_name
            files = [target] if target.is_file() else sorted(f for f in target.rglob("*") if f.is_file()) if target.exists() else []
            for f in files:
                rel = f.relative_to(REPO_ROOT)
                if not shipped(rel, with_raw):
                    continue
                if f.suffix.lower() in TEXT_SUFFIXES:
                    data = f.read_bytes()
                    clean, n = SECRET_RE.subn(b"<REDACTED>", data)
                    masked += n
                    info = zipfile.ZipInfo.from_file(f, rel.as_posix())  # keeps the file's time, as zf.write does
                    zf.writestr(info, clean, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
                else:
                    zf.write(f, rel)
                count += 1
    for attempt in range(10):  # antivirus / Explorer preview hold a fresh 1 GB file for a few seconds (WinError 5)
        try:
            tmp_zip.replace(out_zip)
            break
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(3)

    size_mb = round(out_zip.stat().st_size / (1024 * 1024), 1)
    print(f"Created {out_zip.name}: {count} files ({size_mb} MB), {masked} secrets masked")
    return out_zip


def _selftest():
    assert not shipped(pathlib.Path("video-automation/_backup_2026-10-28_gui_exe/x.py"), False)
    assert not shipped(pathlib.Path("pyCapCut/build/lib/pycapcut/a.py"), False)
    assert not shipped(pathlib.Path("구글드라이브다운파일/media/santafe/gdrive_raw/IMG_1.MOV"), False)
    assert shipped(pathlib.Path("구글드라이브다운파일/media/santafe/gdrive_raw/IMG_1.MOV"), True)
    assert shipped(pathlib.Path("video-automation/work/build_longform.py"), False)
    assert shipped(pathlib.Path("구글드라이브다운파일/media/santafe/thumb/car_exterior.jpg"), False)
    assert not shipped(pathlib.Path(".agents/skills/gdrive/token.json"), True)
    assert SECRET_RE.sub(b"<REDACTED>", b'key="AIza' + b"A" * 35 + b'"') == b'key="<REDACTED>"'
    assert SECRET_RE.sub(b"X", b"ui/src/lib/task-collection-preferences.ts delegate-task-concurrency") ==         b"ui/src/lib/task-collection-preferences.ts delegate-task-concurrency", "a word with -sk- is no key"
    assert not shipped(pathlib.Path("구글드라이브다운파일/frames/compare_santafe_longform.png"), True)


if __name__ == "__main__":
    _selftest()
    build_zip(with_raw="--with-raw" in sys.argv)
