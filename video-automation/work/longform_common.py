"""Clip and draft helpers for build_longform.py (they used to be copy-pasted into each car's builder)."""
import contextlib
import copy
import functools
import hashlib
import json
import math
import os
import pathlib
import random
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image

from portable_paths import MEDIA_DIR, find_ffmpeg, resolve_asset_path


@functools.lru_cache(maxsize=1)
def _has_nvenc() -> bool:
    """Lazy 1-frame NVENC test encode (only runs when encoding/decoding actually starts, never at import time)."""
    try:
        return subprocess.run(
            [find_ffmpeg(), "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.1",
             "-c:v", "h264_nvenc", "-f", "null", "-"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).returncode == 0
    except OSError:
        return False


_NVENC_ARGS = ("-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "23", "-b:v", "0")
_SW_ARGS = ("-c:v", "libx264", "-preset", "veryfast", "-crf", "20")


def _enc_clip(use_hw: bool = True) -> list[str]:
    return list(_NVENC_ARGS) if (use_hw and _has_nvenc()) else list(_SW_ARGS)


FACE_MASK_PATH = pathlib.Path(resolve_asset_path(MEDIA_DIR / "face_mask_circle.png"))
# imdecode, not imread: cv2.imread returns None for a path with Korean letters (a repo under a Korean folder or user name)
FACE_MASK_RGBA = cv2.imdecode(np.fromfile(str(FACE_MASK_PATH), dtype=np.uint8), cv2.IMREAD_UNCHANGED) if FACE_MASK_PATH.exists() and FACE_MASK_PATH.stat().st_size else None
SCENARIOS_DIR = pathlib.Path(__file__).resolve().parent / "scenarios"
MEDIA_SRC_PREFIX = "@media/"
_CLIP_CODE_VERSION = "02369e700e41"  # bump only when visual rendering/compositing logic changes


def resolve_scene_src(raw_dir: pathlib.Path, src: str) -> pathlib.Path:
    """Resolves a scenario scene's `src` or `src_after` to a local file path:
    - `@media/<rel>` resolves against `MEDIA_DIR` (cross-vehicle comparing-scene photo fallback)
    - absolute paths resolve via `resolve_asset_path`
    - relative filenames resolve against the target vehicle's `raw_dir`."""
    if src.startswith(MEDIA_SRC_PREFIX):
        rel = src.removeprefix(MEDIA_SRC_PREFIX).lstrip("/\\")
        return MEDIA_DIR / pathlib.Path(rel)
    p = pathlib.Path(src)
    if p.is_absolute():
        return pathlib.Path(resolve_asset_path(p))
    return raw_dir / src


LINE_FIELDS = {"start", "dur", "fc_pos", "size", "color", "stroke_w", "shadow", "font", "font_style", "text"}

# Scene roles (GLOSSARY.md): what a scene shows. Its house rules follow from it, checked in load_scenario: the shot kinds
# agy may fill it with (make_scenario picks from the same list), the 4 arrows on an OpticGlass mirror view (rule 2.3) and
# no transition in, out of or inside the comparison section (rule 2.5).
ROLES = {
    "exterior": {"kinds": ["car_exterior", "car_detail"]},
    "detail": {"kinds": ["car_detail", "car_exterior"]},
    "card": {"kinds": ["car_exterior", "car_detail"]},  # under the 「광각미러가 꼭 필요한 이유」 card
    "before": {"kinds": ["mirror_before", "install_stock"]},  # stock-side b-roll
    "install": {"kinds": ["install_stock", "install_optic", "mirror_before"]},
    "after": {"kinds": ["mirror_after"], "arrows": True},  # the OpticGlass mirror view
    "compare_before": {"kinds": ["mirror_before"], "no_transition": True},
    "compare_after": {"kinds": ["mirror_after"], "arrows": True, "no_transition": True},
    "split": {"kinds": ["mirror_before", "mirror_after"], "arrows": True, "no_transition": True},  # 50:50, arrows on the right
    "close": {"kinds": ["car_exterior", "car_detail"]},
    "outro": {"kinds": []},
}


def check_scene_rules(name: str, scenes: list, tpl: dict) -> None:
    """The house rules each scene's role brings (ROLES), or ValueError naming the scene and the rule. Sets the scene's
    in-memory "compare" (no transition next to it) from its role and the template ("transitions": false = none)."""
    for sc in scenes:
        role = ROLES.get(sc.get("role"))
        where = f"{name}.json: {sc['id']}"
        if role is None:
            raise ValueError(f"{where}: 역할(role) {sc.get('role')!r}이 없습니다 ({', '.join(ROLES)} 중 하나)")
        kinds = sc.get("kind")  # what agy saw in the footage (generated scenarios); a person's pick has none
        for k in [kinds] if isinstance(kinds, str) else kinds or []:
            if k not in role["kinds"]:
                raise ValueError(f"{where}({sc['role']})에 {k} 장면이 들어 있습니다 ({sc['role']}에는 {'/'.join(role['kinds'])}만)")
        if role.get("arrows") and len(sc.get("arrows") or []) != 4:
            raise ValueError(f"{where}({sc['role']})에 옵틱 미러 화살표 4개가 필요합니다 (지금 {len(sc.get('arrows') or [])}개, 규칙 2.3)")
        if (sc["role"] == "split") != ("split" in sc) or (sc["role"] == "outro") != (sc["src"] == "outro"):
            raise ValueError(f"{where}: 역할 {sc['role']}이 영상(분할/아웃트로)과 맞지 않습니다")
        sc["compare"] = bool(role.get("no_transition")) or not tpl.get("transitions", True)


def load_template(key: str) -> dict:
    """work/scenarios/templates/<key>/: template.json (from extract_template.py) plus the copied draft files ("dir")."""
    tpl_dir = SCENARIOS_DIR / "templates" / key
    return {**json.loads((tpl_dir / "template.json").read_text(encoding="utf-8")), "dir": tpl_dir}


def load_scenario(name: str, path: pathlib.Path | None = None) -> dict:
    """work/scenarios/<name>.json: the car's template, scenes (source clip, in-point, look) and on-screen lines, with
    the template ("tpl") attached. A scene without start/dur takes its video slot's timing; a line takes any field it
    leaves out from the template's text slot with the same id. Scenes run back to back with no gaps and end with the
    outro. A scenario with a different scene count than the template's slots (the 80-100 s guideline cut is longer
    than the 41.5 s template) gives every scene its own start and dur. `path` checks a copy instead (agy_edit.py)."""
    scenario = json.loads((path or SCENARIOS_DIR / f"{name}.json").read_text(encoding="utf-8"))
    tpl = scenario["tpl"] = load_template(scenario["template"])
    scenes = scenario["scenes"]
    if len(scenes) != len(tpl["slots"]) and not all("start" in sc and "dur" in sc for sc in scenes):
        raise ValueError(f"{name}.json has {len(scenes)} scenes but template {scenario['template']} has {len(tpl['slots'])} video slots "
                         f"(a scenario with its own scene count must give every scene start and dur)")
    if scenes[-1]["src"] != "outro":
        raise ValueError(f"{name}.json: the last scene ({scenes[-1]['id']}) must be the outro (src \"outro\")")
    for sc, slot in zip(scenes, tpl["slots"]):
        sc.setdefault("start", slot["start"])
        sc.setdefault("dur", slot["dur"])
    for a, b in zip(scenes, scenes[1:]):
        if abs(a["start"] + a["dur"] - b["start"]) > 0.5 / 30:
            raise ValueError(f"{name}.json: {b['id']} starts at {b['start']}s but {a['id']} ends at {a['start'] + a['dur']:.3f}s")
    check_scene_rules(name, scenes, tpl)
    for line in scenario["lines"]:
        for k, v in tpl["text_slots"].get(line["id"], {}).items():
            line.setdefault(k, v)
        if LINE_FIELDS - line.keys():
            raise ValueError(f"{name}.json: line {line['id']} needs {sorted(LINE_FIELDS - line.keys())} "
                             f"(template {scenario['template']} has no {line['id']} text slot to take them from)")
    return scenario


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _is_image(path: pathlib.Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def _input_args(src: pathlib.Path, ss: float, dur_s: float, tmp_files: list[pathlib.Path]) -> list[str]:
    """FFmpeg input args for a video clip (-ss ... -i ...) or an EXIF-upright still image (-loop 1 -framerate 30 ...)."""
    if not _is_image(src):
        return ["-ss", f"{ss:.3f}", "-i", str(src)]
    from PIL import ImageOps
    fd, name = tempfile.mkstemp(prefix="upright_", suffix=".jpg")
    os.close(fd)
    up = pathlib.Path(name)
    tmp_files.append(up)
    with Image.open(src) as im:
        ImageOps.exif_transpose(im).convert("RGB").save(up, quality=96)
    return ["-loop", "1", "-framerate", "30", "-t", f"{dur_s:.3f}", "-i", str(up)]


def _with_cuda_decode(args: list[str]) -> list[str]:
    """Injects -hwaccel cuda before decoded video inputs when NVENC/NVDEC is available, skipping stream-copy/concat/audio/images."""
    if not _has_nvenc():
        return list(args)
    for idx, tok in enumerate(args[:-1]):
        if tok in ("-c:v", "-vcodec") and args[idx + 1] == "copy":
            return list(args)
    out: list[str] = []
    for idx, tok in enumerate(args):
        if tok == "-i" and idx + 1 < len(args):
            inp = str(args[idx + 1]).lower()
            prev_pair = args[max(0, idx - 2):idx]
            is_concat = prev_pair == ["-f", "concat"] or (idx >= 4 and args[idx - 4:idx - 2] == ["-f", "concat"])
            is_audio_or_lavfi = inp.endswith((".mp3", ".wav", ".m4a", ".aac", ".flac")) or prev_pair == ["-f", "lavfi"]
            is_image = inp.endswith(tuple(IMAGE_EXTS)) or "-loop" in args[max(0, idx - 6):idx]
            if not is_concat and not is_audio_or_lavfi and not is_image:
                out.extend(["-hwaccel", "cuda"])
        out.append(tok)
    return out


def _strip_hw_args(args: list[str]) -> list[str]:
    """Removes CUDA decode flags and swaps NVENC options for libx264 software encoding."""
    nv_len = len(_NVENC_ARGS)
    out: list[str] = []
    idx = 0
    while idx < len(args):
        if idx + 1 < len(args) and args[idx] == "-hwaccel" and args[idx + 1] == "cuda":
            idx += 2
            continue
        if tuple(args[idx : idx + nv_len]) == _NVENC_ARGS:
            out.extend(_SW_ARGS)
            idx += nv_len
            continue
        if args[idx] == "h264_nvenc":
            out.append("libx264")
            idx += 1
            continue
        out.append(args[idx])
        idx += 1
    return out


def run_ffmpeg(args):
    base = [find_ffmpeg(), "-nostdin", "-y", "-hide_banner", "-loglevel", "error"]
    hw_args = _with_cuda_decode(args)
    try:
        subprocess.run(base + hw_args, stdin=subprocess.DEVNULL, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.CalledProcessError:
        sw_args = _strip_hw_args(list(args))
        if sw_args == list(args) and hw_args == list(args):
            raise
        subprocess.run(base + sw_args, stdin=subprocess.DEVNULL, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


_SEAMLESS_BGM_PROFILES = (
    ("031 - Mood Audio Edit", (1.20, 63.20, 10.00, 1.50)),
    ("002 - sahara", (0.10, 40.70, 0.15, 1.20)),
)


def encode_bgm_mp3(src: pathlib.Path, out_mp3: pathlib.Path, dur_s: float) -> None:
    """Encodes a seamless loop of `src` to `dur_s` seconds as 192k MP3, skipping trailing silence/low-pass drops on known tracks."""
    profile = next((cfg for key, cfg in _SEAMLESS_BGM_PROFILES if key in src.name), None)
    fade_out_st = max(0.0, dur_s - 2.5)
    if profile is None:
        run_ffmpeg([
            "-stream_loop", "-1", "-i", str(src), "-t", f"{dur_s:.3f}",
            "-af", f"afade=t=in:st=0:d=0.8,afade=t=out:st={fade_out_st:.3f}:d=2.5,volume=0.85",
            "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3),
        ])
        return
    trim_a, trim_b, loop_a, xfade = profile
    seg0_len = trim_b - trim_a
    loop_len = max(1.0, trim_b - loop_a - xfade)
    n_loops = max(0, math.ceil((dur_s + 2.0 - seg0_len) / loop_len))
    parts = [f"[0:a]atrim=start={trim_a:.2f}:end={trim_b:.2f},asetpts=PTS-STARTPTS[a0]"]
    prev = "a0"
    for idx in range(1, n_loops + 1):
        parts.append(f"[0:a]atrim=start={loop_a:.2f}:end={trim_b:.2f},asetpts=PTS-STARTPTS[s{idx}]")
        nxt = f"a{idx}"
        parts.append(f"[{prev}][s{idx}]acrossfade=d={xfade:.2f}:c1=tri:c2=tri[{nxt}]")
        prev = nxt
    parts.append(
        f"[{prev}]atrim=start=0:end={dur_s:.3f},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=0.8,afade=t=out:st={fade_out_st:.3f}:d=2.5,volume=0.85[outa]"
    )
    run_ffmpeg([
        "-i", str(src),
        "-filter_complex", ";".join(parts),
        "-map", "[outa]",
        "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3),
    ])


@contextlib.contextmanager
def vehicle_build_lock(media_dir: pathlib.Path, label: str = ""):
    """Cross-process exclusive lock on media_dir/.build.lock so simultaneous GUI + CLI runs on the same car wait
    cleanly instead of colliding on .part files or spawning 2x FFmpeg encoders."""
    media_dir.mkdir(parents=True, exist_ok=True)
    lock_path = media_dir / ".build.lock"
    f = open(lock_path, "a+b")
    try:
        f.seek(0)
        if lock_path.stat().st_size == 0:
            f.write(b"0")
            f.flush()
        f.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                tag = label or media_dir.name
                print(f"[동시 실행 대기] {tag}: 다른 프로세스(GUI/CLI)에서 인코딩 중이라 완료될 때까지 대기합니다...", flush=True)
                while True:
                    try:
                        f.seek(0)
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.5)
                print(f"[동시 실행 재개] {tag}: 이전 프로세스 인코딩 완료 — 캐시를 재사용하여 이어서 진행합니다.", flush=True)
        yield
    finally:
        if os.name == "nt":
            import msvcrt
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        f.close()


def atomic_write_json(path: pathlib.Path, obj, indent: int | None = None) -> None:
    """Writes JSON atomically via a per-PID and per-thread temp file + os.replace so taskkill /T /F never leaves half-written JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}_{threading.get_ident()}_{time.time_ns()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")
    _retry_locked(lambda: os.replace(tmp, path))


def build_if_stale(out_p: pathlib.Path, builder, dur_s: float, deps: list, key: str = "") -> bool:
    """Builds out_p when it is missing, tiny, older than any dep (builder code, source clip, plate PNG), or built with
    a different key (the clip's own scenario settings, kept next to it as <name>.key).
    Encodes into a .part file first, so an interrupted run never leaves a half-written clip that later runs reuse."""
    newest_dep = max((p.stat().st_mtime for p in deps if p.exists()), default=0.0)
    key_p = out_p.with_suffix(".key")
    if (out_p.exists() and out_p.stat().st_size >= 10_000 and out_p.stat().st_mtime >= newest_dep
            and (not key or (key_p.exists() and key_p.read_text(encoding="utf-8") == key))):
        return False
    # per process and thread: two runs of the same car (parallel agents) never write one .part; the last whole clip wins
    part = out_p.with_name(f"{out_p.stem}.{os.getpid()}_{threading.get_ident()}.part{out_p.suffix}")
    try:
        builder(part, dur_s)
        _retry_locked(lambda: part.replace(out_p))
    finally:
        part.unlink(missing_ok=True)
    if key:
        _retry_locked(lambda: key_p.write_text(key, encoding="utf-8"))
    return True


def _retry_locked(op, tries: int = 6):
    """Windows briefly locks a just-written file (antivirus scan, indexer, a player holding the old clip); retry for
    ~5 s before giving up, so one scan does not fail a whole build."""
    for i in range(tries):
        try:
            return op()
        except OSError:  # PermissionError / WinError 5 / Errno 22 on a locked file
            if i == tries - 1:
                raise
            time.sleep(0.25 * (i + 1) * random.uniform(0.5, 1.5))  # jitter: writers of one file must not retry in lockstep


_FRAME_W, _FRAME_H = 1920, 1080
_FRAME_BYTES = _FRAME_W * _FRAME_H * 3


def _read_exact(stream, buf: bytearray) -> bool:
    mv = memoryview(buf)
    offset = 0
    total = len(buf)
    while offset < total:
        n = stream.readinto(mv[offset:])
        if not n:
            return False
        offset += n
    return True


def _draw_expansion_arrows_bgr(frame_bgr: np.ndarray, arrows: list, disp: float = 0.0) -> None:
    """Draws anti-aliased solid-orange (#F26925 -> BGR 37,105,242) outward-expanding arrows directly in BGR."""
    orange_bgr = (37, 105, 242)
    polys = []
    for ax, ay, ux, uy, length in arrows:
        mag = math.hypot(ux, uy) or 1.0
        ux, uy = ux / mag, uy / mag
        px, py = -uy, ux
        sx = ax + ux * (disp - length * 0.50)
        sy = ay + uy * (disp - length * 0.50)
        head_len = max(56.0, length * 0.50)
        head_half_w = max(36.0, length * 0.32)
        shaft_half_w = max(14.5, length * 0.125)
        bx = sx + ux * (length - head_len)
        by = sy + uy * (length - head_len)
        tx = sx + ux * length
        ty = sy + uy * length
        poly = np.array([
            [sx + px * shaft_half_w, sy + py * shaft_half_w],
            [bx + px * shaft_half_w, by + py * shaft_half_w],
            [bx + px * head_half_w,  by + py * head_half_w],
            [tx, ty],
            [bx - px * head_half_w,  by - py * head_half_w],
            [bx - px * shaft_half_w, by - py * shaft_half_w],
            [sx - px * shaft_half_w, sy - py * shaft_half_w],
        ], dtype=np.float32)
        polys.append(np.round(poly * 16.0).astype(np.int32))
    if polys:
        cv2.fillPoly(frame_bgr, polys, orange_bgr, lineType=cv2.LINE_AA, shift=4)


def _pyr_lk_median_flow(prev_gray: np.ndarray, gray: np.ndarray, pts0: np.ndarray):
    """Forward-backward Lucas-Kanade optical flow returning (inlier_pts1, median_delta_xy or None)."""
    if pts0 is None or len(pts0) < 4:
        return None, None
    lk_params = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 15, 0.03))
    pts1, st_f, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, pts0, None, **lk_params)
    if pts1 is None or st_f is None:
        return None, None
    pts0_b, st_b, _ = cv2.calcOpticalFlowPyrLK(gray, prev_gray, pts1, None, **lk_params)
    if pts0_b is None or st_b is None:
        return None, None
    p0 = pts0.reshape(-1, 2)
    p1 = pts1.reshape(-1, 2)
    pb = pts0_b.reshape(-1, 2)
    fb_err = np.hypot(p0[:, 0] - pb[:, 0], p0[:, 1] - pb[:, 1])
    step = np.hypot(p1[:, 0] - p0[:, 0], p1[:, 1] - p0[:, 1])
    good = (st_f.reshape(-1) == 1) & (st_b.reshape(-1) == 1) & (fb_err < 1.5) & (step < 36.0)
    if int(good.sum()) < 4:
        return None, None
    delta = np.median(p1[good] - p0[good], axis=0).astype(np.float32)
    return p1[good].reshape(-1, 1, 2).astype(np.float32), delta


def _warp_plate_onto_frame(f_bgr: np.ndarray, dst_pts: np.ndarray, plate_bgr: np.ndarray, src_pts: np.ndarray) -> None:
    rx0 = max(0, int(math.floor(dst_pts[:, 0].min())) - 6)
    ry0 = max(0, int(math.floor(dst_pts[:, 1].min())) - 6)
    rx1 = min(_FRAME_W, int(math.ceil(dst_pts[:, 0].max())) + 6)
    ry1 = min(_FRAME_H, int(math.ceil(dst_pts[:, 1].max())) + 6)
    rw, rh = rx1 - rx0, ry1 - ry0
    if rw <= 2 or rh <= 2:
        return
    dst_roi = dst_pts - np.array([[rx0, ry0]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src_pts, dst_roi)
    warped = cv2.warpPerspective(plate_bgr, M, (rw, rh), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    mask = np.zeros((rh, rw), dtype=np.uint8)
    cv2.fillConvexPoly(mask, np.round(dst_pts).astype(np.int32) - np.array([[rx0, ry0]], dtype=np.int32), 255)
    mask_3 = (cv2.GaussianBlur(mask, (3, 3), 0.8).astype(np.float32) / 255.0)[:, :, None]
    roi = f_bgr[ry0:ry1, rx0:rx1].astype(np.float32)
    f_bgr[ry0:ry1, rx0:rx1] = (roi * (1.0 - mask_3) + warped.astype(np.float32) * 0.94 * mask_3).astype(np.uint8)


class _PlateStreamTracker:
    """Causal per-frame NCC + perspective homography plate tracker (O(1) RAM, works on normal, arrow & split clips)."""

    def __init__(self, plate_keyframes: list, plate_bgr: np.ndarray):
        # Accept single track [[frac, quad], ...] or multi-track [[[frac, quad], ...], ...]
        if plate_keyframes and isinstance(plate_keyframes[0][0], (int, float)):
            self.tracks = [plate_keyframes]
        else:
            self.tracks = [t for t in (plate_keyframes or []) if t]
        self.plate_bgr = plate_bgr
        ph, pw = plate_bgr.shape[:2]
        self.src_pts = np.array([[0, 0], [pw - 1, 0], [pw - 1, ph - 1], [0, ph - 1]], dtype=np.float32)
        self.state = [{"seg": -1, "tmpl": None, "q0": None, "x0": 0, "y0": 0, "off": np.zeros(2, dtype=np.float32)}
                      for _ in self.tracks]

    def step(self, frame_bgr: np.ndarray, gray: np.ndarray, frac: float) -> None:
        for kfs, st in zip(self.tracks, self.state):
            if not kfs:
                continue
            seg = 0
            alpha = 0.0
            if len(kfs) >= 2:
                for i in range(len(kfs) - 1):
                    f0, _ = kfs[i]
                    f1, _ = kfs[i + 1]
                    if frac <= f1 or i == len(kfs) - 2:
                        seg = i
                        alpha = float(np.clip((frac - f0) / max(1e-6, f1 - f0), 0.0, 1.0))
                        break
            q_base = interp_quad(kfs, frac)
            if st["seg"] != seg:
                st["seg"] = seg
                st["off"] = np.zeros(2, dtype=np.float32)
                st["q0"] = q_base.copy()
                x0 = max(0, int(q_base[:, 0].min()) + 6)
                y0 = max(0, int(q_base[:, 1].min()) + 6)
                x1 = min(_FRAME_W, int(q_base[:, 0].max()) - 6)
                y1 = min(_FRAME_H, int(q_base[:, 1].max()) - 6)
                if x1 - x0 >= 20 and y1 - y0 >= 12:
                    st["tmpl"] = gray[y0:y1, x0:x1].copy()
                    st["x0"], st["y0"] = x0, y0
                else:
                    st["tmpl"] = None
                corr = np.zeros(2, dtype=np.float32)
            elif st["tmpl"] is not None:
                th, tw = st["tmpl"].shape[:2]
                base_x = st["x0"] + (q_base[0, 0] - st["q0"][0, 0])
                base_y = st["y0"] + (q_base[0, 1] - st["q0"][0, 1])
                exp_x = int(round(base_x + st["off"][0]))
                exp_y = int(round(base_y + st["off"][1]))
                pad = 24
                sx0, sy0 = max(0, exp_x - pad), max(0, exp_y - pad)
                sx1, sy1 = min(_FRAME_W, exp_x + tw + pad), min(_FRAME_H, exp_y + th + pad)
                search = gray[sy0:sy1, sx0:sx1]
                if search.shape[0] >= th and search.shape[1] >= tw:
                    res = cv2.matchTemplate(search, st["tmpl"], cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    if max_val > 0.70:
                        raw = np.array([(sx0 + max_loc[0]) - base_x, (sy0 + max_loc[1]) - base_y], dtype=np.float32)
                        st["off"] = 0.45 * st["off"] + 0.55 * raw
                corr = st["off"] * (1.0 - alpha)
            else:
                corr = np.zeros(2, dtype=np.float32)
            _warp_plate_onto_frame(frame_bgr, q_base + corr, self.plate_bgr, self.src_pts)


class _BezelArrowTracker:
    """Tracks the side mirror bezel around the 4 arrow anchors via PyrLK optical flow so handheld motion never detaches arrows."""

    def __init__(self, arrows: list, split_divider: bool = False):
        default_len = 110.0 if split_divider else 125.0
        self.base_arrows = [
            [float(a[0]), float(a[1]), float(a[2]), float(a[3]), float(a[4]) if len(a) > 4 else default_len]
            for a in (arrows or [])
        ]
        self.split_divider = split_divider
        self.lo_x = 964 if split_divider else 4
        self.shift = np.zeros(2, dtype=np.float32)
        self.pts: np.ndarray | None = None
        self.age = 0

    def _seed_bezel_points(self, gray: np.ndarray) -> np.ndarray | None:
        if not self.base_arrows:
            return None
        mask = np.zeros((_FRAME_H, _FRAME_W), dtype=np.uint8)
        sx, sy = float(self.shift[0]), float(self.shift[1])
        for ax, ay, *_ in self.base_arrows:
            cx, cy = int(round(ax + sx)), int(round(ay + sy))
            x0, x1 = max(self.lo_x, cx - 48), min(_FRAME_W - 4, cx + 48)
            y0, y1 = max(4, cy - 48), min(_FRAME_H - 4, cy + 48)
            if x1 > x0 and y1 > y0:
                mask[y0:y1, x0:x1] = 255
        mask = np.where(gray > 14, mask, 0).astype(np.uint8)
        if not mask.any():
            return None
        return cv2.goodFeaturesToTrack(gray, maxCorners=48, qualityLevel=0.02, minDistance=6, mask=mask)

    def step(self, frame_bgr: np.ndarray, gray: np.ndarray | None, prev_gray: np.ndarray | None, idx: int) -> None:
        if self.split_divider:
            frame_bgr[:, 958:962] = 255
        if not self.base_arrows:
            return
        if gray is not None:
            if prev_gray is not None and self.pts is not None:
                good_pts, delta = _pyr_lk_median_flow(prev_gray, gray, self.pts)
                if delta is not None:
                    cand = np.clip(self.shift + delta, -280.0, 280.0)
                    # Keep every arrow anchor safely inside its frame/panel
                    for ax, ay, _ux, _uy, length in self.base_arrows:
                        pad = length * 0.55
                        cand[0] = float(np.clip(cand[0], self.lo_x + pad - ax, (_FRAME_W - pad) - ax))
                        cand[1] = float(np.clip(cand[1], pad - ay, (_FRAME_H - pad) - ay))
                    self.shift = cand
                    self.pts = good_pts
                else:
                    self.pts = None
            self.age += 1
            if self.pts is None or len(self.pts) < 12 or self.age >= 12:
                self.pts = self._seed_bezel_points(gray)
                self.age = 0
        disp = 28.0 * (0.5 - 0.5 * math.cos(2.0 * math.pi * (idx % 18) / 18))
        sx, sy = float(self.shift[0]), float(self.shift[1])
        shifted = [[ax + sx, ay + sy, ux, uy, length] for ax, ay, ux, uy, length in self.base_arrows]
        _draw_expansion_arrows_bgr(frame_bgr, shifted, disp=disp)


class _FaceStreamTracker:
    """Combines exact keyframe interpolation with PyrLK optical flow between 0.5s keyframes so fast pans stay masked."""

    def __init__(self, face_keyframes: list):
        self.tracks = [t for t in (face_keyframes or []) if t]
        self.state = [{"seg": -2, "lin": None, "off": np.zeros(2, dtype=np.float32)} for _ in self.tracks]

    @staticmethod
    def _track_at(track: list, frac: float):
        if frac <= track[0][0]:
            _, cx, cy, r = track[0]
            return (-1, 0.0, float(cx), float(cy), float(r)) if r > 0 else None
        if frac >= track[-1][0]:
            _, cx, cy, r = track[-1]
            return (len(track), 1.0, float(cx), float(cy), float(r)) if r > 0 else None
        for i in range(len(track) - 1):
            f0, x0, y0, r0 = track[i]
            f1, x1, y1, r1 = track[i + 1]
            if f0 <= frac <= f1 or i == len(track) - 2:
                if r0 <= 0 and r1 <= 0:
                    return None
                if r0 > 0 and r1 <= 0:
                    return (i, 0.0, float(x0), float(y0), float(r0)) if frac <= 0.5 * (f0 + f1) else None
                if r0 <= 0 and r1 > 0:
                    return (i, 1.0, float(x1), float(y1), float(r1)) if frac >= 0.5 * (f0 + f1) else None
                alpha = float(np.clip((frac - f0) / max(1e-6, f1 - f0), 0.0, 1.0))
                return (i, alpha, (1.0 - alpha) * x0 + alpha * x1, (1.0 - alpha) * y0 + alpha * y1, (1.0 - alpha) * r0 + alpha * r1)
        return None

    def step(self, frame_bgr: np.ndarray, gray: np.ndarray | None, prev_gray: np.ndarray | None, frac: float) -> None:
        circles = []
        for track, st in zip(self.tracks, self.state):
            cur = self._track_at(track, frac)
            if cur is None:
                st["seg"] = -2
                st["lin"] = None
                st["off"] = np.zeros(2, dtype=np.float32)
                continue
            seg, alpha, lx, ly, lr = cur
            if st["seg"] != seg or st["lin"] is None:
                st["seg"] = seg
                st["off"] = np.zeros(2, dtype=np.float32)
            elif prev_gray is not None and gray is not None and 0.0 < alpha < 1.0:
                prev_cx = int(round(st["lin"][0] + st["off"][0]))
                prev_cy = int(round(st["lin"][1] + st["off"][1]))
                roi_r = max(16, int(round(lr * 0.75)))
                x0, x1 = max(0, prev_cx - roi_r), min(_FRAME_W, prev_cx + roi_r)
                y0, y1 = max(0, prev_cy - roi_r), min(_FRAME_H, prev_cy + roi_r)
                if x1 - x0 >= 16 and y1 - y0 >= 16:
                    mask = np.zeros((_FRAME_H, _FRAME_W), dtype=np.uint8)
                    cv2.circle(mask, (prev_cx, prev_cy), roi_r, 255, -1)
                    pts0 = cv2.goodFeaturesToTrack(prev_gray, maxCorners=24, qualityLevel=0.02, minDistance=5, mask=mask)
                    _, delta = _pyr_lk_median_flow(prev_gray, gray, pts0)
                    if delta is not None:
                        lin_step = np.array([lx - st["lin"][0], ly - st["lin"][1]], dtype=np.float32)
                        cand = st["off"] + (delta - lin_step)
                        norm = float(np.hypot(cand[0], cand[1]))
                        max_dev = 0.65 * lr
                        if norm > max_dev > 0:
                            cand = cand * (max_dev / norm)
                        st["off"] = cand
            st["lin"] = (lx, ly)
            eff = st["off"] * (1.0 - alpha) if 0.0 < alpha < 1.0 else np.zeros(2, dtype=np.float32)
            circles.append((int(round(lx + eff[0])), int(round(ly + eff[1])), int(round(lr))))
        if circles:
            mask_faces_in_frame(frame_bgr, circles, FACE_MASK_RGBA)


def _stream_composite_video(
    dec_args: list[str],
    out_mp4: pathlib.Path,
    dur_s: float,
    post_vf: str = "setsar=1",
    plate_keyframes: list | None = None,
    plate_png: pathlib.Path | None = None,
    arrows: list | None = None,
    split_divider: bool = False,
    face_keyframes: list | None = None,
) -> None:
    """Single-pass FFmpeg rawvideo stdout -> Python in-place BGR buffer -> FFmpeg rawvideo stdin pipeline."""
    has_plate = bool(plate_keyframes)
    if has_plate and not (plate_png and plate_png.exists()):
        raise FileNotFoundError(f"plate cover {plate_png} not found for {out_mp4.name}; add 로고_번호판.png to the car's media folder")
    has_arrows = bool(arrows) or split_divider
    has_faces = bool(face_keyframes)

    plate_bgr = None
    if has_plate:
        plate_bgr = cv2.imdecode(np.fromfile(str(plate_png), dtype=np.uint8), cv2.IMREAD_COLOR)
        if plate_bgr is None:
            raise RuntimeError(f"Failed to decode plate cover image: {plate_png}")

    ff = find_ffmpeg()
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    n_expected = max(1, int(round(dur_s * 30.0)))

    def _run_pass(use_hw: bool) -> None:
        plate_tracker = _PlateStreamTracker(plate_keyframes, plate_bgr) if has_plate else None
        arrow_tracker = _BezelArrowTracker(arrows or [], split_divider=split_divider) if has_arrows else None
        face_tracker = _FaceStreamTracker(face_keyframes) if has_faces else None
        need_gray = plate_tracker is not None or bool(arrows) or face_tracker is not None

        in_dec = _with_cuda_decode(dec_args) if use_hw else _strip_hw_args(dec_args)
        dec_cmd = [ff, "-nostdin", "-hide_banner", "-loglevel", "error", *in_dec,
                   "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{_FRAME_W}x{_FRAME_H}", "-r", "30", "pipe:1"]
        enc_cmd = [ff, "-y", "-hide_banner", "-loglevel", "error",
                   "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{_FRAME_W}x{_FRAME_H}", "-r", "30", "-i", "pipe:0",
                   "-vf", post_vf, "-an", *_enc_clip(use_hw=use_hw), "-pix_fmt", "yuv420p", "-r", "30", str(out_mp4)]

        buf = bytearray(_FRAME_BYTES)
        mv = memoryview(buf)
        frame = np.frombuffer(buf, dtype=np.uint8).reshape((_FRAME_H, _FRAME_W, 3))
        prev_gray: np.ndarray | None = None
        written = 0

        with tempfile.SpooledTemporaryFile(max_size=65536) as dec_err, tempfile.SpooledTemporaryFile(max_size=65536) as enc_err:
            dec_proc = subprocess.Popen(dec_cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=dec_err, bufsize=_FRAME_BYTES, creationflags=creationflags)
            enc_proc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE, stderr=enc_err, bufsize=_FRAME_BYTES, creationflags=creationflags)
            try:
                assert dec_proc.stdout is not None and enc_proc.stdin is not None
                while _read_exact(dec_proc.stdout, buf):
                    frac = min(1.0, written / max(1, n_expected - 1))
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if need_gray else None
                    if plate_tracker is not None and gray is not None:
                        plate_tracker.step(frame, gray, frac)
                    if arrow_tracker is not None:
                        arrow_tracker.step(frame, gray, prev_gray, written)
                    if face_tracker is not None:
                        face_tracker.step(frame, gray, prev_gray, frac)
                    enc_proc.stdin.write(mv)
                    prev_gray = gray
                    written += 1
            except BaseException:
                if dec_proc.poll() is None:
                    dec_proc.kill()
                if enc_proc.poll() is None:
                    enc_proc.kill()
                raise
            finally:
                if dec_proc.stdout:
                    dec_proc.stdout.close()
                if enc_proc.stdin:
                    try:
                        enc_proc.stdin.close()
                    except OSError:
                        pass
                dec_rc = dec_proc.wait()
                enc_rc = enc_proc.wait()
            if dec_rc != 0 or enc_rc != 0 or written == 0:
                dec_err.seek(0)
                enc_err.seek(0)
                d_msg = dec_err.read().decode("utf-8", errors="replace").strip()
                e_msg = enc_err.read().decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"ffmpeg stream composite failed for {out_mp4} (dec={dec_rc}, enc={enc_rc}, frames={written}): {d_msg} | {e_msg}")

    try:
        _run_pass(_has_nvenc())
    except RuntimeError:
        if not _has_nvenc():
            raise
        _run_pass(False)


def _panel_960x1080_filter(in_stream: str, crop_expr: str, out_label: str) -> str:
    import re
    m = re.search(r"crop=(\d+):(\d+):(\d+):(\d+)", crop_expr)
    if m:
        cw, ch = int(m.group(1)), int(m.group(2))
        fg_h = (int(round(ch * 960.0 / cw)) // 2) * 2
        if fg_h < 1068:
            uid = out_label
            feather = min(56, max(16, (1080 - fg_h) // 2))
            return (
                f"[{in_stream}]{crop_expr},fps=30,eq=brightness=0.03:gamma=1.06:saturation=1.05,split=2[{uid}_a][{uid}_b];"
                f"[{uid}_a]scale=960:1080:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop=960:1080,gblur=sigma=32,eq=brightness=-0.04[{uid}_bg];"
                f"[{uid}_b]scale=960:{fg_h}:flags=lanczos,format=rgba,"
                f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                f"a='255*min(1,min(Y/{feather},(H-1-Y)/{feather}))'[{uid}_fg];"
                f"[{uid}_bg][{uid}_fg]overlay=0:(H-h)/2:format=auto,format=yuv420p[{out_label}]"
            )
    return f"[{in_stream}]{crop_expr},scale=960:1080:flags=lanczos,fps=30,eq=brightness=0.03:gamma=1.06:saturation=1.05[{out_label}]"


def build_split_video_50x50(
    src_video: pathlib.Path,
    ss_before: float,
    ss_after: float,
    dur_s: float,
    crop_before: str,
    crop_after: str,
    arrows: list,
    out_mp4: pathlib.Path,
    face_keyframes: list = None,
    fade: bool = False,
    src_after: pathlib.Path = None,
    plate_keyframes: list = None,
    plate_png: pathlib.Path = None,
):
    """
    Builds a 1920x1080 50:50 split-screen comparison VIDEO from real 4K MOV footage
    (시공 전 left moving video vs 시공 후 right moving video) in a single streaming pass (no _tmp_split.mp4).
    """
    left_fc = _panel_960x1080_filter("0:v", crop_before, "left")
    right_fc = _panel_960x1080_filter("1:v", crop_after, "right")
    fc = f"{left_fc};{right_fc};[left][right]hstack=inputs=2,setsar=1[outv]"
    if fade:
        fade_d = min(0.22, dur_s * 0.22)
        fade_out_st = max(0.0, dur_s - fade_d)
        post_vf = f"fade=t=in:st=0:d={fade_d:.3f},fade=t=out:st={fade_out_st:.3f}:d={fade_d:.3f},setsar=1"
    else:
        post_vf = "setsar=1"
    tmp_files: list[pathlib.Path] = []
    try:
        dec_args = [
            *_input_args(src_video, ss_before, dur_s, tmp_files),
            *_input_args(src_after or src_video, ss_after, dur_s, tmp_files),
            "-filter_complex", fc,
            "-map", "[outv]",
            "-t", f"{dur_s:.3f}",
            "-an",
        ]
        _stream_composite_video(
            dec_args,
            out_mp4,
            dur_s,
            post_vf=post_vf,
            plate_keyframes=plate_keyframes,
            plate_png=plate_png,
            arrows=arrows,
            split_divider=True,
            face_keyframes=face_keyframes,
        )
    finally:
        for p in tmp_files:
            p.unlink(missing_ok=True)


def interp_quad(kfs, frac: float):
    for i in range(len(kfs) - 1):
        f0, q0 = kfs[i]
        f1, q1 = kfs[i + 1]
        if f0 <= frac <= f1 or i == len(kfs) - 2:
            alpha = (frac - f0) / max(1e-6, f1 - f0)
            return (1.0 - alpha) * np.array(q0, dtype=np.float32) + alpha * np.array(q1, dtype=np.float32)
    return np.array(kfs[-1][1], dtype=np.float32)


_mov_meta_lock = threading.Lock()


def get_mov_meta_cached(mov_f: pathlib.Path) -> tuple:
    """Returns (dur_us, width, height) for a raw .MOV file, cached by mtime+size in .mov_meta_cache.json."""
    cache_file = mov_f.parent / ".mov_meta_cache.json"
    st = mov_f.stat()
    key = f"{mov_f.name}:{st.st_mtime_ns}:{st.st_size}"
    with _mov_meta_lock:
        cache = {}
        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                cache = {}
        if key in cache:
            val = cache[key]
            return int(val[0]), int(val[1]), int(val[2])
    cap = cv2.VideoCapture(str(mov_f))
    dur_us = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30) * 1_000_000)
    w_px = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 3840
    h_px = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 2160
    cap.release()
    with _mov_meta_lock:
        cache = {}
        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                cache = {}
        cache[key] = [dur_us, w_px, h_px]
        try:
            atomic_write_json(cache_file, cache)
        except Exception:
            pass
    return dur_us, w_px, h_px


def trim_video_16x9(
    src_video: pathlib.Path,
    out_mp4: pathlib.Path,
    ss: float,
    dur_s: float,
    speed_pts: float = 1.0,
    brighten: bool = True,
    crop_expr: str = "",
    overlay_png: pathlib.Path = None,
    fade: bool = False,
    darken_for_title: bool = False,
    plate_keyframes: list = None,
    plate_png: pathlib.Path = None,
    animated_arrows: list = None,
    face_keyframes: list = None,
):
    has_arrows = animated_arrows is not None and len(animated_arrows) > 0
    has_plate = plate_keyframes is not None and len(plate_keyframes) > 0
    has_faces = face_keyframes is not None and len(face_keyframes) > 0
    use_speed = not _is_image(src_video) and abs(speed_pts - 1.0) > 0.01
    tmp_files: list[pathlib.Path] = []

    try:
        in_args = _input_args(src_video, ss, dur_s, tmp_files)
        if has_arrows or has_plate or has_faces:
            vf_parts = []
            if use_speed:
                vf_parts.append(f"setpts={speed_pts:.4f}*PTS")
            if crop_expr:
                vf_parts.append(crop_expr)
            vf_parts.append("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30,setsar=1")
            if darken_for_title:
                vf_parts.append("eq=brightness=-0.07:gamma=0.90:saturation=1.05")
            elif brighten:
                vf_parts.append("eq=brightness=0.03:gamma=1.06:saturation=1.05")
            post_vf = []
            if fade:
                fade_d = min(0.22, dur_s * 0.22)
                fade_out_st = max(0.0, dur_s - fade_d)
                post_vf.append(f"fade=t=in:st=0:d={fade_d:.3f},fade=t=out:st={fade_out_st:.3f}:d={fade_d:.3f}")
            post_vf.append("setsar=1")
            dec_args = [
                *in_args,
                "-t", f"{dur_s:.3f}",
                "-vf", ",".join(vf_parts),
                "-an",
            ]
            _stream_composite_video(
                dec_args,
                out_mp4,
                dur_s,
                post_vf=",".join(post_vf),
                plate_keyframes=plate_keyframes if has_plate else None,
                plate_png=plate_png if has_plate else None,
                arrows=animated_arrows if has_arrows else None,
                split_divider=False,
                face_keyframes=face_keyframes if has_faces else None,
            )
            return

        vf_parts = []
        if use_speed:
            vf_parts.append(f"setpts={speed_pts:.4f}*PTS")
        if crop_expr:
            vf_parts.append(crop_expr)
        vf_parts.append("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30,setsar=1")
        if darken_for_title:
            vf_parts.append("eq=brightness=-0.07:gamma=0.90:saturation=1.05")
        elif brighten:
            vf_parts.append("eq=brightness=0.03:gamma=1.06:saturation=1.05")
        if fade:
            fade_d = min(0.22, dur_s * 0.22)
            fade_out_st = max(0.0, dur_s - fade_d)
            vf_parts.append(f"fade=t=in:st=0:d={fade_d:.3f},fade=t=out:st={fade_out_st:.3f}:d={fade_d:.3f}")
        vf = ",".join(vf_parts)

        if overlay_png is not None and overlay_png.exists():
            run_ffmpeg([
                *in_args,
                "-i", str(overlay_png),
                "-t", f"{dur_s:.3f}",
                "-filter_complex", f"[0:v]{vf}[bg];[bg][1:v]overlay=0:0",
                "-an",
                *_enc_clip(), "-pix_fmt", "yuv420p", "-r", "30",
                str(out_mp4),
            ])
        else:
            run_ffmpeg([
                *in_args,
                "-t", f"{dur_s:.3f}",
                "-vf", vf,
                "-an",
                *_enc_clip(), "-pix_fmt", "yuv420p", "-r", "30",
                str(out_mp4),
            ])
    finally:
        for p in tmp_files:
            p.unlink(missing_ok=True)


# Rule 1: Dynamic Transition Catalog (Cross-Dissolve, Wipe, Slide, Fade, Zoom — replaces legacy blackout)
DYNAMIC_TRANSITION_CATALOG = [
    {
        "key": "cross_dissolve",
        "capcut_name": "혼합",
        "capcut_effect_id": "6724845717472416269",
        "capcut_resource_id": "6724845717472416269",
        "capcut_category_id": "2037709434",
        "capcut_category_name": "기본형",
        "capcut_path": "C:/Users/bssho/AppData/Local/CapCut/User Data/Cache/effect/6724845717472416269/7b53f4c008c4c684fccf8c7d4d46cc92",
    },
    {
        "key": "wipe",
        "capcut_name": "오른쪽",
        "capcut_effect_id": "6724227599616184836",
        "capcut_resource_id": "6724227599616184836",
        "capcut_category_id": "2037709434",
        "capcut_category_name": "기본형",
        "capcut_path": "C:/Users/bssho/AppData/Local/CapCut/User Data/Cache/effect/6724227599616184836/94ddc5b44c66c523dbf70622efb612d3",
    },
    {
        "key": "slide",
        "capcut_name": "왼쪽",
        "capcut_effect_id": "6726711499676455435",
        "capcut_resource_id": "6726711499676455435",
        "capcut_category_id": "2037709434",
        "capcut_category_name": "기본형",
        "capcut_path": "C:/Users/bssho/AppData/Local/CapCut/User Data/Cache/effect/6726711499676455435/1315a55c2f804d86894e1453976b48fd",
    },
    {
        "key": "fade",
        "capcut_name": "흐리게",
        "capcut_effect_id": "6916426617455645186",
        "capcut_resource_id": "6916426617455645186",
        "capcut_category_id": "30193",
        "capcut_category_name": "인기",
        "capcut_path": "C:/Users/bssho/AppData/Local/CapCut/User Data/Cache/effect/6916426617455645186/fc1352435f88c6f284b6c6dce8552ffe",
    },
    {
        "key": "zoom",
        "capcut_name": "지연 줌",
        "capcut_effect_id": "7488094700159782145",
        "capcut_resource_id": "7488094700159782145",
        "capcut_category_id": "30193",
        "capcut_category_name": "인기",
        "capcut_path": "C:/Users/bssho/AppData/Local/CapCut/User Data/Cache/effect/7488094700159782145/8f3ae25af421f026ede897c2e469449c",
    },
]


def prepare_scene_clips(scenes: list, raw_dir: pathlib.Path, media_dir: pathlib.Path, outro_src: pathlib.Path,
                        plate_png: pathlib.Path = None) -> list:
    """Encodes each scenario scene into media_dir/lf_<id>_<name>.mp4 (rebuilt only when its settings, source or the code
    change) and returns the scene list the builder places. src "outro" is the chosen outro file; a scene with "split"
    is a 50:50 before/after comparison; "compare" (set by load_scenario from the scene's role) keeps transitions away
    from the comparison section. A scene's "plates" ([frac, 4-point quad] keyframes),
    "faces" (tracks of [frac, cx, cy, r]) and "arrows" ([x, y, ux, uy, length], 4 on 시공 후) trace its footage."""
    total_scenes = len(scenes)
    done_cnt = 0
    prog_lock = threading.Lock()

    def _prepare_one(sc: dict) -> dict:
        nonlocal done_cnt
        sid = sc["id"]
        src = outro_src if sc["src"] == "outro" else resolve_scene_src(raw_dir, sc["src"])
        out_p = media_dir / f"lf_{sid}_{sc['name']}.mp4"
        plates, faces, arrows = sc.get("plates"), sc.get("faces"), sc.get("arrows")
        if "split" in sc:
            sp = sc["split"]
            src_after = resolve_scene_src(raw_dir, sp["src_after"]) if sp.get("src_after") else src  # the 시공 후 half from another clip
            builder = lambda p, d: build_split_video_50x50(src, sc["in"], sp["in_after"], d, sp["crop_before"], sp["crop_after"],
                                                           arrows or [], p, face_keyframes=faces, fade=False, src_after=src_after,
                                                           plate_keyframes=plates, plate_png=plate_png if plates else None)
        else:
            builder = lambda p, d: trim_video_16x9(src, p, sc["in"], d, speed_pts=sc.get("speed", 1.0), brighten=sc["look"] != "plain",
                                                   crop_expr=sc.get("crop", ""), darken_for_title=sc["look"] == "title",
                                                   plate_keyframes=plates, plate_png=plate_png if plates else None,
                                                   animated_arrows=arrows, face_keyframes=faces, fade=False)
        # The key holds everything the builder feeds this clip, so a scenario edit re-encodes only the scenes it touches;
        # _CLIP_CODE_VERSION re-encodes them all when this module (the encoding code) changes.
        deps = [src] + ([resolve_scene_src(raw_dir, sc["split"]["src_after"])] if sc.get("split", {}).get("src_after") else []) + (
            [plate_png] if plates else []) + ([FACE_MASK_PATH] if faces else [])
        cache_key = json.dumps({
            "sc": {k: v for k, v in sc.items() if k not in ("start", "compare", "plates", "faces", "arrows", "note", "role", "kind")},
            "arrows": arrows,
            "faces": faces,
            "plate": plates,
            "code": _CLIP_CODE_VERSION,
        }, sort_keys=True, ensure_ascii=False)
        built = build_if_stale(out_p, builder, sc["dur"], deps, cache_key)
        with prog_lock:
            done_cnt += 1
            if built or done_cnt == total_scenes:
                print(f"    [씬 클립 {done_cnt}/{total_scenes}] {sid} ({'인코딩 완료' if built else '캐시 완료'})", flush=True)
        return {"id": sid, "start": sc["start"], "dur": sc["dur"], "path": out_p,
                "is_split_compare": "split" in sc or sc.get("compare", False)}

    workers = min(2, max(1, os.cpu_count() or 2), len(scenes) or 1)
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(_prepare_one, scenes))
    return [_prepare_one(sc) for sc in scenes]


def fit_video_slots(dc: dict, tpl: dict, n_scenes: int) -> tuple:
    """The template draft's video slots, one per scenario scene: its main-track segments then its outro segment (the
    last scene). A scenario with more scenes than the template gets copies of the first main segment (new ids; the
    builder sets their material, timing and refs), one with fewer drops the extra main segments.
    Returns (main segments, all segments in scene order)."""
    main = dc["tracks"][tpl["tracks"]["main"]]["segments"]
    outro = dc["tracks"][tpl["tracks"]["outro"]]["segments"]
    need = n_scenes - len(outro)
    while len(main) < need:
        seg = copy.deepcopy(main[0])
        seg["id"] = str(uuid.uuid4()).upper()
        main.append(seg)
    del main[need:]
    return main, main + outro


def should_apply_transition(curr_scene: dict, next_scene: dict) -> bool:
    """
    Rule 2: Disable Transitions during Split-Screen Comparisons.
    Returns False when entering, exiting, or within any split-screen comparison scene.
    """
    if not curr_scene or not next_scene:
        return False
    if curr_scene.get("is_split_compare", False) or next_scene.get("is_split_compare", False):
        return False
    return True


def mask_faces_in_frame(
    frame_bgr: np.ndarray,
    face_circles: list,
    mask_rgba: np.ndarray = None,
) -> np.ndarray:
    """
    Rule 3: Face Masking Requirement.
    Covers each detected/tracked face region (cx, cy, r) entirely with the solid black circle
    privacy barrier (구글드라이브다운파일/media/face_mask_circle.png) without exposing any facial features.
    """
    h, w = frame_bgr.shape[:2]
    for cx, cy, r in face_circles:
        if r <= 0:
            continue
        d = 2 * r
        x0, y0 = cx - r, cy - r
        x1, y1 = x0 + d, y0 + d
        cx0, cy0 = max(0, x0), max(0, y0)
        cx1, cy1 = min(w, x1), min(h, y1)
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        if mask_rgba is not None:
            resized = cv2.resize(mask_rgba, (d, d), interpolation=cv2.INTER_AREA)
            sub = resized[cy0 - y0 : cy1 - y0, cx0 - x0 : cx1 - x0]
            alpha = sub[:, :, 3:4].astype(np.float32) / 255.0
            roi = frame_bgr[cy0:cy1, cx0:cx1].astype(np.float32)
            frame_bgr[cy0:cy1, cx0:cx1] = (roi * (1.0 - alpha)).astype(np.uint8)
        else:
            cv2.circle(frame_bgr, (cx, cy), r, (0, 0, 0), -1, lineType=cv2.LINE_AA)
    return frame_bgr


# --- CapCut text tracks from the line plan (the scenario lines) ----------------------------------------------------
# ponytail: calibration knobs, set without a CapCut render. A line's fc_pos/size are scenario pixels on the 1920x1080
# canvas (named after the FilmCraft preview they were first measured on, removed 2026-11-06). CapCut size per scenario
# px is the ratio the six hand-tuned Part 3-4 lines already used (style size x scale ~ 0.134 x plan size); the stroke
# maps 10 px at size 92 to the template's 0.06. fc_pos y sits near the text baseline: the rendered centre is 0.40 x size
# above it. Re-measure from one CapCut export frame if CapCut sizes or places look off.
CC_SIZE_PER_FC_PX = 0.134
CC_STROKE_PER_FC_RATIO = 0.06 / (10 / 92)
FC_CENTER_ABOVE_Y = 0.40
_CC_DROP_SHADOW = [{"alpha": 0.88, "angle": -45.0, "content": {"render_type": "solid", "solid": {"color": [0.0, 0.0, 0.0]}},
                    "distance": 8.0, "feather": 0.28, "offset": {"x": 0.10, "y": -0.10}}]


def _frame_us(sec: float, fps: int = 30) -> int:
    """Seconds -> microseconds on a frame boundary, so a line starts on the same frame as its video cut."""
    return round(round(sec * fps) / fps * 1_000_000)


def _resolve_template_font(row: dict, default_font_path: str) -> tuple[str, str]:
    """Return (font_path_fwd, font_title) for a wide1/template-style slot using bundled Korean-safe fonts."""
    from portable_paths import ASSETS_DIR, to_fwd
    fonts_dir = ASSETS_DIR / "fonts"
    preset = row.get("style_preset") or ""
    rid = row.get("id", "")
    if preset == "title_translucent" or rid == "lt01":
        cands, title = ("NotoSansKR-Regular.otf", "NotoSansKR-Bold-Static.ttf"), "NotoSansKR Regular"
    elif preset == "card_sub" or rid == "w04a":
        cands, title = ("GalleryModern.otf", "NotoSansKR-Regular.otf"), "GalleryModern Regular"
    elif preset == "card_title" or rid == "w04b":
        cands, title = ("BlackHanSans-Regular.ttf", "Paperlogy-9Black.ttf"), "BlackHanSans Regular"
    else:
        cands, title = ("NotoSansKR-Bold-Static.ttf", "Paperlogy-7Bold.ttf"), "NotoSansKR Bold"
    for name in cands:
        p = fonts_dir / name
        if p.exists():
            return to_fwd(p.resolve()), title
    return default_font_path, f"{row.get('font', 'Paperlogy')} {row.get('font_style', '7 Bold')}"


def _style_capcut_text(mat: dict, row: dict, font_path: str, preserve_template_style: bool = False):
    """Apply either the authentic CapCut wide-mirror template style (preserve_template_style=True: no black box,
    original 花字/stroke/opacity preserved with bundled Korean-safe fonts) or the legacy R3 house box look."""
    size = round(row["size"] * CC_SIZE_PER_FC_PX, 2)
    width = round(row["stroke_w"] / row["size"] * CC_STROKE_PER_FC_RATIO, 4) if row["stroke_w"] > 0 else 0.0
    box = bool(row.get("box", not preserve_template_style))
    use_font_path, use_font_title = (_resolve_template_font(row, font_path)
                                     if preserve_template_style else (font_path, f"{row['font']} {row['font_style']}"))
    font_id = str(uuid.uuid5(uuid.NAMESPACE_URL, use_font_path)).upper()  # stable per font file
    black = {"render_type": "solid", "solid": {"alpha": 1.0, "color": [0.0, 0.0, 0.0]}}
    content = json.loads(mat.get("content") or "{}")
    style = (content.get("styles") or [{}])[0]  # one run over the whole line; template runs could overlap
    keep_fx = bool(preserve_template_style and style.get("effectStyle"))
    rgb = [int(row["color"][i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    if keep_fx:
        # Preserve original CapCut 花字 effectStyle & texture/solid fill; bind Korean-safe font and update text range
        style.update({
            "range": [0, len(row["text"])], "size": size, "font": {"id": font_id, "path": use_font_path},
            "bold": False,
        })
        if style.get("fill", {}).get("content", {}).get("render_type") != "texture":
            style["fill"] = {"alpha": 1.0, "content": {"render_type": "solid", "solid": {"alpha": 1.0, "color": rgb}}}
    else:
        style.update({
            "range": [0, len(row["text"])], "size": size, "font": {"id": font_id, "path": use_font_path}, "useLetterColor": True,
            "fill": {"alpha": 1.0, "content": {"render_type": "solid", "solid": {"alpha": 1.0, "color": rgb}}},
            "strokes": [{"alpha": 1.0, "content": black, "width": width}] if width else [],
            "shadows": copy.deepcopy(_CC_DROP_SHADOW) if row.get("shadow") else [],
            "effectStyle": None,
            "bold": False,
        })
    content.update({"text": row["text"], "styles": [style]})
    global_alpha = float(row.get("alpha", mat.get("global_alpha", 1.0))) if preserve_template_style else 1.0
    check_flag = ((mat.get("check_flag", 7) & ~(8 | 16 | 32 | 64))
                  | (0 if keep_fx else (8 if width else 0))
                  | (16 if box else 0)
                  | (0 if keep_fx else (32 if row.get("shadow") else 0)))
    mat.update({
        "content": json.dumps(content, ensure_ascii=False), "text_color": row["color"],
        "use_effect_default_color": keep_fx,
        "font_path": use_font_path, "font_title": use_font_title, "font_id": "", "font_resource_id": "",
        "fonts": [{"id": font_id, "path": use_font_path, "title": use_font_title, "resource_id": "",
                   "third_resource_id": "", "category_id": "", "category_name": "", "source_platform": 0, "effect_id": "",
                   "team_id": "", "file_uri": "", "request_id": ""}],
        "font_size": size, "border_color": "#000000", "border_width": width, "border_alpha": 1.0,
        "has_shadow": bool(row.get("shadow")) and not keep_fx, "shadow_color": "#000000", "shadow_alpha": 0.88, "shadow_angle": -45.0,
        "shadow_distance": 8.0, "shadow_smoothing": 0.28, "shadow_point": {"x": 0.10, "y": -0.10},
        "alignment": 1, "background_style": 1 if box else 0, "background_color": "#000000", "background_alpha": 1.0,
        "background_round_radius": 0.14 if box else 0.0, "background_height": 0.18 if box else 0.14,
        "background_width": 0.18 if box else 0.14,
        "background_horizontal_offset": 0.0, "background_vertical_offset": 0.0,
        "text_preset_resource_id": "", "bold_width": 0.0, "global_alpha": global_alpha,
        "check_flag": check_flag,
    })
    return keep_fx


def apply_text_plan_to_capcut(dc: dict, plan: list, font_path: str, text_slots: dict,
                              preserve_template_style: bool = False) -> list:
    """Rebuilds a template draft's text tracks from the line plan (the scenario's text, timing, position and colours).
    Each row reuses the animation of the template text segment its text slot came from (template.json text_slots: the
    first unused segment containing the slot's text, in time order); a row without a slot (the section card, which the
    template draws as a text_template) clones a matched row with the same outline style. When preserve_template_style
    is True (opticglass_wide1), matched slots keep their original CapCut 花字/stroke/opacity with no black box.
    Returns [(plan id, segment id)]."""
    M = dc["materials"]
    texts = {t["id"]: t for t in M.get("texts", [])}
    text_fx = {e["id"] for e in M.get("effects", []) if e.get("type") in ("text_effect", "bloom")}  # 花字 and glow
    anims = {a["id"]: a for a in M.get("material_animations", [])}
    text_tracks = [tr for tr in dc["tracks"] if tr["type"] == "text"]
    pool = sorted(((s, texts[s["material_id"]]) for tr in text_tracks for s in tr["segments"] if s["material_id"] in texts),
                  key=lambda p: p[0]["target_timerange"]["start"])
    picked = {}
    for row in plan:
        key = text_slots.get(row["id"], {}).get("text")
        for i, (seg, mat) in enumerate(pool):
            if key and key in json.loads(mat.get("content") or "{}").get("text", ""):
                picked[row["id"]] = pool.pop(i)
                break
    if not picked:
        raise ValueError("no plan row matched a template text segment; check the template's text_slots")
    for tr in text_tracks:
        tr["segments"] = []

    canvas_w, canvas_h = dc["canvas_config"]["width"], dc["canvas_config"]["height"]
    placed = []
    for row in plan:
        cloned = False
        if row["id"] in picked:
            seg, mat = picked[row["id"]]
        else:  # clone a matched row (prefer one without effectStyle when preserve_template_style)
            cloned = True
            base = next((r["id"] for r in plan if r["id"] in picked and (r["stroke_w"] > 0) == (row["stroke_w"] > 0)
                         and (not preserve_template_style or not (json.loads(picked[r["id"]][1].get("content") or "{}").get("styles") or [{}])[0].get("effectStyle"))),
                        next(iter(picked)))
            seg, mat = copy.deepcopy(picked[base][0]), copy.deepcopy(picked[base][1])
            seg["id"], mat["id"] = str(uuid.uuid4()).upper(), str(uuid.uuid4()).upper()
            seg["material_id"] = mat["id"]
            if preserve_template_style:
                c_tmp = json.loads(mat.get("content") or "{}")
                for st in c_tmp.get("styles", []):
                    st["effectStyle"] = None
                mat["content"] = json.dumps(c_tmp, ensure_ascii=False)
                mat["global_alpha"] = 1.0
            M["texts"].append(mat)
            refs = []
            for ref in seg.get("extra_material_refs", []):
                if ref in anims:
                    anim = copy.deepcopy(anims[ref])
                    anim["id"] = ref = str(uuid.uuid4()).upper()
                    M.setdefault("material_animations", []).append(anim)
                refs.append(ref)
            seg["extra_material_refs"] = refs
        keep_fx = _style_capcut_text(mat, row, font_path, preserve_template_style=preserve_template_style)
        start, end = _frame_us(row["start"]), _frame_us(row["start"] + row["dur"])
        seg["target_timerange"] = {"start": start, "duration": end - start}
        if isinstance(seg.get("source_timerange"), dict):
            seg["source_timerange"] = {"start": 0, "duration": end - start}
        cy = row["fc_pos"][1] - FC_CENTER_ABOVE_Y * row["size"]
        seg["clip"]["scale"] = {"x": 1.0, "y": 1.0}
        seg["clip"]["transform"] = {"x": round((row["fc_pos"][0] - canvas_w / 2) / (canvas_w / 2), 4),
                                    "y": round((canvas_h / 2 - cy) / (canvas_h / 2), 4)}
        if not keep_fx or cloned:
            seg["extra_material_refs"] = [r for r in seg.get("extra_material_refs", []) if r not in text_fx]
        # first text track with no overlap; a fresh track when the plan stacks more lines than the template had
        track = next((tr for tr in text_tracks if all(start >= s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                                                      or end <= s["target_timerange"]["start"] for s in tr["segments"])), None)
        if track is None:
            track = copy.deepcopy(text_tracks[0])
            track["id"], track["segments"] = str(uuid.uuid4()).upper(), []
            dc["tracks"].append(track)
            text_tracks.append(track)
        track["segments"].append(seg)
        placed.append((row["id"], seg["id"]))
    for tr in text_tracks:
        tr["segments"].sort(key=lambda s: s["target_timerange"]["start"])
    used = {s["material_id"] for tr in text_tracks for s in tr["segments"]}
    M["texts"] = [t for t in M["texts"] if t["id"] in used]
    M["text_templates"] = [t for t in M.get("text_templates", []) if t["id"] in used]
    return placed
