"""Writes scenarios/<slug>_longform.json for a car that has no longform scenario, so build_longform.py builds it with
no one editing JSON. The edit is 「옵틱글래스 광각미러 템플릿 1」 (templates/opticglass_wide1/skeleton.json, 57.7 s, the
channel's own longform length: exterior cuts, the 「광각미러가 꼭 필요한 이유」 card, 시공 전 and 시공 후 mirror shots, two
50:50 splits, the outro; no transitions). It keeps the skeleton's scene timing, lines and template; only the car title
and what fills each scene change. The hand-made 80 s scenarios (cybertruck, santafe, ...) stay as they are.

What fills a scene comes from this car's own media first: agy (thumb_photos' review) sorts stills cut from its video
clips (`.MOV`/`.mp4`, prioritized first) and standalone Drive photos (`.jpg`/`.png`, automatic fallback when video clips
lack fresh moments for a role) into exterior / stock mirror / OpticGlass mirror / install shots and boxes the mirror,
and each scene takes the best still of its kind that no other scene took. For before/after comparing scenes
(`compare_before`, `compare_after`, `split` across templates including `opticglass_wide1`), normal target-vehicle
selection is preserved whenever this car's own index has an appropriate reference; only when this car's index lacks
an appropriate `mirror_before` or `mirror_after` reference does it fall back to appropriate before/after photos in
another vehicle's index (`@media/...`) without extra donor-vehicle constraints. Every scene is then cut once without
covers and agy marks the plates, faces and the mirror on stills about half a second apart; they become the scene's
plate keyframes, face tracks and the 4 arrows on its 시공 후 shots. A car whose videos and same-vehicle photos
together still lack required non-comparing shots (or whose comparing shots lack both target and donor references)
raises ShortFootage (recorded in media/<car>/scenario_short.json for the GUI) instead of using AI-generated footage.

A variant other than "longform" follows its template's skeleton (SKELETONS) into scenarios/<slug>_<variant>.json, built
as its own draft (build_longform.py <slug> --variant wide1): wide1 gives a hand-made 80 s car its 57.7 s edit; for a car
whose longform was generated it is a copy of that longform (no agy call).

usage: py make_scenario.py <slug> [--variant wide1] [--force]   (--force writes over an existing scenario)
       py make_scenario.py <slug> --add-arrows                  a person's scenario: add the missing 4 arrows only
       py make_scenario.py                                      self-check (no agy call)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import re
import shutil
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

import cv2
from PIL import Image

import drive_index
import longform_common as lc
import preflight_check
import thumb_photos as tp

WIDE1 = lc.SCENARIOS_DIR / "templates" / "opticglass_wide1" / "skeleton.json"
SKELETONS = {"longform": WIDE1, "wide1": WIDE1}  # variant -> the skeleton its scenarios copy (timing, lines, template)
COMPARE_ROLES = {"compare_before", "compare_after", "split"}
COMPARE_KINDS = ("mirror_before", "mirror_after")
# Each skeleton scene's role (longform_common.ROLES) says which shot kinds may fill it and which rules it keeps (arrows
# on the OpticGlass mirror, no transitions around the comparison); a split takes a stock and an OpticGlass mirror view.
ShortFootage = tp.ShortFootage
FRAMES_PER_VIDEO = tp.FRAMES_PER_VIDEO  # shared with thumb_photos so Stage 2 and Stage 3 reuse _frames/ and thumb/review.json
KEY_EVERY_S = 0.5  # seconds between the stills agy marks plates/faces on (a face passing quicker can be missed)
EDGE_GROW = 1.5  # a face's circle on the still before/after its sightings, where it may have moved
MAX_SLOW = 2.5  # slowest playback a clip shorter than its scene is stretched to
REUSE_GAP_S = 3.0  # two scenes may use one clip when their moments are this far apart
PLATE_MIN_SHARE = 0.6  # a plate seen on fewer of a scene's stills than this is covered by circles, not the plate cover
PANEL_ASPECT = 960 / 1080
MAX_FACE_R = 0.45 * 1920  # px: a face circle wider than 90% of the frame is not a face (covers)
MAX_PLATE_SHARE = 0.5  # a "plate" over half the frame is a misread badge or lettering close-up (covers)
AGY_WORKERS = 3

MASK_ASK = """This folder holds {n} stills ({files}) from a car video about to be published on YouTube. Open and look at
every one closely, including small background areas and reflections in mirrors, windows and paint. Answer with only a
JSON object:
{{"photos": [{{"file": "k1.jpg", "plates": [[[x, y], [x, y], [x, y], [x, y]]], "faces": [[cx, cy, r]], "mirror": [x0, y0, x1, y1]}}]}}
- plates: the 4 corners of every licence plate, readable or not, also on other cars and in reflections (an
  orange-and-white "Optic-Glass" plate cover is not a plate).
- faces: a circle over every human face or head, also partly cut off, small, in the background, or reflected.
- mirror: the box around the whole side mirror (housing and glass) the shot is about; on a still split into a left and
  a right half, the one in the right half. [] when no side mirror is seen.
- Coordinates are 0-1000: x as a fraction of the still's width, y of its height; r as a fraction of the width.
  Empty lists when there is none."""
MASK_VERSION = hashlib.sha1(MASK_ASK.encode()).hexdigest()[:8]  # answers to an older prompt are asked again


def scenario_path(slug: str, variant: str = "longform"):
    return lc.SCENARIOS_DIR / f"{slug}_{variant}.json"


def short_file(slug: str):
    return drive_index.media_dir(slug) / "scenario_short.json"


# --- picking the footage ----------------------------------------------------------------------------------------------
def stills(slug: str, review: dict) -> list:
    """The sorted stills of the car's clips and standalone Drive photos: {src, t, len, kind, score, box, size, photo}."""
    raw, out, lens = tp.raw_dir(slug), [], {}
    clips = {p.stem: p.name for p in raw.iterdir() if p.suffix.lower() in tp.VIDEO_EXTS} if raw.exists() else {}
    photos = set(tp.candidates(slug))
    for name, item in review.items():
        m = re.fullmatch(r"_frames/(.+)_(\d+\.\d)s\.jpg", name)
        if m and m[1] in clips:
            src = clips[m[1]]
            if src not in lens:
                lens[src] = lc.get_mov_meta_cached(raw / src)[0] / 1e6
            w, h = Image.open(raw / name).size
            b = item.get("mirror") or []
            box = [b[0] * w / 1000, b[1] * h / 1000, b[2] * w / 1000, b[3] * h / 1000] if len(b) == 4 else None
            out.append({"src": src, "t": float(m[2]), "len": lens[src], "kind": item.get("kind"), "score": tp._score(item),
                        "box": box, "size": (w, h), "photo": False})
        elif name in photos and (raw / name).exists():
            w, h = tp.open_rgb(raw / name).size
            b = item.get("mirror") or []
            box = [b[0] * w / 1000, b[1] * h / 1000, b[2] * w / 1000, b[3] * h / 1000] if len(b) == 4 else None
            out.append({"src": name, "t": 0.0, "len": math.inf, "kind": item.get("kind"), "score": tp._score(item),
                        "box": box, "size": (w, h), "photo": True})
    return out


def pick(cands: list, kinds: list, used: list, dur: float):
    """The best candidate of kinds for a dur-second scene: unused video clip moments first (at least REUSE_GAP_S from
    taken moments), then unused standalone Drive photos when video clips lack fresh moments for that role, then reused
    video moments (furthest gap) or photos, by kind order, usage count and score. None when there is none."""
    pool = [c for c in cands if c["kind"] in kinds and (c.get("photo") or c["len"] - 0.1 >= dur / MAX_SLOW)]
    gap = lambda c: min((abs(u["t"] - c["t"]) for u in used if u["src"] == c["src"]), default=math.inf)

    def _key(c: dict) -> tuple:
        is_photo = bool(c.get("photo"))
        reused = any(u["src"] == c["src"] for u in used) if is_photo else (gap(c) < REUSE_GAP_S)
        return (reused, is_photo, kinds.index(c["kind"]), 0.0 if is_photo else -min(gap(c), REUSE_GAP_S),
                sum(u["src"] == c["src"] for u in used), -c["score"])

    return min(pool, key=_key, default=None)


def timing(c: dict, dur: float) -> tuple:
    """(in-point, speed) centring the scene on the still's moment; a clip shorter than the scene plays slower."""
    if c.get("photo"):
        return 0.0, 1.0
    speed = 1.0 if c["len"] - 0.1 >= dur else round(dur / (c["len"] - 0.1), 3)
    need = dur / speed
    return round(min(max(0.0, c["t"] - need / 2), max(0.0, c["len"] - need - 0.05)), 2), speed


def panel_crop(box, size) -> str:
    """A 960x1080 (8:9) crop of the frame around the mirror with a margin, kept inside the frame (the whole frame's
    middle when agy found no mirror); a mirror wider than that keeps the frame's width (the panel pads it)."""
    W, H = size
    if box:
        x0, y0, x1, y1 = box
        w, h, cx, cy = (x1 - x0) * 1.7, (y1 - y0) * 1.7, (x0 + x1) / 2, (y0 + y1) / 2
    else:
        w, h, cx, cy = W, H, W / 2, H / 2
    w, h = (w, w / PANEL_ASPECT) if w / max(h, 1) > PANEL_ASPECT else (h * PANEL_ASPECT, h)
    if w > W:
        w, h = W, min(H, W / PANEL_ASPECT)
    if h > H:
        w, h = min(W, H * PANEL_ASPECT), H
    w, h = int(w) // 2 * 2, int(h) // 2 * 2
    x, y = min(max(0, cx - w / 2), W - w), min(max(0, cy - h / 2), H - h)
    return f"crop={w}:{h}:{int(x) // 2 * 2}:{int(y) // 2 * 2}"


def _box_to_1080p(box, size, crop_str: str = "", split_right: bool = False):
    """Maps a candidate still's mirror box [x0, y0, x1, y1] into rendered 1920x1080 scene coordinates."""
    if not box or len(box) != 4:
        return None
    W, H = size
    x0, y0, x1, y1 = (float(v) for v in box)
    m = re.search(r"crop=(\d+):(\d+):(\d+):(\d+)", crop_str or "")
    if m:
        cw, ch, cx, cy = map(int, m.groups())
        x0, y0, x1, y1 = x0 - cx, y0 - cy, x1 - cx, y1 - cy
        W, H = cw, ch
    pw, ph = (960, 1080) if split_right else (1920, 1080)
    s = min(pw / max(W, 1), ph / max(H, 1))
    ox = (960 if split_right else 0) + (pw - W * s) / 2
    oy = (ph - H * s) / 2
    return [ox + x0 * s, oy + y0 * s, ox + x1 * s, oy + y1 * s]


def donor_stills(exclude_slug: str) -> list:
    """Standalone mirror_before / mirror_after photos from other vehicles' review.json indexes (no extra donor-vehicle
    constraints), encoded as portable `@media/<rel>/gdrive_raw/<name>` sources."""
    media_root = drive_index.MEDIA_DIR.resolve()
    exclude_dir = drive_index.media_dir(exclude_slug).resolve()
    candidate_dirs = []
    for slug in sorted(drive_index.links()):
        if slug != exclude_slug:
            candidate_dirs.append(drive_index.media_dir(slug))
    if media_root.exists():
        for entry in sorted(media_root.iterdir(), key=lambda p: p.name):
            if not entry.is_dir():
                continue
            if (entry / "thumb" / "review.json").exists() and (entry / "gdrive_raw").exists():
                candidate_dirs.append(entry)
            for sub in sorted(entry.iterdir(), key=lambda p: p.name):
                if sub.is_dir() and (sub / "thumb" / "review.json").exists() and (sub / "gdrive_raw").exists():
                    candidate_dirs.append(sub)
    seen, out = set(), []
    for d in candidate_dirs:
        try:
            d_res = d.resolve()
        except OSError:
            continue
        if d_res == exclude_dir or d_res in seen:
            continue
        seen.add(d_res)
        review_f, raw = d_res / "thumb" / "review.json", d_res / "gdrive_raw"
        if not review_f.exists() or not raw.exists():
            continue
        try:
            donor_rel = d_res.relative_to(media_root).as_posix()
        except ValueError:
            continue
        try:
            review_data = json.loads(review_f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for key, item in sorted(review_data.items()):
            parts = key.split("|", 2)
            if len(parts) != 3 or parts[0] != tp.REVIEW_VERSION:
                continue
            name = parts[1]
            if (name.startswith("_frames/") or pathlib.Path(name).suffix.lower() not in tp.PHOTO_EXTS
                    or tp._AUTO_STILL_RE.match(name)
                    or any(b.lower() in name.lower() for b in preflight_check.AI_SLOP_BLOCKLIST)):
                continue
            kind = item.get("kind")
            if kind not in COMPARE_KINDS:
                continue
            img_path = raw / name
            if not img_path.is_file():
                continue
            try:
                w, h = tp.open_rgb(img_path).size
            except Exception:
                continue
            b = item.get("mirror") or []
            box = [b[0] * w / 1000, b[1] * h / 1000, b[2] * w / 1000, b[3] * h / 1000] if len(b) == 4 else None
            out.append({
                "src": f"{lc.MEDIA_SRC_PREFIX}{donor_rel}/gdrive_raw/{name}",
                "t": 0.0,
                "len": math.inf,
                "kind": kind,
                "score": tp._score(item),
                "box": box,
                "size": (w, h),
                "photo": True,
            })
    return out


def plan(slug: str, review: dict, skeleton: dict) -> list:
    """The skeleton's scenes, each filled from this car's stills of a kind its role takes (no plates/faces/arrows yet).
    Comparing roles (COMPARE_ROLES) preserve target-vehicle selection when available and fall back to donor_stills(slug)
    only when the target vehicle lacks an appropriate mirror_before/mirror_after reference. ShortFootage, whose text is
    the report shown to the user, when required shots are still missing."""
    cands = stills(slug, review)
    _donors = None

    def _get_donors() -> list:
        nonlocal _donors
        if _donors is None:
            _donors = donor_stills(slug)
        return _donors

    def _pick_for_role(role: str, kinds: list, used: list, dur: float):
        hit = pick(cands, kinds, used, dur)
        if hit is not None or role not in COMPARE_ROLES:
            return hit
        return pick(_get_donors(), kinds, used, dur)

    needs = [
        (sk["role"], [k])
        for sk in skeleton["scenes"]
        if sk["role"] == "split"
        for k in lc.ROLES["split"]["kinds"]
    ] + [
        (sk["role"], lc.ROLES[sk["role"]]["kinds"])
        for sk in skeleton["scenes"]
        if sk["role"] not in ("split", "outro")
    ]
    missing = list(dict.fromkeys(
        tp.KIND_LABEL[k[0]]
        for r, k in needs
        if not any(c["kind"] in k for c in cands)
        and (r not in COMPARE_ROLES or not any(d["kind"] in k for d in _get_donors()))
    ))
    if missing:
        raise ShortFootage(tp.footage_report(slug, missing))
    used, scenes = [], []
    for sk in skeleton["scenes"]:
        sid, dur, role = sk["id"], sk["dur"], sk["role"]
        base = {"id": sid, "role": role, "start": sk["start"], "dur": dur}
        if role == "outro":
            scenes.append({**base, "name": sk["name"], "src": "outro", "in": 0.0, "look": sk.get("look", "plain")})
            continue
        if role == "split":
            b = _pick_for_role(role, ["mirror_before"], used, dur)
            a = _pick_for_role(role, ["mirror_after"], used, dur)
            if not (b and a):
                raise ShortFootage(tp.footage_report(slug, [tp.KIND_LABEL["mirror_before" if not b else "mirror_after"]],
                                                     f" ({dur / MAX_SLOW:.1f}초 이상)"))
            used += [b, a]
            (in_b, sp_b), (in_a, sp_a) = timing(b, dur), timing(a, dur)
            pts = lambda s: f"setpts={s}*PTS," if s != 1.0 else ""
            crop_a = panel_crop(a["box"], a["size"])
            split = {"in_after": in_a, "crop_before": pts(sp_b) + panel_crop(b["box"], b["size"]),
                     "crop_after": pts(sp_a) + crop_a}
            if a["src"] != b["src"]:
                split = {"src_after": a["src"], **split}
            sc = {**base, "name": f"{sid}_split", "kind": [b["kind"], a["kind"]], "src": b["src"], "in": in_b, "split": split}
            if a.get("box"):
                sc["_fallback_box"] = _box_to_1080p(a["box"], a["size"], crop_a, split_right=True)
            scenes.append(sc)
            continue
        kinds = lc.ROLES[role]["kinds"]
        c = _pick_for_role(role, kinds, used, dur)
        if not c:
            raise ShortFootage(tp.footage_report(slug, [tp.KIND_LABEL[kinds[0]]], f" ({dur / MAX_SLOW:.1f}초 이상)"))
        used.append(c)
        in_, speed = timing(c, dur)
        sc = {**base, "name": f"{sid}_{c['kind']}", "kind": c["kind"], "src": c["src"], "in": in_, "look": sk.get("look", "bright")}
        if speed != 1.0:
            sc["speed"] = speed
        if lc.ROLES[role].get("arrows") and c.get("box"):
            sc["_fallback_box"] = _box_to_1080p(c["box"], c["size"])
        scenes.append(sc)
    return scenes


# --- covers and arrows ------------------------------------------------------------------------------------------------
def face_tracks(fracs: list, per_key: list) -> list:
    """Circles found on the stills at fracs (per_key[j] = [(cx, cy, r)]) chained into tracks the builder moves between
    stills: a circle continues the track of a near circle on the previous still. Each track covers from the still before
    its first sighting to the still after its last one (EDGE_GROW larger there), so a face that moves in between stays
    covered."""
    tracks = []
    for j, circles in enumerate(per_key):
        open_ = [t for t in tracks if t[-1][0] == j - 1]
        for cx, cy, r in circles:
            t = next((t for t in open_ if math.hypot(t[-1][1] - cx, t[-1][2] - cy) < 3 * max(t[-1][3], r)), None)
            if t:
                open_.remove(t)
                t.append((j, cx, cy, r))
            else:
                tracks.append([(j, cx, cy, r)])
    out, last = [], len(fracs) - 1
    for t in tracks:
        pts = [[fracs[j], cx, cy, r] for j, cx, cy, r in t]
        (j0, *first), (j1, *end) = t[0], t[-1]
        if j0 > 0:
            pts = [[round(fracs[j0 - 1] - 0.001, 4), *first[:2], 0], [fracs[j0 - 1], *first[:2], round(first[2] * EDGE_GROW)]] + pts
        if j1 < last:
            pts += [[fracs[j1 + 1], *end[:2], round(end[2] * EDGE_GROW)], [round(fracs[j1 + 1] + 0.001, 4), *end[:2], 0]]
        out.append(pts)
    return out


def circle_over(quad) -> tuple:
    cx, cy = sum(p[0] for p in quad) / 4, sum(p[1] for p in quad) / 4
    return round(cx), round(cy), round(max(math.hypot(p[0] - cx, p[1] - cy) for p in quad) * 1.15)


def arrows_for(box, split: bool) -> list:
    """4 arrows straddling the mirror's left, right, top and bottom edges, pointing out, kept inside the frame (the
    시공 후 half on a split)."""
    L = 110 if split else 125
    lo_x = 960 if split else 0
    x0, y0, x1, y1 = box or ((1210, 300, 1670, 780) if split else (560, 240, 1360, 840))
    clamp = lambda v, lo, hi: round(min(max(v, lo + L * 0.8), hi - L * 0.8))
    cx, cy = clamp((x0 + x1) / 2, lo_x, 1920), clamp((y0 + y1) / 2, 0, 1080)
    return [[clamp(x0, lo_x, 1920), cy, -1.0, 0.0, L], [clamp(x1, lo_x, 1920), cy, 1.0, 0.0, L],
            [cx, clamp(y0, 0, 1080), 0.0, -1.0, L], [cx, clamp(y1, 0, 1080), 0.0, 1.0, L]]


def _centre(q) -> tuple:
    return sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4


def plate_track(plates_k: list) -> tuple:
    """({still: quad} of the one plate the cover follows, the other plates per still): the largest plate of the first
    still with one, then on each still the plate nearest the last one taken; a plate further than 1.5 of that plate's
    width is another plate, so the cover never slides from one plate to another."""
    track, rest, prev = {}, [], None
    for j, plates in enumerate(plates_k):
        near = None
        if plates and prev is None:
            near = max(plates, key=lambda q: cv2.contourArea(lc.np.array(q, dtype=lc.np.float32)))
        elif plates:
            (px, py), width = _centre(prev), max(p[0] for p in prev) - min(p[0] for p in prev)
            near = min(plates, key=lambda q: math.hypot(_centre(q)[0] - px, _centre(q)[1] - py))
            if math.hypot(_centre(near)[0] - px, _centre(near)[1] - py) > 1.5 * max(width, 40):
                near = None
        if near is not None:
            track[j], prev = near, near
        rest.append([q for q in plates if q is not near])
    return track, rest


def covers(fracs: list, answers: list, split: bool, arrows: bool, fallback_box=None) -> dict:
    """The scene's plates / faces / arrows from agy's answers on its stills (1920x1080 pixels)."""
    plates_k, circles_k, boxes = [], [], []
    for item in answers:
        plates, faces = tp.to_pixels(item, 1920, 1080)
        # A "plate" over half the frame or a "face" as wide as it is agy misreading a close-up (seen 11-09: a RECHARGE
        # TWIN badge filling the frame read as a plate); its cover would black out the whole shot, so it is left out
        # (a real plate or face that size leaves nothing else to show anyway).
        area = lambda q: cv2.contourArea(lc.np.array(q, dtype=lc.np.float32))
        huge = [q for q in plates if area(q) > MAX_PLATE_SHARE * 1920 * 1080] + [f for f in faces if f[2] > MAX_FACE_R]
        if huge:
            print(f"  [AI 가림] 화면을 덮는 번호판/얼굴 {len(huge)}개는 클로즈업 오인으로 보고 뺍니다", flush=True)
        plates_k.append([[[round(float(v)) for v in p] for p in tp.order_quad(q)] for q in plates if area(q) <= MAX_PLATE_SHARE * 1920 * 1080])  # TL, TR, BR, BL
        circles_k.append([tuple(f) for f in faces if f[2] <= MAX_FACE_R])
        b = item.get("mirror") or []
        boxes.append([b[0] * 1.92, b[1] * 1.08, b[2] * 1.92, b[3] * 1.08] if len(b) == 4 else None)
    out = {}
    track, rest = plate_track(plates_k)
    # Perspective homography cover (로고_번호판.png + NCC tracking) for one persistent plate across any scene (including arrow/split)
    if track and len(track) >= PLATE_MIN_SHARE * len(fracs):
        seen = sorted(track)
        out["plates"] = ([[0.0, track[seen[0]]]] if seen[0] else []) + [[fracs[j], track[j]] for j in seen] + (
            [[1.0, track[seen[-1]]]] if seen[-1] < len(fracs) - 1 else [])  # held to both ends, never extrapolated
    else:  # secondary/fleeting plates: circles so no cover floats where no plate is
        rest = plates_k
    for j, extra in enumerate(rest):
        circles_k[j] += [circle_over(q) for q in extra]
    faces = face_tracks(fracs, circles_k)
    if faces:
        out["faces"] = faces
    if arrows:
        mid = sorted((j for j, b in enumerate(boxes) if b), key=lambda j: abs(fracs[j] - 0.5))
        out["arrows"] = arrows_for(boxes[mid[0]] if mid else fallback_box, split)
    return out


def _cut_unmasked(slug: str, sc: dict, out) -> None:
    raw = tp.raw_dir(slug)
    src_p = lc.resolve_scene_src(raw, sc["src"])
    if "split" in sc:
        sp = sc["split"]
        src_after = lc.resolve_scene_src(raw, sp["src_after"]) if sp.get("src_after") else None
        lc.build_split_video_50x50(src_p, sc["in"], sp["in_after"], sc["dur"], sp["crop_before"], sp["crop_after"], [],
                                   out, src_after=src_after)
    else:
        lc.trim_video_16x9(src_p, out, sc["in"], sc["dur"], speed_pts=sc.get("speed", 1.0),
                           crop_expr=sc.get("crop", ""), darken_for_title=sc["look"] == "title")


def _is_static_scene(raw: pathlib.Path, sc: dict) -> bool:
    if not lc._is_image(lc.resolve_scene_src(raw, sc["src"])):
        return False
    after = sc["split"].get("src_after") if "split" in sc else None
    return lc._is_image(lc.resolve_scene_src(raw, after)) if after else True


def _load_review_cache(media_dir: pathlib.Path) -> dict:
    """Loads {name: item} from <media_dir>/thumb/review.json, preferring tp.REVIEW_VERSION."""
    cache_f = media_dir / "thumb" / "review.json"
    if not cache_f.exists():
        return {}
    try:
        raw_cache = json.loads(cache_f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out, versions = {}, {}
    for k, item in raw_cache.items():
        parts = k.split("|", 2)
        if len(parts) < 2 or not isinstance(item, dict):
            continue
        ver, name = parts[0], parts[1]
        if name not in out or (ver == tp.REVIEW_VERSION and versions.get(name) != tp.REVIEW_VERSION):
            out[name] = item
            versions[name] = ver
    return out


def _map_item_to_1080p(item: dict, size: tuple, crop_str: str = "", split_panel: int | None = None) -> dict:
    """Maps a 1st-pass review item (0-1000 of source image `size`) to 0-1000 of the rendered 1920x1080 scene."""
    if not item:
        return {"plates": [], "faces": [], "mirror": []}
    W, H = size
    m = re.search(r"crop=(\d+):(\d+):(\d+):(\d+)", crop_str or "")
    if m:
        eff_w, eff_h, cx, cy = map(int, m.groups())
    else:
        eff_w, eff_h, cx, cy = W, H, 0, 0
    pw, ph = (1920, 1080) if split_panel is None else (960, 1080)
    px_off = 960 if split_panel == 1 else 0
    s = min(pw / max(eff_w, 1), ph / max(eff_h, 1))
    ox = px_off + (pw - eff_w * s) / 2.0
    oy = (ph - eff_h * s) / 2.0

    def _pt(x01, y01) -> tuple[float, float]:
        return ox + (float(x01) * W / 1000.0 - cx) * s, oy + (float(y01) * H / 1000.0 - cy) * s

    def _clamp_x(x: float) -> float:
        return min(max(x, float(px_off)), float(px_off + pw))

    def _clamp_y(y: float) -> float:
        return min(max(y, 0.0), float(ph))

    plates = []
    for q in item.get("plates") or []:
        try:
            pts = [_pt(p[0], p[1]) for p in q]
        except (TypeError, ValueError, IndexError):
            continue
        if len(pts) != 4:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        if max(xs) <= px_off or min(xs) >= px_off + pw or max(ys) <= 0 or min(ys) >= ph:
            continue
        plates.append([[round(_clamp_x(x) * 1000.0 / 1920.0, 2), round(_clamp_y(y) * 1000.0 / 1080.0, 2)] for x, y in pts])

    faces = []
    for c in item.get("faces") or []:
        try:
            cx0, cy0, r0 = (float(v) for v in c)
        except (TypeError, ValueError):
            continue
        fx, fy = _pt(cx0, cy0)
        fr = r0 * W / 1000.0 * s
        if fx + fr <= px_off or fx - fr >= px_off + pw or fy + fr <= 0 or fy - fr >= ph or fr <= 0:
            continue
        faces.append([round(fx * 1000.0 / 1920.0, 2), round(fy * 1000.0 / 1080.0, 2), round(fr * 1000.0 / 1920.0, 2)])

    mirror = []
    b = item.get("mirror") or []
    if len(b) == 4 and (split_panel is None or split_panel == 1):
        try:
            x0, y0 = _pt(b[0], b[1])
            x1, y1 = _pt(b[2], b[3])
            mirror = [round(x0 * 1000.0 / 1920.0, 2), round(y0 * 1000.0 / 1080.0, 2),
                      round(x1 * 1000.0 / 1920.0, 2), round(y1 * 1000.0 / 1080.0, 2)]
        except (TypeError, ValueError):
            mirror = []
    return {"plates": plates, "faces": faces, "mirror": mirror}


def _scene_source_samples(
    raw: pathlib.Path,
    target_review: dict,
    donor_cache: dict,
    src: str,
    in_s: float,
    dur_s: float,
    speed: float = 1.0,
) -> list:
    """Returns [(frac, review_item, (W, H)), ...] over [0.0, 1.0] from 1st-pass review without re-cutting or calling agy."""
    src_p = lc.resolve_scene_src(raw, src)
    if src.startswith(lc.MEDIA_SRC_PREFIX):
        donor_media = src_p.parent.parent
        if donor_media not in donor_cache:
            donor_cache[donor_media] = _load_review_cache(donor_media)
        rev = donor_cache[donor_media]
    else:
        rev = target_review

    if lc._is_image(src_p):
        size = tp.open_rgb(src_p).size
        item = rev.get(src_p.name) or {}
        return [(0.0, item, size), (1.0, item, size)]

    pat = re.compile(r"^_frames/" + re.escape(src_p.stem) + r"_(\d+(?:\.\d+)?)s\.jpg$")
    clip_frames = []
    for name, item in rev.items():
        m = pat.fullmatch(name)
        if m:
            clip_frames.append((float(m[1]), name, item))
    clip_frames.sort(key=lambda x: x[0])

    size = None
    if clip_frames:
        fp = raw / clip_frames[0][1]
        if fp.exists():
            size = Image.open(fp).size
    if size is None:
        size = lc.get_mov_meta_cached(src_p)[1:3]
    if not clip_frames:
        return [(0.0, {}, size), (1.0, {}, size)]

    t0 = float(in_s)
    src_dur = max(float(dur_s) / max(float(speed), 1e-6), 1e-6)
    t1 = t0 + src_dur
    matched = [(t, it) for t, _fn, it in clip_frames if t0 - 0.5 <= t <= t1 + 0.5]
    if not matched:
        nearest = min(clip_frames, key=lambda x: abs(x[0] - (t0 + t1) / 2.0))
        matched = [(nearest[0], nearest[2])]
    if len(matched) == 1:
        return [(0.0, matched[0][1], size), (1.0, matched[0][1], size)]

    by_frac: dict[float, tuple[float, dict]] = {}
    for t, it in matched:
        f = round(min(max((t - t0) / src_dur, 0.0), 1.0), 4)
        target_t = t0 + f * src_dur
        if f not in by_frac or abs(t - target_t) < abs(by_frac[f][0] - target_t):
            by_frac[f] = (t, it)
    pts = sorted((f, it) for f, (_, it) in by_frac.items())
    if pts[0][0] > 0.0:
        pts.insert(0, (0.0, pts[0][1]))
    if pts[-1][0] < 1.0:
        pts.append((1.0, pts[-1][1]))
    if len(pts) == 1:
        return [(0.0, pts[0][1], size), (1.0, pts[0][1], size)]
    return [(f, it, size) for f, it in pts]


def _review_items_for_scene(raw: pathlib.Path, sc: dict, target_review: dict, donor_cache: dict) -> tuple[list, list]:
    """Builds (fracs, mapped_1080p_items) for one scene using only 1st-pass review data."""
    if "split" not in sc:
        samples = _scene_source_samples(
            raw, target_review, donor_cache, sc["src"], sc.get("in", 0.0), sc["dur"], sc.get("speed", 1.0)
        )
        fracs = [f for f, _, _ in samples]
        answers = [_map_item_to_1080p(it, sz, sc.get("crop", ""), split_panel=None) for _, it, sz in samples]
        return fracs, answers

    sp = sc["split"]
    _sp = lambda expr: float(m[1]) if (m := re.search(r"setpts=([\d.]+)\*PTS", expr or "")) else 1.0
    b_samples = _scene_source_samples(
        raw, target_review, donor_cache, sc["src"], sc.get("in", 0.0), sc["dur"], _sp(sp.get("crop_before", ""))
    )
    a_samples = _scene_source_samples(
        raw, target_review, donor_cache, sp.get("src_after") or sc["src"], sp["in_after"], sc["dur"], _sp(sp.get("crop_after", ""))
    )
    fracs = sorted({0.0, 1.0} | {f for f, _, _ in b_samples} | {f for f, _, _ in a_samples})
    nearest = lambda samples, f: min(samples, key=lambda x: abs(x[0] - f))
    answers = []
    for f in fracs:
        _, it_b, sz_b = nearest(b_samples, f)
        _, it_a, sz_a = nearest(a_samples, f)
        mb = _map_item_to_1080p(it_b, sz_b, sp.get("crop_before", ""), split_panel=0)
        ma = _map_item_to_1080p(it_a, sz_a, sp.get("crop_after", ""), split_panel=1)
        answers.append({"plates": mb["plates"] + ma["plates"], "faces": mb["faces"] + ma["faces"], "mirror": ma["mirror"]})
    return fracs, answers


def mark(slug: str, scenes: list, progress, review: dict | None = None) -> None:
    """Applies 1st-pass review (_review) plates, faces, and mirror boxes directly onto rendered 1920x1080 scenes,
    skipping 2nd-pass per-scene frame cutting and agy MASK_ASK inspection."""
    raw = tp.raw_dir(slug)
    target_review = review if review is not None else _load_review_cache(drive_index.media_dir(slug))
    donor_cache: dict[pathlib.Path, dict] = {}
    todo = [sc for sc in scenes if sc["src"] != "outro"]
    total = len(todo) or 1
    for idx, sc in enumerate(todo, 1):
        fracs, per = _review_items_for_scene(raw, sc, target_review, donor_cache)
        fb = sc.pop("_fallback_box", None)
        need_arrows = bool(lc.ROLES[sc["role"]].get("arrows"))
        if need_arrows and not any(len(it.get("mirror") or []) == 4 for it in per) and fb is None:
            print(f"  [화살표 폴백] {sc['id']}: 미러 박스가 없어 기본 미러 영역에 화살표 4개를 배치합니다", flush=True)
        sc.update(covers(fracs, per, "split" in sc, need_arrows, fallback_box=fb))
        progress(idx / total, f"번호판·얼굴·화살표 1차 분류 반영 {idx}/{total}")


def generate(slug: str, progress=lambda frac, label: None, force: bool = False, variant: str = "longform"):
    """Writes scenarios/<slug>_<variant>.json (see the module docstring) and returns its path."""
    path = scenario_path(slug, variant)
    if path.exists() and not force:
        raise FileExistsError(f"{path.name} already exists (--force writes over it)")
    skeleton = json.loads(SKELETONS[variant].read_text(encoding="utf-8"))
    own = scenario_path(slug)
    if variant != "longform" and own.exists() and json.loads(own.read_text(encoding="utf-8"))["template"] == skeleton["template"]:
        path.write_text(own.read_text(encoding="utf-8"), encoding="utf-8")  # the longform already is this template's edit
        print(f"[시나리오 생성] {path.name}: {own.name}와 같은 템플릿이라 복사", flush=True)
        return path
    w1 = scenario_path(slug, "wide1")
    if variant == "longform" and not path.exists() and w1.exists() and json.loads(w1.read_text(encoding="utf-8")).get("template") == skeleton["template"]:
        try:
            lc.load_scenario(w1.stem)
            path.write_text(w1.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"[시나리오 생성] {path.name}: {w1.name}와 같은 템플릿이라 복사", flush=True)
            return path
        except Exception:
            pass
    short_file(slug).unlink(missing_ok=True)
    progress(0.0, "영상·사진 장면 확인")
    try:
        photos = tp.candidates(slug)
        review = {}

        # Concurrently execute photo review and video frame extraction & review
        def _review_photos():
            if photos:
                return tp._review(slug, photos, lambda f, l: progress(0.25 * f, l), "사진")
            return {}

        def _extract_and_review_frames():
            fms = tp.video_frames(slug, FRAMES_PER_VIDEO)
            if fms:
                return tp._review(slug, fms, lambda f, l: progress(0.25 + 0.15 * f, l), "영상 장면")
            return {}

        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_photos = ex.submit(_review_photos)
            fut_frames = ex.submit(_extract_and_review_frames)
            p_rev = fut_photos.result()
            f_rev = fut_frames.result()
            review.update(f_rev)
            review.update(p_rev)

        if not review:
            raise ShortFootage(f"{drive_index.title(slug)}: 이 차 폴더에 사진·영상(.MOV/.mp4/.jpg/.png)이 없습니다. 미디어를 Drive에 올려 주세요.")
        scenes = plan(slug, review, skeleton)
    except ShortFootage as e:
        lc.atomic_write_json(short_file(slug), {"reason": str(e)})
        raise

    title = drive_index.title(slug)
    lines = [{**ln, "text": title if ln["id"] == "lt01" else ln["text"].replace("{car}", title)} for ln in skeleton["lines"]]
    scenario = {"template": skeleton["template"], "car": {}, "scenes": scenes, "lines": lines,
                "generated": {"by": "make_scenario.py", "skeleton": skeleton["template"]}}

    # Concurrently overlap visual marking (mark()) with copy diversification (draft_copy.diversify_scenario())
    def _run_mark():
        mark(slug, scenes, lambda f, l: progress(0.4 + 0.50 * f, l), review=review)

    def _run_diversify():
        try:
            import draft_copy
            draft_copy.diversify_scenario(slug, scenario)
        except (Exception, SystemExit) as e:  # draft_copy exits when datasets/ is missing (a git-only PC): keep the template lines
            print(f"  [대사 다양화 건너뜀] 기본 템플릿 자막 유지 ({e})", flush=True)

    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_mark = ex.submit(_run_mark)
        fut_copy = ex.submit(_run_diversify)
        fut_mark.result()
        fut_copy.result()

    progress(0.95, "시나리오 검증 및 저장")
    lc.atomic_write_json(path, scenario, indent=1)
    lc.load_scenario(path.stem)  # the builder's own checks: back-to-back scenes, the outro last, every line complete
    print(f"[시나리오 생성] {path.name}: 장면 {len(scenes)}개, {scenes[-1]['start'] + scenes[-1]['dur']:.1f}s", flush=True)
    return path


def add_arrows(slug: str, variant: str = "longform") -> list:
    """For a person's scenario: the 4 arrows on each scene whose role needs them (lc.ROLES) and has none, around the
    mirror agy boxes on 3 stills of a fresh cut of the scene (cropped as the builder crops it; a built clip may be from
    older footage); nothing else in the scenario changes.
    Writes the scenario (the old one goes to scenarios/_backup/) and returns the scene ids given arrows."""
    path = scenario_path(slug, variant)
    data = json.loads(path.read_text(encoding="utf-8"))
    todo = [sc for sc in data["scenes"] if lc.ROLES[sc["role"]].get("arrows") and not sc.get("arrows")]
    if not todo:
        return []
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="_arrows_tmp_", dir=drive_index.media_dir(slug)))
    fracs, files = [0.25, 0.5, 0.75], {}
    try:
        for sc in todo:
            clip = tmp / f"{sc['id']}.mp4"
            _cut_unmasked(slug, sc, clip)
            cap = cv2.VideoCapture(str(clip))
            n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            for j, f in enumerate(fracs):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(f * (n - 1)))
                ok, frame = cap.read()
                if ok:
                    files[f"{sc['id']}_a{j}.jpg"] = tmp / f"{sc['id']}_a{j}.jpg"
                    cv2.imencode(".jpg", cv2.resize(frame, (1920, 1080)))[1].tofile(str(files[f"{sc['id']}_a{j}.jpg"]))
            cap.release()
        names = list(files)
        with ThreadPoolExecutor(AGY_WORKERS) as ex:
            answers = {k: v for res in ex.map(lambda b: tp._ask_about({n: files[n] for n in b}, MASK_ASK),
                                              [names[i:i + tp.AI_BATCH] for i in range(0, len(names), tp.AI_BATCH)])
                       for k, v in res.items()}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    done = []
    for sc in todo:
        is_split = "split" in sc
        boxes = [answers.get(f"{sc['id']}_a{j}.jpg", {}).get("mirror") or [] for j in (1, 0, 2)]  # the middle still first
        box = next(([b[0] * 1.92, b[1] * 1.08, b[2] * 1.92, b[3] * 1.08] for b in boxes if len(b) == 4), None)
        if box is None:
            print(f"  [화살표 폴백] {sc['id']}: agy가 미러를 찾지 못해 기본 미러 영역에 화살표 4개를 배치합니다", flush=True)
        sc["arrows"] = arrows_for(box, is_split)
        done.append(sc["id"])
    backup = lc.SCENARIOS_DIR / "_backup" / f"{path.stem}.before_arrows.json"
    backup.parent.mkdir(exist_ok=True)
    backup.write_bytes(path.read_bytes())
    lc.atomic_write_json(path, data, indent=1)
    return done


def _selftest() -> None:
    cand = lambda src, t, kind, score=5, ln=30.0: {"src": src, "t": t, "len": ln, "kind": kind, "score": score, "box": None, "size": (3840, 2160)}
    cs = [cand("a.mov", 5, "mirror_before", 9), cand("a.mov", 6, "mirror_before", 8), cand("b.mov", 5, "install_stock", 10),
          cand("c.mov", 1, "mirror_before", 3, ln=1.0)]
    BEFORE, AFTER, EXTERIOR = (lc.ROLES[r]["kinds"] for r in ("before", "after", "exterior"))
    first = pick(cs, BEFORE, [], 2.0)
    assert first["t"] == 5 and first["src"] == "a.mov"
    assert pick(cs, BEFORE, [first], 2.0)["t"] == 6 or pick(cs, BEFORE, [first], 2.0)["src"] != "a.mov"
    assert pick(cs, BEFORE, [], 3.0)["src"] != "c.mov"  # 1 s clip: 3 s at 2.5x slower is too long
    assert pick(cs, AFTER, [], 2.0) is None
    assert pick([cand("i.mov", 5, "install_optic", 10)], AFTER, [], 2.0) is None  # an install shot never fills a mirror view
    ext = [cand("e.mov", 0, "car_exterior", 9), cand("e.mov", 2, "car_exterior", 5), cand("e.mov", 4, "car_exterior", 1)]
    assert pick(ext, EXTERIOR, ext[:2], 2.0)["t"] == 4  # one exterior clip: the moment furthest from the taken ones
    p1 = {**cand("p1.jpg", 0, "car_exterior", 10, ln=math.inf), "photo": True}
    p2 = {**cand("p2.jpg", 0, "car_detail", 9, ln=math.inf), "photo": True}
    v1 = cand("v1.mov", 5, "car_detail", 6)
    assert pick([p1, v1], EXTERIOR, [], 3.0)["src"] == "v1.mov"  # video-first even when a photo has higher score/primary kind
    assert pick([p1, v1], EXTERIOR, [v1], 3.0)["src"] == "p1.jpg"  # photo fallback when video has no fresh moment left
    assert pick([p1, p2], EXTERIOR, [p1], 3.0)["src"] == "p2.jpg" and timing(p1, 4.5) == (0.0, 1.0)
    assert timing(cand("x", 0.5, "k"), 2.0) == (0.0, 1.0)
    assert timing(cand("x", 29.9, "k"), 2.0) == (27.95, 1.0)
    assert timing(cand("x", 1, "k", ln=1.1), 2.0) == (0.05, 2.0)  # 1 s of the clip played at half speed
    m = re.fullmatch(r"crop=(\d+):(\d+):(\d+):(\d+)", panel_crop([1700, 800, 2100, 1200], (3840, 2160)))
    w, h, x, y = map(int, m.groups())
    assert x <= 1700 and x + w >= 2100 and y <= 800 and y + h >= 1200 and abs(w / h - PANEL_ASPECT) < 0.01
    m = re.fullmatch(r"crop=(\d+):(\d+):(\d+):(\d+)", panel_crop(None, (1920, 1080)))
    assert int(m[2]) == 1080 and int(m[3]) + int(m[1]) <= 1920
    tr = face_tracks([0, 0.5, 1], [[], [(100, 100, 40)], [(120, 110, 40)]])
    assert len(tr) == 1 and tr[0][0][3] == 0 and tr[0][1][0] == 0 and tr[0][-1] == [1, 120, 110, 40]
    assert lc._FaceStreamTracker._track_at(tr[0], 0.0)[2:] == (100, 100, 60)  # the encoder's own rule: covered (grown) from the still before its first sighting
    assert len(face_tracks([0, 1], [[(100, 100, 40)], [(900, 500, 40)]])) == 2  # far apart: two faces
    plate = {"plates": [[[104, 139], [52, 92], [104, 92], [52, 139]]]}  # corners out of order
    one = covers([0, 0.5, 1], [plate] * 3, False, False)
    assert len(one["plates"]) == 3 and "faces" not in one
    q = one["plates"][0][1]
    assert q[0][0] < q[1][0] and q[0][1] < q[3][1], "corners are TL, TR, BR, BL"
    late = covers([0, 0.25, 0.5, 0.75, 1], [{}] + [plate] * 4, False, False)
    assert late["plates"][0][0] == 0.0 and late["plates"][0][1] == late["plates"][1][1]  # held, not extrapolated
    arrowed_cov = covers([0, 0.5, 1], [plate] * 3, False, True)
    assert len(arrowed_cov["plates"]) == 3 and "faces" not in arrowed_cov and len(arrowed_cov["arrows"]) == 4  # arrow clips get plate homography too
    fb_cov = covers([0, 1], [{}, {}], False, True, fallback_box=[1000, 300, 1700, 800])
    assert fb_cov["arrows"][0][0] == 1000 and fb_cov["arrows"][1][0] == 1700  # fallback_box used when mirror is missing
    assert "faces" not in covers([0, 1], [{"faces": [[500, 500, 740]]}, {}], False, False)  # blur read as a frame-wide face
    assert len(covers([0, 1], [{"faces": [[500, 500, 120]]}, {}], False, False)["faces"]) == 1
    badge = {"plates": [[[0, 30], [1000, 110], [1000, 1000], [0, 1000]]]}  # c40 외관영상 7: the RECHARGE TWIN badge
    assert covers([0, 1], [badge, {}], False, False) == {}
    few = covers([0, 0.5, 1], [{}, {}, plate], False, False)
    assert "plates" not in few and len(few["faces"]) == 1
    a, b = [[100, 100], [200, 100], [200, 150], [100, 150]], [[1500, 600], [1650, 600], [1650, 680], [1500, 680]]
    track, rest = plate_track([[a], [a, b], [b]])
    assert track == {0: a, 1: a} and rest == [[], [b], [b]]  # the cover never jumps to the other car's plate
    sp = covers([0, 1], [{"mirror": [600, 300, 900, 700]}] * 2, True, True)
    assert all(960 < a[0] < 1920 for a in sp["arrows"]) and "plates" not in sp
    for variant, f in SKELETONS.items():  # every scene has a role, the template its slots
        skel = json.loads(f.read_text(encoding="utf-8"))
        assert all(s.get("role") in lc.ROLES for s in skel["scenes"]), f"{variant}: a scene without a role"
        assert skel["scenes"][-1].get("role") == "outro"
        n_slots = len(lc.load_template(skel["template"])["slots"])
        assert len(skel["scenes"]) == n_slots, f"{variant}: {len(skel['scenes'])} scenes for {n_slots} slots"
    global stills
    real, stills = stills, lambda slug, review: [cand(f"{k}{i}.mov", 5, k) for k in ("car_exterior", "car_detail", "mirror_before", "mirror_after") for i in range(6)]
    try:  # the wide1 skeleton filled: arrows on the 시공 후 shots and splits only, splits as 50:50, the outro last
        got = plan("t", {}, json.loads(SKELETONS["wide1"].read_text(encoding="utf-8")))
    finally:
        stills = real
    arrowed = lambda got: [s["id"] for s in got if lc.ROLES[s["role"]].get("arrows")]
    assert arrowed(got) == ["w08", "w09", "w10", "w11"]
    assert [s["id"] for s in got if "split" in s] == ["w10", "w11"] and got[-1]["src"] == "outro"
    assert got[0]["src"].startswith("car_exterior") and got[1]["src"].startswith("car_detail") and got[6]["src"].startswith("mirror_before")
    wide1_tpl = lc.load_template("opticglass_wide1")
    wide1_skel = json.loads(SKELETONS["wide1"].read_text(encoding="utf-8"))
    assert wide1_tpl.get("transitions") is False, "wide1: no transitions, as the template"
    assert wide1_tpl.get("keep_stickers") is True, "wide1: preserve Track[4] badge-pointer stickers"
    assert len(wide1_tpl["slots"]) == 13 and round(wide1_tpl["slots"][-1]["start"] + wide1_tpl["slots"][-1]["dur"], 3) == 57.733
    assert [s["id"] for s in wide1_skel["scenes"]] == [f"w{i:02d}" for i in range(13)]
    assert [l["id"] for l in wide1_skel["lines"]] == list(wide1_tpl["text_slots"].keys()) and len(wide1_tpl["text_slots"]) == 21
    for gold_id in ("ws2", "ws4", "wz2", "wz4"):
        assert wide1_tpl["text_slots"][gold_id]["color"] == "#F4C70F", f"wide1 {gold_id} must be #F4C70F"
    wide1_dc = json.loads((wide1_tpl["dir"] / "draft_content.json").read_text(encoding="utf-8"))
    assert wide1_dc["duration"] == 57733333
    assert all(s["target_timerange"] == {"start": 0, "duration": 57733333}
               for t in wide1_dc["tracks"] if t["type"] == "audio" for s in t["segments"]), "wide1 shell audio must cover 57.733s"
    for s in got:  # what plan fills keeps the role rules once mark() has drawn the arrows
        s["arrows"] = [[0, 0, 1, 0, 100]] * 4 if lc.ROLES[s["role"]].get("arrows") else None
    lc.check_scene_rules("t", got, {})
    stills = lambda slug, review: [cand(f"{k}{i}.mov", 5, k) for k in ("car_exterior", "car_detail", "mirror_before", "mirror_after") for i in range(9)]
    hand = lc.SCENARIOS_DIR / "cybertruck_longform.json"  # a hand-made 80 s scenario (agy_edit/add_arrows still plan these)
    try:  # the 80 s cut: arrows on s12/s12b/s12c (시공 후 mirror), the comparison shots and the splits, nowhere else
        got = plan("t", {}, json.loads(hand.read_text(encoding="utf-8")))
    finally:
        stills = real
    assert arrowed(got) == ["s12", "s12b", "s12c", "s14", "s15", "s16", "s16b", "s16c"], arrowed(got)
    stills = lambda slug, review: [cand(f"{k}{i}.mov", 5, k) for k in ("car_exterior", "mirror_before", "install_optic") for i in range(9)]
    try:  # no OpticGlass mirror view, only install shots: no scenario (an install shot never fills a 시공 후 scene)
        plan("t", {}, json.loads(hand.read_text(encoding="utf-8")))
        raise AssertionError("planned 시공 후 scenes from install shots")
    except ShortFootage as e:
        assert "옵틱 미러 시야" in str(e), e
    finally:
        stills = real
    # Cross-vehicle comparing-scene fallback vs target preservation (offline, isolated from DATA_DIR)
    global donor_stills
    real_donors = donor_stills
    donor_pool = [
        {**cand("@media/donor_a/gdrive_raw/mb.jpg", 0.0, "mirror_before", 10, ln=math.inf), "photo": True},
        {**cand("@media/donor_b/gdrive_raw/ma.jpg", 0.0, "mirror_after", 10, ln=math.inf), "photo": True},
    ]
    donor_stills = lambda exclude_slug: list(donor_pool)
    try:
        # 1. Target lacks mirror_before/mirror_after -> comparing scenes w06..w11 fall back to donors, w00..w05 stay target
        stills = lambda slug, review: [cand(f"target_ext{i}.mov", 5, "car_exterior") for i in range(6)]
        got_fb = plan("target_car", {}, wide1_skel)
        assert all(not s["src"].startswith(lc.MEDIA_SRC_PREFIX) for s in got_fb[:6]), "non-comparing scenes must stay target"
        assert all(s["src"] == "@media/donor_a/gdrive_raw/mb.jpg" for s in got_fb if s["role"] == "compare_before")
        assert all(s["src"] == "@media/donor_b/gdrive_raw/ma.jpg" for s in got_fb if s["role"] == "compare_after")
        assert all(s["src"] == "@media/donor_a/gdrive_raw/mb.jpg" and s["split"]["src_after"] == "@media/donor_b/gdrive_raw/ma.jpg"
                   for s in got_fb if s["role"] == "split")
        # 2. Target has its own mirror_before/mirror_after (lower score) -> target selection preserved, zero donor fallback
        stills = lambda slug, review: (
            [cand(f"target_ext{i}.mov", 5, "car_exterior") for i in range(6)]
            + [{**cand("own_before.jpg", 0.0, "mirror_before", 2, ln=math.inf), "photo": True},
               {**cand("own_after.jpg", 0.0, "mirror_after", 2, ln=math.inf), "photo": True}]
        )
        got_own = plan("target_car", {}, wide1_skel)
        assert all(not s["src"].startswith(lc.MEDIA_SRC_PREFIX) and not s.get("split", {}).get("src_after", "").startswith(lc.MEDIA_SRC_PREFIX)
                   for s in got_own if s["role"] in COMPARE_ROLES), "target own comparing refs must be preserved"
        # 3. Partial missing: target has mirror_before only -> only mirror_after falls back to donor
        stills = lambda slug, review: (
            [cand(f"target_ext{i}.mov", 5, "car_exterior") for i in range(6)]
            + [{**cand("own_before.jpg", 0.0, "mirror_before", 2, ln=math.inf), "photo": True}]
        )
        got_part = plan("target_car", {}, wide1_skel)
        assert all(s["src"] == "own_before.jpg" for s in got_part if s["role"] == "compare_before")
        assert all(s["src"] == "@media/donor_b/gdrive_raw/ma.jpg" for s in got_part if s["role"] == "compare_after")
        assert all(s["src"] == "own_before.jpg" and s["split"]["src_after"] == "@media/donor_b/gdrive_raw/ma.jpg"
                   for s in got_part if s["role"] == "split")
        # 4. Neither target nor any donor has mirror_before/mirror_after -> ShortFootage raised
        donor_stills = lambda exclude_slug: []
        stills = lambda slug, review: [cand(f"target_ext{i}.mov", 5, "car_exterior") for i in range(6)]
        try:
            plan("target_car", {}, wide1_skel)
            raise AssertionError("wide1 without target or donor comparing refs must raise ShortFootage")
        except ShortFootage:
            pass
    finally:
        stills = real
        donor_stills = real_donors
    # 5. mark() uses 1st-pass review directly (no 2nd-pass agy _ask_about call) for target & @media/ donor scenes
    import portable_paths as pp
    td = pathlib.Path(tempfile.mkdtemp(prefix="ms_mark_"))
    orig_env = (pp.MEDIA_DIR, lc.MEDIA_DIR, drive_index.MEDIA_DIR, drive_index.LINKS, tp._ask_about)
    try:
        pp.MEDIA_DIR = lc.MEDIA_DIR = drive_index.MEDIA_DIR = td
        links_f = td / "links.json"
        links_f.write_text(json.dumps({"tcar": {"folder_id": "1", "folder_name": "tcar", "car_name": "tcar"},
                                       "dcar": {"folder_id": "2", "folder_name": "dcar", "car_name": "dcar"}}), encoding="utf-8")
        drive_index.LINKS = links_f
        (td / "tcar" / "gdrive_raw").mkdir(parents=True)
        (td / "dcar" / "gdrive_raw").mkdir(parents=True)
        (td / "dcar" / "thumb").mkdir(parents=True)
        Image.new("RGB", (1920, 1080), (40, 60, 80)).save(td / "tcar" / "gdrive_raw" / "ext.jpg")
        Image.new("RGB", (1280, 720), (80, 120, 160)).save(td / "dcar" / "gdrive_raw" / "aft.jpg")
        sz_aft = (td / "dcar" / "gdrive_raw" / "aft.jpg").stat().st_size
        (td / "dcar" / "thumb" / "review.json").write_text(json.dumps({
            f"{tp.REVIEW_VERSION}|aft.jpg|{sz_aft}": {
                "kind": "mirror_after", "score": 9, "plates": [],
                "faces": [[200, 300, 50]], "mirror": [300, 200, 800, 800],
            }
        }), encoding="utf-8")
        tp._ask_about = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("2nd-pass agy must not be called"))
        t_rev = {"ext.jpg": {"kind": "car_exterior", "score": 9,
                             "plates": [[[400, 600], [600, 600], [600, 680], [400, 680]]],
                             "faces": [[250, 250, 40]], "mirror": []}}
        m_scenes = [
            {"id": "w00", "role": "exterior", "src": "ext.jpg", "in": 0.0, "dur": 4.0, "look": "title"},
            {"id": "w08", "role": "compare_after", "src": "@media/dcar/gdrive_raw/aft.jpg", "in": 0.0, "dur": 5.0, "look": "bright"},
            {"id": "w10", "role": "split", "src": "ext.jpg", "in": 0.0, "dur": 4.0,
             "split": {"src_after": "@media/dcar/gdrive_raw/aft.jpg", "in_after": 0.0,
                       "crop_before": "crop=960:1080:0:0", "crop_after": "crop=640:720:320:0"}},
            {"id": "w12", "role": "outro", "src": "outro", "in": 0.0, "dur": 7.133, "look": "plain"},
        ]
        mark("tcar", m_scenes, lambda f, l: None, review=t_rev)
        assert "plates" in m_scenes[0] and "faces" in m_scenes[0], "target scene must inherit 1st-pass plates/faces"
        assert len(m_scenes[1].get("arrows") or []) == 4 and "faces" in m_scenes[1], "donor compare_after needs arrows + faces"
        assert len(m_scenes[2].get("arrows") or []) == 4 and all(960 < a[0] < 1920 for a in m_scenes[2]["arrows"]), "split arrows on right"
    finally:
        pp.MEDIA_DIR, lc.MEDIA_DIR, drive_index.MEDIA_DIR, drive_index.LINKS, tp._ask_about = orig_env
        shutil.rmtree(td, ignore_errors=True)
    print("make_scenario self-check ok")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        _selftest()
    else:
        v = sys.argv[sys.argv.index("--variant") + 1] if "--variant" in sys.argv else "longform"
        if "--add-arrows" in sys.argv:  # a person's scenario: only the missing arrows
            print(f"[화살표 추가] {sys.argv[1]}_{v}: {add_arrows(sys.argv[1], v)}")
            sys.exit()
        try:
            generate(sys.argv[1], force="--force" in sys.argv, variant=v)
        except ShortFootage as e:
            sys.exit(f"[시나리오 생성 불가] {e}")
