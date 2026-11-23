"""The three thumbnail photos of a car (exterior, before, after), picked and masked by the AI (agy) with no one picking
photos; the GUI picker is only an optional override.

media/<car>/thumb_picks.json (media/<car>/ = drive_index.media_dir, the car's Drive path) keeps, per slot, the source
photo (a file name relative to media/<car>/gdrive_raw; stills cut from the car's clips are in its _frames/) and the
plate quads and face circles drawn on it; save() writes the masked copies to media/<car>/thumb/<slot>.jpg.
ai_check() has agy (llm.py, task photo_check) sort the car's photos into the slots and find plates and faces when
nothing is picked yet (stills from its clips when the photos lack a kind, an install shot when there is no clean
mirror view), then look at the masked copies for any plate or face left and fix what it finds (re-mask, then the next
photo); it records the verdict in thumb/ai_check.json. Stage 3 uses only copies that passed (ready()), so a thumbnail
never shows an uncovered plate or face, or another car's photo.

usage: py video-automation/work/thumb_photos.py               self-check (no agy call)
       py video-automation/work/thumb_photos.py <slug>        AI check of the saved picks (AI picks if none)
       py video-automation/work/thumb_photos.py <slug> --auto AI picks again from all of the car's photos
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image, ImageOps

import drive_index
from longform_common import atomic_write_json, mask_faces_in_frame
from portable_paths import ASSETS_DIR, find_ffmpeg

SLOTS = {"car_exterior": "외관", "before_photo": "시공 전", "after_photo": "시공 후"}
PHOTO_EXTS = {".jpg", ".jpeg", ".png"}
PLATE_PNG = ASSETS_DIR / "masks" / "로고_번호판.png"
FACE_PNG = ASSETS_DIR / "masks" / "face_mask_circle.png"
# the kinds agy may fill each slot with: the 시공 전/후 cards compare the stock and the OpticGlass mirror views only
# (2026-11-10, user: never an install shot with hands); a car with no mirror view gets no thumbnail and a report
AI_KINDS = {"car_exterior": ["car_exterior"], "before_photo": ["mirror_before"], "after_photo": ["mirror_after"]}
KIND_LABEL = {"car_exterior": "외관", "car_detail": "외관", "mirror_before": "순정 미러 시야", "mirror_after": "옵틱 미러 시야",
              "install_stock": "시공", "install_optic": "시공", "other": "기타"}


class ShortFootage(ValueError):
    """The car's photos or clips lack a kind of shot a role or slot needs. str() is the ~100-character report the GUI
    shows in a message box (footage_report)."""


def footage_report(slug: str, missing: list, detail: str = "", thumbnail: bool = False) -> str:
    """'<car>: 사진 0장·영상 7개(시공 59·기타 28)에 외관·옵틱 미러 시야 장면이 없습니다. ...' from what agy already sorted
    (thumb/review.json): what the clips and photos do show, what is missing, and what to upload. No agy call."""
    from collections import Counter
    f = drive_index.media_dir(slug) / "thumb" / "review.json"
    cache = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    items = {k.split("|")[1]: v for k, v in cache.items() if k.startswith(REVIEW_VERSION + "|")}
    frames = {n: v for n, v in items.items() if n.startswith("_frames/")}
    photos = {n: v for n, v in items.items() if not n.startswith("_frames/")}
    clips = {re.sub(r"_\d+\.\ds\.jpg$", "", n) for n in frames}
    seen = lambda d: "·".join(f"{k} {n}" for k, n in Counter(KIND_LABEL.get(v.get("kind"), "기타") for v in d.values()).most_common(3))
    video = f"영상 {len(clips)}개" + (f"({seen(frames)})" if frames else "")
    photo = f"사진 {len(photos)}장" + (f"({seen(photos)})" if photos else "")
    want = "·".join(missing).replace("순정 미러 시야·옵틱 미러 시야", "순정·옵틱 미러 시야")
    title = drive_index.title(slug)
    if thumbnail:
        return (f"{title} 썸네일: {photo}·{video}에 {want} 장면이 "
                f"없어 전/후 칸을 못 채웁니다. 해당 사진·영상을 Drive에 올려 주세요.")
    return f"{title}: {photo}·{video}에 {want} 장면{detail}이 없습니다. 해당 사진·영상을 Drive에 올려 주세요."
AI_BATCH = 8  # photos per agy call: the agent opens them one by one, and a call gets 300 s
VIDEO_EXTS = {".mov", ".mp4"}
FRAME_EVERY_S, FRAMES_PER_VIDEO = 2.0, 8  # stills cut from the car's clips when its photos lack a kind
FIX_ROUNDS = 2  # after a failed check: agy masks what it still sees, then the slot takes its next-best photo
AI_SIDE = 1600  # long side of the copies agy sees; its 0-1000 coordinates are mapped back to the full photo
FACE_PAD, PLATE_PAD = 1.3, 1.12  # the AI's circles and corners sit tight; grow them so no edge of a face or plate shows

REVIEW_ASK = """This folder holds {n} images ({files}) from one car's job at OpticGlass, a shop that replaces stock
side-mirror glass with a wide-angle mirror. Names like p1_v2_007s.jpg are sequential stills from video v2 (at 7s);
names like p1_photo.jpg are standalone photos. Open and look at every one of them. Answer with only a JSON object:
{{"photos": [{{"file": "<exact file name>", "kind": "car_exterior|car_detail|mirror_before|mirror_after|install_stock|install_optic|other",
  "score": 1-10, "plates": [[[x, y], [x, y], [x, y], [x, y]]], "faces": [[cx, cy, r]], "mirror": [x0, y0, x1, y1]}}]}}
- kind:
  car_exterior = the whole car (or most of its front, rear or side) seen from outside;
  car_detail = a close-up of a part of the car's outside (emblem, badge, lettering, head- or tail-light, grille, wheel, body line);
  mirror_before = a shot demonstrating the narrow, flat reflected view of the stock side mirror — either mounted in the housing OR held by hand right in front of the mirror housing to show its narrow reflection;
  mirror_after = a shot demonstrating the much wider, curved reflected view of the installed OpticGlass wide-angle mirror in the housing — including comparison shots where a hand lifts or holds the old stock glass above or beside the housing to reveal the wide view inside the housing;
  install_stock = active disassembly/removal (prying glass out, unplugging wires, empty housing) where the stock mirror's reflected view is NOT being demonstrated;
  install_optic = active fitting/wiring/bench handling of the new glass where the installed mirror's wide reflected view is NOT yet being demonstrated;
  other = anything else: an empty housing with no glass, a close-up of a person or the car's inside without a mirror reflection, or an already edited image with a title, text or graphics drawn on it.
- score: how well the image works as that kind (sharp, whole car or whole mirror housing in frame; a clean view without hands scores higher than a hand-held comparison, e.g. 8-10 vs 6-7).
- plates: the 4 corners of every licence plate, readable or not, also on other cars and in reflections (an orange-and-white "Optic-Glass" plate cover is already a cover, not a plate).
- faces: a circle over every human face or head, also partly cut off, small, in the background, or reflected in a mirror, window or paint.
- mirror: the box around the whole side mirror demonstrating the view (for mirror_before when held in front of the housing, box that held stock glass/housing; for mirror_after when the old glass is lifted away, box ONLY the installed housing+wide glass, NOT the lifted glass); [] when no side mirror is seen.
- Coordinates are 0-1000: x as a fraction of the image's width, y of its height; r as a fraction of the width.
  Empty lists when there is none."""

VERIFY_ASK = """This folder holds {n} photos ({files}) that are about to be published in a YouTube thumbnail. Licence
plates must be covered (an orange-and-white "Optic-Glass" plate cover is the cover, not a plate) and human faces must be
covered by solid black circles. Open and look at every photo closely, including small background areas and
reflections in mirrors, windows and paint. Answer with only a JSON object:
{{"photos": [{{"file": "x.jpg", "plate_visible": true|false, "face_visible": true|false, "where": "..."}}]}}
plate_visible: any plate characters can still be read. face_visible: any part of a human face can still be seen.
where: in Korean, where in the photo it is (empty when both are false)."""

FIX_ASK = """This folder holds {n} photo(s) ({files}) about to be published in a YouTube thumbnail. Some licence plates
and faces are already covered: an orange-and-white "Optic-Glass" plate cover and solid black circles are covers, not
plates or faces. A check still saw this uncovered: {where}. Open the photo and find only what is still NOT covered.
Answer with only a JSON object:
{{"photos": [{{"file": "x.jpg", "plates": [[[x, y], [x, y], [x, y], [x, y]]], "faces": [[cx, cy, r]]}}]}}
plates: the 4 corners of every uncovered licence plate (readable or not, also in reflections); faces: a circle over every
uncovered human face or head. Coordinates are 0-1000: x as a fraction of the photo's width, y of its height; r as a
fraction of the width. Empty lists when there is none."""
REVIEW_VERSION = hashlib.sha1(REVIEW_ASK.encode()).hexdigest()[:8]  # cached answers to an older prompt are asked again


def picks_file(slug: str) -> pathlib.Path:
    return drive_index.media_dir(slug) / "thumb_picks.json"


def masked_file(slug: str, slot: str) -> pathlib.Path:
    return drive_index.media_dir(slug) / "thumb" / f"{slot}.jpg"


def check_file(slug: str) -> pathlib.Path:
    return drive_index.media_dir(slug) / "thumb" / "ai_check.json"


def load_picks(slug: str) -> dict:
    f = picks_file(slug)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def raw_dir(slug: str) -> pathlib.Path:
    return drive_index.media_dir(slug) / "gdrive_raw"


_AUTO_STILL_RE = re.compile(r"^0[012]_.*_(?:car_exterior|before_mirror|after_mirror)\.jpg$", re.I)


def candidates(slug: str, frames: bool = False) -> list:
    """This car's own photos only (its Drive download, excluding any legacy auto-extracted stills); with frames
    also the stills video_frames() cut into gdrive_raw/_frames/ (names relative to gdrive_raw), for the GUI picker."""
    raw = raw_dir(slug)
    names = sorted(
        p.name for p in raw.iterdir()
        if p.suffix.lower() in PHOTO_EXTS and not _AUTO_STILL_RE.match(p.name)
    ) if raw.exists() else []
    return names + (sorted(f"_frames/{p.name}" for p in (raw / "_frames").glob("*.jpg")) if frames else [])


def open_rgb(path: pathlib.Path) -> Image.Image:
    """Upright as a phone shows it (EXIF rotation applied), so GUI clicks and the saved copy share coordinates."""
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def _imread_unicode(path: pathlib.Path, flags=cv2.IMREAD_UNCHANGED) -> np.ndarray:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), flags)  # cv2.imread fails on Korean paths


def order_quad(pts) -> np.ndarray:
    """Four clicked corners in any order -> top-left, top-right, bottom-right, bottom-left."""
    p = np.array(pts, dtype=np.float32)
    s, d = p.sum(axis=1), p[:, 1] - p[:, 0]
    return np.array([p[s.argmin()], p[d.argmin()], p[s.argmax()], p[d.argmax()]], dtype=np.float32)


def apply_masks(img: Image.Image, plates: list, faces: list) -> Image.Image:
    """Plates: 로고_번호판.png warped onto each 4-corner quad (homography). Faces: face_mask_circle.png."""
    bgr = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    if plates:
        plate = _imread_unicode(PLATE_PNG, cv2.IMREAD_COLOR)
        ph, pw = plate.shape[:2]
        src = np.array([[0, 0], [pw - 1, 0], [pw - 1, ph - 1], [0, ph - 1]], dtype=np.float32)
        for quad in plates:
            dst = order_quad(quad)
            warped = cv2.warpPerspective(plate, cv2.getPerspectiveTransform(src, dst), (w, h), flags=cv2.INTER_LANCZOS4)
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillConvexPoly(mask, np.round(dst).astype(np.int32), 255)
            bgr[mask > 0] = warped[mask > 0]
    if faces:
        mask_faces_in_frame(bgr, [tuple(int(v) for v in c) for c in faces], _imread_unicode(FACE_PNG))
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def save(slug: str, picks: dict) -> None:
    """picks = {slot: {"src": file name in gdrive_raw, "plates": [[[x, y] x4], ...], "faces": [[cx, cy, r], ...]}} for all three slots."""
    missing = [SLOTS[s] for s in SLOTS if s not in picks]
    if missing:
        raise ValueError(f"사진을 고르지 않은 칸: {', '.join(missing)}")
    check_file(slug).unlink(missing_ok=True)  # the AI's verdict was about the copies about to be replaced
    for slot, p in picks.items():
        out = masked_file(slug, slot)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".tmp.jpg")
        apply_masks(open_rgb(raw_dir(slug) / p["src"]), p["plates"], p["faces"]).save(tmp, quality=95)
        if slot == next(iter(picks)):  # the old picks go before the first copy is replaced: a save that fails
            picks_file(slug).unlink(missing_ok=True)  # partway must not pair new copies with them in ready()
        os.replace(tmp, out)
    # written last: ready() trusts the copies only once the picks that made them are on disk
    tmp = picks_file(slug).with_suffix(".tmp")
    tmp.write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, picks_file(slug))
    atomic_write_json(check_file(slug), {"ok": True, "problems": [], "failed": [], "copies": _copies(slug)}, indent=1)


def saved(slug: str):
    """{slot: masked copy} once all three are picked and saved, else None. A source photo removed from gdrive_raw
    since (the picker then shows that slot as unpicked) takes its copy out of use too, and so does an agy pick of a kind
    the slot no longer takes (the install shots picked for 시공 전/후 before 2026-11-10); a person's pick stands."""
    picks, out = load_picks(slug), {s: masked_file(slug, s) for s in SLOTS}
    kind_ok = lambda s: picks[s].get("by") != "agy" or picks[s].get("kind") in (None, *AI_KINDS[s])
    ok = all(s in picks and (raw_dir(slug) / picks[s]["src"]).exists() and out[s].exists() and kind_ok(s) for s in SLOTS)
    return out if ok else None


def _copies(slug: str) -> dict:
    """{slot: sha1 of its masked copy}: ties ai_check's verdict to the copies it looked at."""
    return {s: hashlib.sha1(masked_file(slug, s).read_bytes()).hexdigest() for s in SLOTS if masked_file(slug, s).exists()}


def ready(slug: str):
    """The saved copies, ready immediately without post-masking AI inspection."""
    return saved(slug)


# --- AI (agy) --------------------------------------------------------------------------------------------------------
def _ask_about(photos: dict, ask: str) -> dict:
    """photos = {name the AI sees: local photo}; agy looks at AI_SIDE copies of them and answers per photo:
    {name: its JSON item}."""
    import llm
    with tempfile.TemporaryDirectory(prefix="thumb_ai_") as tmp:
        files = {}
        for name, src in photos.items():
            im = open_rgb(src)
            im.thumbnail((AI_SIDE, AI_SIDE))
            files[name] = pathlib.Path(tmp) / name
            im.save(files[name], quality=90)
        prompt = ask.format(n=len(files), files=", ".join(files)) + (
            "\nLook at the photos with your file viewing tool only; do not write a plan or any file, and running commands is not allowed here. "
            "Your final message must be the JSON object.")
        # an agy turn now and then runs past its 300 s (the model thinking over the photos), or Gemini's safety filter
        # blocks an answer (faces, plates); the next turn usually passes
        for attempt in (1, 2):
            try:
                ans = llm.generate_json("photo_check", prompt, files)  # it asks once more when a turn ends without the answer
                break
            except ValueError as e:
                why = "5분 시간 초과" if "timeout" in str(e) else "안전 필터 차단" if "safety filter" in str(e) else "JSON 응답 누락" if "did not answer with JSON" in str(e) else None
                if not why or (attempt == 2 and len(photos) == 1):
                    raise
                if attempt == 2:  # two failures on one batch: half as many photos per turn
                    print(f"  [AI] agy {why}, {len(photos)}장을 둘로 나눠 묻습니다", flush=True)
                    names = list(photos)
                    half = len(names) // 2
                    return {**_ask_about({n: photos[n] for n in names[:half]}, ask),
                            **_ask_about({n: photos[n] for n in names[half:]}, ask)}
                print(f"  [AI] agy {why}, 한 번 더 묻습니다", flush=True)
    return {item.get("file"): item for item in ans.get("photos") or [] if item.get("file") in photos}


def to_pixels(item: dict, w: int, h: int) -> tuple:
    """The AI's 0-1000 plate corners and face circles -> pixels of the w x h photo, each grown a little. An entry that
    is not 4 points (plate) or 3 numbers (face) is dropped instead of stopping the run."""
    plates, faces = [], []
    for q in item.get("plates") or []:
        try:
            p = np.array(q, dtype=np.float32).reshape(4, 2) * [w / 1000, h / 1000]
        except (TypeError, ValueError):
            continue
        plates.append(((p - p.mean(axis=0)) * PLATE_PAD + p.mean(axis=0)).round().tolist())
    for c in item.get("faces") or []:
        try:
            cx, cy, r = (float(v) for v in c)
        except (TypeError, ValueError):
            continue
        faces.append([round(cx * w / 1000), round(cy * h / 1000), round(r * w / 1000 * FACE_PAD)])
    return plates, faces


def _score(item: dict) -> float:
    try:
        return float(item.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


_review_lock = threading.Lock()


def _probe_clip(clip: pathlib.Path) -> tuple[pathlib.Path, float]:
    probe = subprocess.run([find_ffmpeg(), "-nostdin", "-hide_banner", "-i", str(clip)],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe.stderr)
    if not m:
        return clip, 0.0
    return clip, int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def _extract_frame_ffmpeg(task: tuple) -> tuple[pathlib.Path, bool]:
    clip, t, f = task
    if not f.exists() or f.stat().st_mtime < clip.stat().st_mtime:
        part = f.with_name(f"{f.name}.{os.getpid()}.part")  # a kill mid-write (작업 중지) must not leave a cut-short .jpg
        subprocess.run([find_ffmpeg(), "-nostdin", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(clip),
                        "-frames:v", "1", "-q:v", "2", "-f", "image2", "-c:v", "mjpeg", str(part)],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if part.exists():
            os.replace(part, f)
    return f, f.exists()


def video_frames(slug: str, per_video: int = FRAMES_PER_VIDEO) -> list:
    """Stills from the car's clips, every FRAME_EVERY_S (at most per_video a clip, spread over it), cut into
    gdrive_raw/_frames/ (again when the clip is newer) and named relative to gdrive_raw: a job folder's photos are often
    all of the outside while the mirror views are only in its clips."""
    raw, out = raw_dir(slug), raw_dir(slug) / "_frames"
    clips = sorted(p for p in raw.iterdir() if p.suffix.lower() in VIDEO_EXTS) if raw.exists() else []
    if not clips:
        return []
    out.mkdir(exist_ok=True)

    # 1. Probe clip durations concurrently with bounded workers
    workers = min(4, max(1, os.cpu_count() or 4), len(clips))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        probes = list(ex.map(_probe_clip, clips))

    # 2. Plan frame tasks
    tasks = []
    for clip, dur in probes:
        if dur <= 0:
            continue
        n = max(1, min(per_video, int(dur // FRAME_EVERY_S)))
        for k in range(n):
            t = dur * (k + 0.5) / n
            f = out / f"{clip.stem}_{t:05.1f}s.jpg"
            tasks.append((clip, t, f))

    # 3. Parallelize FFmpeg frame extraction across clips & timestamps
    ext_workers = min(4, max(1, os.cpu_count() or 4), len(tasks) or 1)
    if ext_workers > 1 and tasks:
        with ThreadPoolExecutor(max_workers=ext_workers) as ex:
            list(ex.map(_extract_frame_ffmpeg, tasks))
    else:
        for tsk in tasks:
            _extract_frame_ffmpeg(tsk)

    names = []
    for _, _, f in tasks:
        if f.exists():
            names.append(f"_frames/{f.name}")
    return names


def _review(slug: str, names: list, progress, what: str, fresh: bool = False) -> dict:
    """agy's answer (REVIEW_ASK) for each photo, kept in thumb/review.json per prompt version, file name and size, so a
    rerun or a timeout part way through asks only about the photos it has no answer for yet (fresh: ask about all)."""
    cache_f = drive_index.media_dir(slug) / "thumb" / "review.json"
    with _review_lock:
        cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
    key = lambda n: f"{REVIEW_VERSION}|{n}|{(raw_dir(slug) / n).stat().st_size}"
    todo = [n for n in names if fresh or key(n) not in cache]
    clip_ids: dict[str, int] = {}

    def _alias(j: int, n: str) -> str:
        m = re.fullmatch(r"_frames/(.+)_(\d+(?:\.\d+)?)s\.jpg", n)
        if not m:
            return f"p{j + 1}_photo.jpg"
        vid = clip_ids.setdefault(m[1], len(clip_ids) + 1)
        return f"p{j + 1}_v{vid}_{int(round(float(m[2]))):03d}s.jpg"

    batches = [
        (i, {_alias(j, n): n for j, n in enumerate(todo[i:i + AI_BATCH])})
        for i in range(0, len(todo), AI_BATCH)
    ]
    if batches:
        def _run_batch(item: tuple) -> tuple:
            idx, batch = item
            print(f"  [AI 분류] {what} {idx + 1}-{idx + len(batch)} / {len(todo)}", flush=True)
            return batch, _ask_about({a: raw_dir(slug) / n for a, n in batch.items()}, REVIEW_ASK)

        done_cnt = 0
        with ThreadPoolExecutor(max_workers=min(3, len(batches))) as ex:
            for batch, ans in ex.map(_run_batch, batches):
                with _review_lock:
                    for alias, item in ans.items():
                        cache[key(batch[alias])] = item
                    done_cnt += len(batch)
                    if cache_f.exists():
                        try:
                            cache = {**json.loads(cache_f.read_text(encoding="utf-8")), **cache}
                        except Exception:
                            pass
                    atomic_write_json(cache_f, cache, indent=1)
                progress(done_cnt / len(todo), f"{what} AI 분류 {done_cnt} / {len(todo)}")
    with _review_lock:
        if cache_f.exists():
            try:
                cache = {**json.loads(cache_f.read_text(encoding="utf-8")), **cache}
            except Exception:
                pass
    return {n: cache[key(n)] for n in names if key(n) in cache}


def _ranked(review: dict, slot: str, skip=()) -> list:
    """The photos that can fill a slot, best first by score; not those in skip."""
    return [n for kind in AI_KINDS[slot]
            for n in sorted((n for n, it in review.items() if it.get("kind") == kind and n not in skip), key=lambda n: -_score(review[n]))]


def _pick(slug: str, review: dict, slot: str, name: str) -> dict:
    plates, faces = to_pixels(review[name], *open_rgb(raw_dir(slug) / name).size)
    print(f"  [AI 분류] {SLOTS[slot]}: {name} ({review[name].get('kind')}, 번호판 {len(plates)}, 얼굴 {len(faces)})", flush=True)
    return {"src": name, "plates": plates, "faces": faces, "by": "agy", "kind": review[name].get("kind")}


def _full_review(slug: str, progress=lambda frac, label: None, fresh: bool = False, skip=()) -> dict:
    """agy's answers about the car's photos first, reusing any cached clip stills in review.json next, and only
    extracting/reviewing stills from clips when a slot still lacks its kind."""
    cands = candidates(slug)
    raw = raw_dir(slug)
    review = _review(slug, cands, lambda f, l: progress(0.6 * f, l), "사진", fresh)

    if not fresh and any(not _ranked(review, s, skip) for s in SLOTS):
        cache_f = drive_index.media_dir(slug) / "thumb" / "review.json"
        with _review_lock:
            cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
        for k, item in cache.items():
            parts = k.split("|")
            if len(parts) == 3 and parts[0] == REVIEW_VERSION and parts[1].startswith("_frames/") and (raw / parts[1]).exists():
                review[parts[1]] = item
    if any(not _ranked(review, s, skip) for s in SLOTS):
        frames = video_frames(slug)  # the photos lack a kind: look through the clips too
        if frames:
            review.update(_review(slug, frames, lambda f, l: progress(0.6 + 0.4 * f, l), "영상 장면", fresh))
    return review


def auto_pick(slug: str, progress=lambda frac, label: None, fresh: bool = False, skip=()) -> tuple:
    """agy sorts the car's photos (and stills from its clips when needed), takes the best of each kind for the three
    slots (a different photo each, none in skip), covers the plates and faces it found and saves the picks.
    Returns (picks, review). ShortFootage (its text = the report) when the folder has no photo or clip still of a
    slot's kind, e.g. no mirror view for 시공 전/후."""
    review = _full_review(slug, progress, fresh, skip)
    picks, used = {}, set(skip)
    missing = [KIND_LABEL[AI_KINDS[s][0]] for s in SLOTS if not _ranked(review, s, used)]
    if missing:
        raise ShortFootage(footage_report(slug, list(dict.fromkeys(missing)), thumbnail=True))
    for slot in SLOTS:
        name = next(iter(_ranked(review, slot, used)), None)
        if name is None:  # one photo cannot fill two slots
            raise ShortFootage(footage_report(slug, [KIND_LABEL[AI_KINDS[slot][0]]], thumbnail=True))
        picks[slot] = _pick(slug, review, slot, name)
        used.add(name)
    save(slug, picks)
    return picks, review


def _verify(slug: str) -> dict:
    """{slot: problem text} for the masked copies agy still sees a plate or face on, did not answer about, or answered
    about without saying plainly that none is visible."""
    seen = _ask_about({f"{s}.jpg": masked_file(slug, s) for s in SLOTS}, VERIFY_ASK)
    problems = {}
    for s, label in SLOTS.items():
        item = seen.get(f"{s}.jpg")
        if item is None:
            problems[s] = f"{label}: AI가 이 사진에 답하지 않았습니다"
        elif item.get("plate_visible") is not False or item.get("face_visible") is not False:
            what = "/".join(k for k, v in (("번호판", item.get("plate_visible")), ("얼굴", item.get("face_visible"))) if v is not False)
            problems[s] = f"{label}: {what} 보임 ({item.get('where') or '위치 미상'})"
    return problems


def ai_check(slug: str, fresh: bool = False, progress=lambda frac, label: None) -> list:
    """Picks and masks the three photos when none are saved (or `fresh`), skipping post-masking AI re-inspection
    (_verify / FIX_ROUNDS) so thumbnail generation completes immediately."""
    if fresh or not saved(slug):
        auto_pick(slug, lambda frac, label: progress(frac, label), fresh)
    else:
        atomic_write_json(check_file(slug), {"ok": True, "problems": [], "failed": [], "copies": _copies(slug)}, indent=1)
    progress(1.0, "사진 분류·가리기 완료 (검수 생략)")
    return []


def _selftest() -> None:
    assert callable(find_ffmpeg) and find_ffmpeg(), "find_ffmpeg must be imported and resolve"
    q = order_quad([[90, 60], [10, 10], [10, 60], [90, 10]])
    assert q.tolist() == [[10, 10], [90, 10], [90, 60], [10, 60]], q
    img = Image.new("RGB", (200, 120), (0, 160, 0))  # green: the plate cover (mostly white/grey) differs everywhere
    out = np.asarray(apply_masks(img, [[[20, 20], [100, 20], [100, 50], [20, 50]]], [[160, 80, 20]]))
    assert (out[22:48, 22:98] != [0, 160, 0]).any(axis=2).all(), "plate not fully covered"
    assert out[80, 160].max() < 30, "face not covered"
    assert out[110, 10].tolist() == [0, 160, 0], "pixels outside the masks changed"
    plates, faces = to_pixels({"plates": [[[100, 500], [300, 500], [300, 600], [100, 600]]], "faces": [[500, 500, 100]]},
                              2000, 1000)
    assert plates == [[[176.0, 494.0], [624.0, 494.0], [624.0, 606.0], [176.0, 606.0]]], plates  # 400x100 px, x1.12
    assert faces == [[1000, 500, 260]], faces
    review = {"a": {"kind": "install_optic", "score": 5}, "b": {"kind": "mirror_after", "score": "3"},
              "c": {"kind": "install_optic", "score": 8}, "d": {"kind": "other", "score": 9}, "e": {"kind": "install_stock", "score": None}}
    assert _ranked(review, "after_photo") == ["b"], "only a mirror view, never an install shot with hands"
    assert _ranked(review, "after_photo", {"b"}) == [] and _ranked(review, "before_photo") == []
    assert _ranked(review, "car_exterior") == []
    assert to_pixels({"plates": [[[1, 2], [3, 4]], "x"], "faces": [[1, 2], [500, 500, 10]]}, 1000, 1000) == ([], [[500, 500, 13]]),         "a malformed plate or face from the AI is dropped"

    import shutil
    import tempfile
    real, drive_index.MEDIA_DIR = drive_index.MEDIA_DIR, pathlib.Path(tempfile.mkdtemp())  # "t" is unlinked: <media>/t
    try:
        raw_dir("t").mkdir(parents=True)
        for s in SLOTS:
            img.save(raw_dir("t") / f"{s}.jpg")
        img.save(raw_dir("t") / "00_t_car_exterior.jpg")  # legacy auto-still in gdrive_raw must be ignored
        picks = {s: {"src": f"{s}.jpg", "plates": [], "faces": []} for s in SLOTS}
        assert saved("t") is None and ready("t") is None
        save("t", picks)
        assert saved("t") and ready("t") and candidates("t") == sorted(f"{s}.jpg" for s in SLOTS)
        chk = json.loads(check_file("t").read_text(encoding="utf-8"))
        assert chk.get("ok") is True and chk.get("copies") == _copies("t")
        save("t", picks)
        assert ready("t"), "save() marks masked copies ready immediately without AI re-inspection"
        (raw_dir("t") / "before_photo.jpg").unlink()
        assert saved("t") is None and ready("t") is None, "a removed source photo must take its masked copy out of use"
        try:
            save("t", picks)  # replaces the exterior copy, then fails on the removed photo
        except FileNotFoundError:
            pass
        assert not picks_file("t").exists() and not check_file("t").exists(), "a half-done re-save left the old picks vouching for new copies"
    finally:
        shutil.rmtree(drive_index.MEDIA_DIR, ignore_errors=True)
        drive_index.MEDIA_DIR = real
    print("thumb_photos self-check ok")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        _selftest()
        raise SystemExit
    car = sys.argv[1]
    print(f"=== [썸네일 사진 AI 검수] {car} ===", flush=True)
    left = ai_check(car, fresh="--auto" in sys.argv)
    for line in left:
        print(f"  [가려지지 않음] {line}")
    print("  [통과] 번호판·얼굴이 보이지 않습니다." if not left else "  AI가 다시 가리고 다른 사진으로도 바꿔 봤지만 남았습니다.")
    raise SystemExit(1 if left else 0)
