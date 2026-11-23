"""Portable path and bundled asset resolver for cross-PC execution.

Allows all OpticGlass video-automation and thumbnail scripts to run identically
on any Windows PC even when original machine-local directories (e.g.
C:\\Users\\bssho\\Downloads\\..., OneDrive, or Windows User Fonts) do not exist,
by falling back to the bundled `video-automation/assets/` directory and the
current user's `%LOCALAPPDATA%\\CapCut` / `%USERPROFILE%` paths.
"""

from __future__ import annotations

import os
import pathlib
import shutil

WORK_DIR = pathlib.Path(__file__).resolve().parent
BASE_DIR = WORK_DIR.parent
REPO_ROOT = BASE_DIR.parent
ASSETS_DIR = BASE_DIR / "assets"
USER_HOME = pathlib.Path.home()
# The pipeline's videos and images (Drive downloads, scene clips, stills, thumbnails, check frames) live outside the
# code tree, in one git-ignored folder at the repo root (or on the user's Desktop if moved there).
_DATA_CANDIDATES = (
    REPO_ROOT / "구글드라이브다운파일",
    USER_HOME / "OneDrive" / "바탕 화면" / "구글드라이브다운파일",
    USER_HOME / "Desktop" / "구글드라이브다운파일",
    USER_HOME / "바탕 화면" / "구글드라이브다운파일",
)
DATA_DIR = next((p for p in _DATA_CANDIDATES if p.exists()), REPO_ROOT / "구글드라이브다운파일")
MEDIA_DIR = DATA_DIR / "media"
OUTPUT_DIR = DATA_DIR / "output"
FRAMES_DIR = DATA_DIR / "frames"
_OLD_DATA = ("video-automation/work/media/", "video-automation/work/output/", "video-automation/work/frames/")

CAPCUT_ROOT = USER_HOME / "AppData" / "Local" / "CapCut"
DRAFT_ROOT = CAPCUT_ROOT / "User Data" / "Projects" / "com.lveditor.draft"
APPS_DIR = CAPCUT_ROOT / "Apps"
WIN_FONTS_DIR = USER_HOME / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts"


def to_fwd(p: str | pathlib.Path) -> str:
    return str(p).replace("\\", "/")


def resolve_asset_path(raw_path: str | pathlib.Path, forward_slash: bool = False) -> str:
    """Resolve an asset/media/font path across machines using bundled fallbacks."""
    if not raw_path:
        return ""
    s = str(raw_path)
    s_norm = s.replace("\\", "/")

    def _fmt(res: pathlib.Path | str) -> str:
        out = str(res)
        return out.replace("\\", "/") if forward_slash else out

    # 1. If path points inside 구글드라이브다운파일 or paperclip-master, rebase onto current DATA_DIR / REPO_ROOT
    data_marker = "구글드라이브다운파일/"
    if data_marker in s_norm:
        rebased_data = DATA_DIR / pathlib.Path(s_norm.split(data_marker, 1)[1])
        if rebased_data.exists():
            return _fmt(rebased_data)

    marker = "paperclip-master/"
    if marker in s_norm:
        rel_after = s_norm.split(marker, 1)[1]
        old = next((o for o in _OLD_DATA if rel_after.startswith(o)), None)  # saved before the data folder moved
        rebased = DATA_DIR / rel_after.split("work/", 1)[1] if old else REPO_ROOT / pathlib.Path(rel_after)
        if rebased.exists():
            return _fmt(rebased)

    # 2. If exact path exists on this machine, use it directly
    direct = pathlib.Path(s)
    if direct.exists():
        return _fmt(direct)

    # 3. If path points to CapCut User Data / Cache under another user's profile
    cc_marker = "AppData/Local/CapCut/"
    if cc_marker in s_norm:
        rel_cc = s_norm.split(cc_marker, 1)[1]
        cc_candidate = CAPCUT_ROOT / pathlib.Path(rel_cc)
        if cc_candidate.exists():
            return _fmt(cc_candidate)

    # 4. Check compatibility cards (조견표) relative path first
    compat_marker = "조견표/"
    if compat_marker in s_norm:
        rel_compat = s_norm.split(compat_marker, 1)[1]
        compat_candidate = ASSETS_DIR / "compat_cards" / pathlib.Path(rel_compat)
        if compat_candidate.exists():
            return _fmt(compat_candidate)

    # 5. Check Windows User Fonts vs bundled assets/fonts
    fname = pathlib.Path(s_norm).name
    if fname:
        if (WIN_FONTS_DIR / fname).exists():
            return _fmt(WIN_FONTS_DIR / fname)
        for sub in ("fonts", "logos", "masks", "outro", "audio"):
            cand = ASSETS_DIR / sub / fname
            if cand.exists():
                return _fmt(cand)
        # Fallback search in compat_cards by filename
        compat_dir = ASSETS_DIR / "compat_cards"
        if compat_dir.exists() and s_norm.lower().endswith((".jpg", ".png")):
            matches = list(compat_dir.rglob(fname))
            if matches:
                return _fmt(matches[0])

    # Return rebased or original if nothing matched
    if data_marker in s_norm:
        return _fmt(DATA_DIR / pathlib.Path(s_norm.split(data_marker, 1)[1]))
    if marker in s_norm:
        rel_after = s_norm.split(marker, 1)[1]
        return _fmt(REPO_ROOT / pathlib.Path(rel_after))
    return _fmt(s)


def resolve_scenario_paths(scenario: dict) -> dict:
    """In-place resolve all file paths inside a loaded scenario dictionary."""
    if "font_path" in scenario and scenario["font_path"]:
        scenario["font_path"] = resolve_asset_path(scenario["font_path"], forward_slash=True)
    if "bgm_path" in scenario and scenario["bgm_path"]:
        scenario["bgm_path"] = resolve_asset_path(scenario["bgm_path"], forward_slash=True)

    for list_key in ("video_Logical", "photo_materials", "video_segments", "photo_segments"):
        for item in scenario.get(list_key, []):
            if isinstance(item, dict) and item.get("path"):
                item["path"] = resolve_asset_path(item["path"], forward_slash=True)

    for seg in scenario.get("audio_segments", []):
        if isinstance(seg, dict) and seg.get("path"):
            seg["path"] = resolve_asset_path(seg["path"], forward_slash=True)

    return scenario


def rewrite_foreign_user_paths(obj):
    """Rewrite foreign user prefixes (wish, 정민석, 회장님 (the shortform template's PC), or bssho on another PC) in draft JSON."""
    home_fwd = to_fwd(USER_HOME).rstrip("/") + "/"
    if isinstance(obj, dict):
        return {k: rewrite_foreign_user_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [rewrite_foreign_user_paths(v) for v in obj]
    if isinstance(obj, str):
        s = obj
        for other in ("C:/Users/wish/", "C:/Users/정민석/", "C:/Users/회장님/", "C:/Users/melly/"):
            s = s.replace(other, home_fwd)
        if "C:/Users/bssho/" in s and home_fwd.lower() != "c:/users/bssho/":
            resolved = resolve_asset_path(s, forward_slash=True)
            if pathlib.Path(resolved).exists():
                return resolved
            s = s.replace("C:/Users/bssho/", home_fwd)
        elif ("paperclip-master/" in s or "구글드라이브다운파일/" in s) and not pathlib.Path(s).exists():
            resolved = resolve_asset_path(s, forward_slash=True)
            if pathlib.Path(resolved).exists():
                return resolved
        return s
    return obj


def find_ffmpeg() -> str:
    """Locate ffmpeg executable across PATH, WinGet packages, or imageio_ffmpeg."""
    which_ff = shutil.which("ffmpeg")
    if which_ff:
        return which_ff
    winget_pkgs = USER_HOME / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_pkgs.exists():
        matches = list(winget_pkgs.rglob("ffmpeg.exe"))
        if matches:
            return str(matches[0])
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return "ffmpeg"


def find_gdrive_cmd() -> pathlib.Path:
    """Locate gdrive.cmd across current user's Antigravity plugin path or PATH."""
    candidates = [
        USER_HOME / ".gemini" / "config" / "plugins" / "gdrive" / "skills" / "gdrive" / "scripts" / "gdrive.cmd",
        REPO_ROOT / ".agents" / "skills" / "gdrive" / "scripts" / "gdrive.cmd",
    ]
    for c in candidates:
        if c.exists():
            return c
    which_gd = shutil.which("gdrive") or shutil.which("gdrive.cmd")
    if which_gd:
        return pathlib.Path(which_gd)
    return candidates[0]
