"""Learns the on-screen lines and the edit structure of the OpticGlass YouTube channel's recent uploads, as examples for
the LLM-written lines (draft_copy.py, build_shorts.py hooks). The channel has no transcripts to read: its lines are
burned into the picture and YouTube's auto-captions hear only the BGM.

For every video and short uploaded in the last --days (default 92), one at a time: download it at 720p (picture only),
find its cuts (ffmpeg scdet), read every half second with Windows OCR (Korean, win_ocr.ps1) on the frame and on three
text masks (coloured fill, two white thresholds), and group the readings that stay at one place on screen for about a
second or more into captions. agy (task youtube_lines, text only) then picks each caption's spelling from its readings
and drops what is not a caption (logos, shop signs, reflections); an answer that strays from the readings is not used.
The video and its frames are deleted after each one (drive C: is nearly full).

Writes
  datasets/youtube/<id>.json       one upload: meta, cuts, captions with every OCR reading (a rerun skips it)
  datasets/youtube_lines.jsonl     every caption as a draft_lines.jsonl-style row with source "youtube"
  datasets/youtube_structure.json  per format: length, shots, caption timing, where the fixed sections start

usage: py youtube_lines.py [--days 92] [--ids ID ...] [--limit N] [--no-agy] [--rebuild] [--selftest]
       --rebuild only rewrites the two summary files from datasets/youtube/*.json
"""
import argparse
import collections
import concurrent.futures as cf
import datetime
import difflib
import json
import os
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

WORK = pathlib.Path(__file__).resolve().parent
DATA = WORK / "datasets"
PER_VIDEO = DATA / "youtube"
LINES = DATA / "youtube_lines.jsonl"
STRUCTURE = DATA / "youtube_structure.json"
CHANNEL = "https://www.youtube.com/channel/UCncj0fohwMC3-ck7FKx4GZg"  # 옵틱글래스 (@optic_glass)
TABS = ("videos", "shorts")
OCR_PS1 = WORK / "win_ocr.ps1"
FPS = 2              # frames read per second; a caption stays at least ~1.5 s
MIN_FRAMES = 2       # text read in fewer frames is noise, or background passing by
SAME_ROW = 0.05      # readings this close (fraction of the frame height; centres within SAME_COL of the width) and
SAME_COL = 0.2       # (the 시공 전 / 시공 후 badges sit side by side at one height)
GAP_S = 1.0          # this close in time
SIMILAR = 0.55       # and this alike (difflib ratio, spaces ignored) are one caption
MIN_QUALITY = 0.8    # share of Hangul / plain ASCII characters a reading needs
AGY_STRAY = 0.4      # agy's text must be at least this alike to one of the caption's readings
WORKERS = 2
CANVAS = {"longform": (1920, 1080), "shortform": (1080, 1920)}  # scenario px, as in draft_lines.jsonl
OPTIC_TITLE = re.compile(r"미러|거울|광각|시야|사각|옵틱|사이드", re.I)  # the channel also posts car-info shorts
ANCHORS = [  # fixed sections of the channel's edits, found by their on-screen text
    ("광각미러가 꼭 필요한 이유", r"꼭\s?필요한\s?이유"),
    ("설치 전/후 표시", r"설치\s?(전|후)"),
    ("시공 전/후 비교", r"시공\s?(전|후)"),
    ("문의 아웃트로", r"문의|010-?\d{4}"),
]
FIX_ASK = """아래는 옵틱글래스(광각 사이드미러 교체) 유튜브 {kind} 「{title}」 화면을 0.5초마다 Windows OCR로 읽은 결과다.
각 항목은 화면의 한 자리에 1초 이상 머문 글자다. readings는 OCR이 읽은 서로 다른 결과와 그렇게 읽은 프레임 수이며, OCR은 한글을 자주 틀린다.
항목마다 다음을 정한다.
- caption: 편집자가 넣은 자막, 제목, 문구면 true. 로고나 워터마크(Optic-Glass, BY OPTICGLASS), 가게 간판, 미러나 배경에 비친 글자, 차 엠블럼, 번호판, 알아볼 수 없는 글자면 false.
- text: caption이면 readings와 영상 제목을 근거로 맞춤법이 맞는 원래 문구. readings에 없는 내용은 지어내지 않는다. 차명, 영문, 숫자는 readings와 제목에 있는 그대로 쓴다. caption이 false면 빈 문자열.
JSON 객체 하나로만 답한다(모든 id 포함): {{"items": [{{"id": 0, "caption": true, "text": "..."}}]}}
항목:
{items}"""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
YTDLP = ["yt-dlp", "--encoding", "utf-8", "--no-warnings"]  # titles in UTF-8, not the console code page


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          creationflags=NO_WINDOW, **kw)


# --- what to read -----------------------------------------------------------------------------------------------------
def list_uploads(days: int) -> list:
    """Uploads of the last `days` days, newest first: {id, tab, upload_date, duration, title}."""
    since = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y%m%d")
    found = []
    with tempfile.TemporaryDirectory(prefix="ogyt_list_") as tmp:
        for tab in TABS:
            f = pathlib.Path(tmp) / f"{tab}.tsv"
            r = run([*YTDLP, "--skip-download", "--ignore-errors", "--extractor-args", "youtube:lang=ko",
                     "--break-match-filters", f"upload_date>={since}",
                     "--print-to-file", "%(upload_date)s\t%(id)s\t%(duration)s\t%(title)s", f, f"{CHANNEL}/{tab}"])
            rows = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
            errs = [l for l in r.stderr.splitlines() if l.startswith("ERROR")]
            if not rows and errs:
                raise RuntimeError(f"yt-dlp could not list {tab}: {errs[-1][:300]}")
            if errs:
                print(f"WARNING {tab}: {len(errs)} yt-dlp errors, the listing may be partial (run again): {errs[-1][:200]}", flush=True)
            for row in rows:
                date, vid, dur, title = row.split("\t", 3)
                if date >= since:
                    found.append({"id": vid, "tab": tab, "upload_date": date, "duration": float(dur) if dur != "NA" else None,
                                  "title": title})
    return found


def meta_for(ids: list) -> list:
    r = run([*YTDLP, "--skip-download", "--extractor-args", "youtube:lang=ko",
             "--print", "%(upload_date)s\t%(id)s\t%(duration)s\t%(title)s", *[f"https://www.youtube.com/watch?v={i}" for i in ids]])
    out = []
    for row in r.stdout.splitlines():
        date, vid, dur, title = row.split("\t", 3)
        out.append({"id": vid, "tab": "?", "upload_date": date, "duration": float(dur), "title": title})
    if len(out) != len(ids):
        raise RuntimeError(f"yt-dlp found {len(out)} of {len(ids)} ids: {r.stderr.strip()[-300:]}")
    return out


# --- one upload -------------------------------------------------------------------------------------------------------
def download(vid: str, tmp: pathlib.Path) -> pathlib.Path:
    r = run([*YTDLP, "-q", "-f", "bv*/b", "-S", "res:720,vcodec:h264,ext:mp4",
             "-o", tmp / "v.%(ext)s", f"https://www.youtube.com/watch?v={vid}"])
    got = sorted(tmp.glob("v.*"))
    if r.returncode or not got:
        raise RuntimeError(f"download failed: {r.stderr.strip()[-300:]}")
    return got[0]


def probe(src: pathlib.Path) -> tuple:
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
             "-of", "json", src])
    j = json.loads(r.stdout)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


def scene_cuts(src: pathlib.Path, vertical: bool) -> list:
    """Cut times (s). A transition fires scdet several frames in a row: those count once. A short is judged on its
    middle half: many keep a fixed headline and logo above and below the picture."""
    vf = ("crop=iw:ih/2:0:ih/4," if vertical else "") + "scale=320:-2,scdet=threshold=12"
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-vf", vf, "-an", "-f", "null", "-"])
    cuts = []
    for t in (float(x) for x in re.findall(r"lavfi\.scd\.time:\s*([\d.]+)", r.stderr)):
        if not cuts or t - cuts[-1] > 0.4:
            cuts.append(round(t, 2))
    return cuts


def text_masks(big):
    """Black text on white for OCR: the channel's captions are coloured fills or white with a dark outline/glow."""
    import cv2
    hsv = cv2.cvtColor(big, cv2.COLOR_BGR2HSV)
    s, v = hsv[..., 1], hsv[..., 2]
    return {"c": (v > 140) & (s > 90), "w": (v > 230) & (s < 40), "g": (v > 200) & (s < 30)}


def ocr_readings(src: pathlib.Path, tmp: pathlib.Path) -> list:
    """Every text line Windows OCR finds, on the frame and its masks, every 1/FPS s:
    {t, tag, text, x, y, w, h} with the box as fractions of the frame."""
    import cv2
    import numpy as np
    frames, shots = tmp / "frames", tmp / "ocr"
    frames.mkdir()
    shots.mkdir()
    r = run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={FPS}", "-q:v", "2", frames / "%05d.jpg"])
    if r.returncode:
        raise RuntimeError(f"ffmpeg frames: {r.stderr[-300:]}")
    kernel = np.ones((2, 2), np.uint8)
    for f in sorted(frames.glob("*.jpg")):
        im = cv2.imread(str(f))
        big = cv2.resize(im, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)  # Windows OCR reads small text better
        for tag, m in text_masks(big).items():
            m = cv2.morphologyEx(m.astype(np.uint8) * 255, cv2.MORPH_OPEN, kernel)
            cv2.imwrite(str(shots / f"{f.stem}_{tag}.png"), 255 - m)
        shutil.move(f, shots / f"{f.stem}_r.jpg")
    r = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", OCR_PS1, "-Dir", shots])
    if r.returncode:
        raise RuntimeError(f"OCR failed: {r.stderr.strip()[-400:]}")
    out = []
    for line in r.stdout.splitlines():
        line = line.lstrip("﻿").strip()
        if not line.startswith("{"):
            continue
        d = json.loads(line)
        frame, tag = pathlib.Path(d["file"]).stem.split("_")
        t = (int(frame) - 1) / FPS
        for x in d["lines"]:
            out.append({"t": t, "tag": tag, "text": x["text"], "x": x["x"] / d["w"], "y": x["y"] / d["h"],
                        "w": x["w"] / d["w"], "h": x["h"] / d["h"]})
    return out


# --- readings -> captions ---------------------------------------------------------------------------------------------
def squash(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, squash(a), squash(b)).ratio()


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" -~•·`'\"\\|*_.,:;^").strip()


def quality(text: str) -> float:
    chars = [c for c in text if not c.isspace()]
    ok = sum(1 for c in chars if "가" <= c <= "힣" or (c.isascii() and (c.isalnum() or c in "-.,!?%~'\"()/:+&#")))
    return ok / len(chars) if chars else 0.0


def meaningful(text: str) -> bool:
    return len(re.findall(r"[가-힣]", text)) >= 2 or len(re.findall(r"[A-Za-z0-9]", text)) >= 3


def captions(readings: list, duration: float) -> list:
    """Readings that stay at one height for MIN_FRAMES+ frames with alike text -> one caption each: its most often
    read text, every reading with its frame count, time span and median box (fractions of the frame)."""
    segs = []
    for r in sorted(readings, key=lambda r: (r["t"], r["y"])):
        text = clean(r["text"])
        if quality(text) < MIN_QUALITY or not meaningful(text):
            continue
        cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
        best = None
        for s in segs:
            if r["t"] - s["last"] > GAP_S or abs(cy - s["cy"]) > SAME_ROW or abs(cx - s["cx"]) > SAME_COL:
                continue
            # match what the segment shows now (read in its latest frames), so 시공 전 -> 시공 후 in one spot starts anew
            sim = max(similar(text, k) for k, ts in s["seen"].items() if max(ts) >= s["last"] - 1 / FPS)
            if sim >= SIMILAR and (best is None or sim > best[0]):
                best = (sim, s)
        if best is None:
            best = (1.0, {"seen": collections.defaultdict(set), "hits": [], "first": r["t"], "last": r["t"], "cx": cx, "cy": cy})
            segs.append(best[1])
        s = best[1]
        s["seen"][text].add(r["t"])
        s["hits"].append((r["t"], text, r["x"], r["y"], r["w"], r["h"]))
        s["last"] = max(s["last"], r["t"])
        s["cx"] = statistics.median(h[2] + h[4] / 2 for h in s["hits"])
        s["cy"] = statistics.median(h[3] + h[5] / 2 for h in s["hits"])
    out = []
    for s in segs:
        for ts in _runs(s["hits"]):
            hits = [h for h in s["hits"] if h[0] in ts]
            seen = collections.defaultdict(set)
            for h in hits:
                seen[h[1]].add(h[0])
            if len(ts) < MIN_FRAMES:
                continue
            ranked = sorted(seen, key=lambda k: (len(seen[k]), quality(k), len(k)), reverse=True)
            box = [round(statistics.median(h[i] for h in hits), 4) for i in range(2, 6)]
            out.append({"start": round(max(0.0, min(ts) - 0.5 / FPS), 2), "end": round(min(duration, max(ts) + 0.5 / FPS), 2),
                        "x": box[0], "y": box[1], "w": box[2], "h": box[3], "frames": len(ts), "text": ranked[0],
                        "ocr": ranked[0], "readings": [[k, len(seen[k])] for k in ranked[:6]], "caption": None, "fixed_by": "ocr"})
    out.sort(key=lambda c: (c["start"], c["y"]))
    return out


def _runs(hits: list) -> list:
    """A segment's frames split where the text read most in a frame changes to another for MIN_FRAMES+ frames in a row
    (시공 전 then 시공 후 in one spot). Shorter changes are misreads and stay with the frames around them. Each run is
    a set of frame times."""
    per_frame = collections.defaultdict(collections.Counter)
    for t, text, *_ in hits:
        per_frame[t][text] += 1
    runs = []  # [text, [frame times]]
    for t in sorted(per_frame):
        text = per_frame[t].most_common(1)[0][0]
        if runs and similar(text, runs[-1][0]) >= 0.9:
            runs[-1][1].append(t)
        else:
            runs.append([text, [t]])
    merged = []
    for run in runs:  # a run too short to be a caption joins the run before it (or, at the start, the one after)
        if merged and (len(run[1]) < MIN_FRAMES or similar(run[0], merged[-1][0]) >= 0.9):
            merged[-1][1].extend(run[1])
        elif merged and len(merged[-1][1]) < MIN_FRAMES:
            merged[-1] = [run[0], merged[-1][1] + run[1]]
        else:
            merged.append(run)
    return [set(ts) for _, ts in merged]


def fix_with_agy(caps: list, title: str, kind: str) -> None:
    """agy picks each caption's spelling and drops non-captions, in place. Answers far from every reading are ignored."""
    import llm
    items = [json.dumps({"id": i, "time": f"{c['start']:.1f}-{c['end']:.1f}s",
                         "pos": "top" if c["y"] + c["h"] / 2 < 0.33 else "bottom" if c["y"] + c["h"] / 2 > 0.66 else "middle",
                         "readings": c["readings"][:5]}, ensure_ascii=False) for i, c in enumerate(caps)]
    for chunk_start in range(0, len(items), 60):  # the agy prompt is capped at ~28,000 characters
        chunk = items[chunk_start:chunk_start + 60]
        ans = llm.generate_json("youtube_lines", FIX_ASK.format(kind=kind, title=title, items="\n".join(chunk)))
        for it in ans.get("items", []) if isinstance(ans.get("items"), list) else []:
            i = it.get("id") if isinstance(it, dict) else None
            if not isinstance(i, int) or not chunk_start <= i < chunk_start + len(chunk):
                continue
            c = caps[i]
            if it.get("caption") is False:
                c["caption"], c["fixed_by"] = False, "agy"
            elif it.get("caption") is True and isinstance(it.get("text"), str) and it["text"].strip():
                text = it["text"].strip()
                if max(similar(text, k) for k, _ in c["readings"]) >= AGY_STRAY:
                    c["caption"], c["text"], c["fixed_by"] = True, text, "agy"
                else:
                    c["agy_stray"] = text


def _centre(c: dict) -> tuple:
    return c["x"] + c["w"] / 2, c["y"] + c["h"] / 2


def _within(a: str, b: str) -> bool:
    """a is b with some letters left out (광각미러가 필요한 이유 / 광각미러가 꼭 필요한 이유), not a different word."""
    it = iter(squash(b))
    return all(ch in it for ch in squash(a))


def merge_same(caps: list) -> list:
    """One caption read as several (badly read frames cluster apart) -> one: same place, touching in time and the same
    text (after agy; an unresolved one by the answer agy gave for it). The same text keeps going over gaps up to 4 s
    (a title card over several shots, a badge over two compare clips)."""
    keep = []
    for c in sorted(caps, key=lambda c: -c["frames"]):
        text = c.get("agy_stray") if c["caption"] is None and c.get("agy_stray") else c["text"]
        for k in keep:
            sim = similar(text, k["text"])
            gap = max(c["start"], k["start"]) - min(c["end"], k["end"])
            (cx, cy), (kx, ky) = _centre(c), _centre(k)
            alike = sim >= 0.95 or (sim >= 0.8 and (_within(text, k["text"]) or _within(k["text"], text)))
            if (c["caption"] is not False and k["caption"] is not False and alike
                    and gap <= (4.0 if sim >= 0.95 else GAP_S) and abs(cy - ky) <= SAME_ROW and abs(cx - kx) <= SAME_COL):
                k["start"], k["end"], k["frames"] = min(k["start"], c["start"]), max(k["end"], c["end"]), k["frames"] + c["frames"]
                counts = collections.Counter(dict(k["readings"])) + collections.Counter(dict(c["readings"]))
                k["readings"] = [list(x) for x in counts.most_common(6)]
                if k["caption"] is None and c["caption"] is True:  # keep the agy-checked text
                    k["caption"], k["text"], k["fixed_by"] = True, c["text"], "agy"
                    k.pop("agy_stray", None)
                break
        else:
            keep.append(c)
    # OCR sometimes reads part of a line as its own line: a piece inside a longer caption shown on that row then goes
    piece_of = lambda c, k: (k is not c and k["caption"] is not False and len(squash(k["text"])) > len(squash(c["text"]))
                             and squash(c["text"]) in squash(k["text"]) and abs(_centre(c)[1] - _centre(k)[1]) <= SAME_ROW
                             and min(c["end"], k["end"]) > max(c["start"], k["start"]))
    # ... and a reading agy left unresolved inside the time of a checked caption on that row is a garbled copy of it
    copy_of = lambda c, k: (c["caption"] is None and k["caption"] is True and abs(_centre(c)[1] - _centre(k)[1]) <= SAME_ROW
                            and abs(_centre(c)[0] - _centre(k)[0]) <= SAME_COL
                            and k["start"] - 0.5 <= c["start"] and c["end"] <= k["end"] + 0.5)
    keep = [c for c in keep if c["caption"] is False or not any(piece_of(c, k) or copy_of(c, k) for k in keep)]
    return sorted(keep, key=lambda c: (c["start"], c["y"]))


def process(v: dict, use_agy: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"ogyt_{v['id']}_") as tmp:
        tmp = pathlib.Path(tmp)
        src = download(v["id"], tmp)
        w, h, duration = probe(src)
        cuts = scene_cuts(src, h > w)
        readings = ocr_readings(src, tmp)
    fmt = "shortform" if h > w else "longform"
    rec = {**v, "url": f"https://www.youtube.com/watch?v={v['id']}", "duration": round(duration, 2), "width": w, "height": h,
           "format": fmt, "aspect": "9:16" if fmt == "shortform" else "16:9", "cuts": cuts, "ocr_readings": len(readings),
           "captions": captions(readings, duration), "agy": False, "note": "",
           "made": datetime.datetime.now().isoformat(timespec="seconds")}
    if use_agy:
        agy_step(rec)
    else:
        rec["captions"] = merge_same(rec["captions"])
    save(rec)
    return rec


def agy_step(rec: dict) -> None:
    """agy checks the record's captions (in place); a failure keeps the OCR text and is retried by the next run."""
    try:
        if rec["captions"]:
            fix_with_agy(rec["captions"], rec["title"], "숏츠" if rec["format"] == "shortform" else "영상")
        rec["agy"], rec["note"] = True, ""
    except Exception as e:
        rec["note"] = f"agy: {e}"[:300]
    rec["captions"] = merge_same(rec["captions"])


def save(rec: dict) -> None:
    """Written whole or not at all: a killed run never leaves a broken cache file."""
    PER_VIDEO.mkdir(parents=True, exist_ok=True)
    tmp = PER_VIDEO / f"{rec['id']}.json.tmp"
    tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, PER_VIDEO / f"{rec['id']}.json")


# --- summaries --------------------------------------------------------------------------------------------------------
def blocks(caps: list) -> list:
    """Captions shown together one above the other (a two-line headline) -> one block, lines top to bottom."""
    out = []
    for c in sorted((c for c in caps if c["caption"] is not False), key=lambda c: (c["start"], c["y"])):
        for b in out:
            top, bottom = b[0], b[-1]  # a line read a frame late may sit above the block's first line
            near = lambda o: (min(c["end"], o["end"]) - max(c["start"], o["start"]) >= 0.6 * min(c["end"] - c["start"], o["end"] - o["start"])
                              and abs(_centre(c)[0] - _centre(o)[0]) < 0.25)
            below = near(bottom) and 0 <= c["y"] - (bottom["y"] + bottom["h"]) < 1.5 * max(c["h"], bottom["h"])
            above = near(top) and 0 <= top["y"] - (c["y"] + c["h"]) < 1.5 * max(c["h"], top["h"])
            if below or above:
                b.append(c)
                b.sort(key=lambda k: k["y"])
                break
        else:
            out.append([c])
    return out


def write_summaries() -> tuple:
    from extract_draft_lines import part_of
    videos = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PER_VIDEO.glob("*.json"))]
    rows = []
    for v in videos:
        brand = "opticglass" if OPTIC_TITLE.search(v["title"]) else "carinfo"
        W, H = CANVAS[v["format"]]
        for b in blocks(v["captions"]):
            text = "\n".join(c["text"] for c in b)
            start, end = min(c["start"] for c in b), max(c["end"] for c in b)
            x0, y0 = min(c["x"] for c in b), min(c["y"] for c in b)
            x1, y1 = max(c["x"] + c["w"] for c in b), max(c["y"] + c["h"] for c in b)
            part, rule = part_of(text, start, v["duration"])
            rows.append({"source": "youtube", "brand": brand, "draft": f"yt {v['upload_date']} {v['title']}", "timeline": v["id"],
                         "video_id": v["id"], "upload_date": v["upload_date"], "tab": v.get("tab"), "format": v["format"],
                         "aspect": v["aspect"], "duration": v["duration"], "scene": 1 + sum(t <= start + 0.5 / FPS + 1e-6 for t in v["cuts"]),
                         "scenes": len(v["cuts"]) + 1, "start": start, "dur": round(end - start, 2),
                         "fc_pos": [round((x0 + x1) / 2 * W), round((y0 + y1) / 2 * H)],
                         "size": round(statistics.median(c["h"] for c in b) * H),  # text box height, not the font size
                         "text": text, "kind": "text", "part": part, "part_rule": rule,
                         "checked": all(c["fixed_by"] == "agy" for c in b)})
    per_text = collections.defaultdict(set)
    for r in rows:
        per_text[squash(r["text"])].add(r["video_id"])
    for r in rows:
        r["common_drafts"] = len(per_text[squash(r["text"])])
    LINES.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    STRUCTURE.write_text(json.dumps(structure(videos, rows), ensure_ascii=False, indent=1), encoding="utf-8")
    return videos, rows


def _q(xs: list) -> dict:
    xs = sorted(xs)
    if not xs:
        return {}
    if len(xs) < 4:
        return {"median": round(statistics.median(xs), 2), "n": len(xs)}
    q1, q2, q3 = statistics.quantiles(xs, n=4)
    return {"q1": round(q1, 2), "median": round(q2, 2), "q3": round(q3, 2), "n": len(xs)}


def structure(videos: list, rows: list) -> dict:
    groups = collections.defaultdict(list)
    for v in videos:
        groups[f"{v['format']}/{'opticglass' if OPTIC_TITLE.search(v['title']) else 'carinfo'}"].append(v)
    out = {"made": datetime.date.today().isoformat(), "channel": CHANNEL, "groups": {}}
    for key, vs in sorted(groups.items()):
        ids = {v["id"] for v in vs}
        rs = [r for r in rows if r["video_id"] in ids]
        anchors = {}
        for name, rx in ANCHORS:
            hits = [(r["start"], r["start"] / r["duration"]) for v in vs
                    for r in [next((r for r in rs if r["video_id"] == v["id"] and re.search(rx, r["text"])), None)] if r]
            anchors[name] = {"videos": len(hits), "start_s": _q([h[0] for h in hits]), "start_share": _q([h[1] for h in hits])}
        pos = collections.Counter("top" if r["fc_pos"][1] < CANVAS[r["format"]][1] / 3 else
                                  "bottom" if r["fc_pos"][1] > 2 * CANVAS[r["format"]][1] / 3 else "middle" for r in rs)
        out["groups"][key] = {
            "videos": len(vs), "uploaded": [min(v["upload_date"] for v in vs), max(v["upload_date"] for v in vs)],
            "duration_s": _q([v["duration"] for v in vs]),
            "shots": _q([len(v["cuts"]) + 1 for v in vs]),
            "shot_s": _q([v["duration"] / (len(v["cuts"]) + 1) for v in vs]),
            "captions_per_video": _q([sum(r["video_id"] == v["id"] for r in rs) for v in vs]),
            "caption_s": _q([r["dur"] for r in rs]), "caption_chars": _q([len(r["text"].replace("\n", "")) for r in rs]),
            "caption_position": dict(pos), "parts": dict(collections.Counter(r["part"] for r in rs)),
            "sections": anchors,
            "common_lines": [t for t, _ in collections.Counter(r["text"] for r in rs if r["common_drafts"] >= 3).most_common(15)],
        }
    return out


_SPEC_HEADLINE_RE = re.compile(
    r"\d+\s*(?:마력|토크|만원|천만|억|리터|km|kwh|초|단|인치)|제로백|복합\s*연비|출고|트림|가격",
    re.I,
)


def shorts_headlines(n: int = 6, avoid: tuple = (), lines_path: pathlib.Path = LINES) -> list:
    """The headlines the channel's recent shorts keep above the picture (two lines, top third, at least half the short),
    newest first: the tone build_shorts.py asks agy to write hooks in. In youtube_lines.jsonl the two lines sit as two
    checked rows at the top of the same video; car-spec numbers and headlines naming `avoid` are left out."""
    if not lines_path.exists():
        return []
    tokens = {squash(t) for t in avoid if len(squash(t)) >= 2}
    rows = [json.loads(l) for l in lines_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_vid: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        if (r.get("format") == "shortform" and r.get("checked")
                and r["fc_pos"][1] < CANVAS["shortform"][1] / 3 and r["dur"] >= 0.5 * r["duration"]
                and not any(t in squash(r.get("draft", "")) or t in squash(r["text"]) for t in tokens)):
            by_vid[r["video_id"]].append(r)
    cands = []
    for vid, rs in by_vid.items():
        rs.sort(key=lambda r: (r["fc_pos"][1], r["start"]))
        if "\n" in rs[0]["text"]:
            pair = [ln.strip() for ln in rs[0]["text"].splitlines() if ln.strip()][:2]
        else:
            pair = []
            for r in rs:
                t = r["text"].replace("\n", " ").strip()
                if t and t not in pair:
                    pair.append(t)
                if len(pair) == 2:
                    break
        if len(pair) == 2:
            joined = f"{pair[0]}\n{pair[1]}"
            if not _SPEC_HEADLINE_RE.search(joined):
                cands.append((int(rs[0].get("upload_date") or 0), vid, joined))
    cands.sort(key=lambda x: (-x[0], x[1]))
    return list(dict.fromkeys(joined for _, _, joined in cands))[:n]


# --- run --------------------------------------------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=92)
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-agy", action="store_true")
    ap.add_argument("--redo", action="store_true", help="read uploads again even if datasets/youtube/<id>.json exists")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if not args.rebuild:
        uploads = meta_for(args.ids) if args.ids else list_uploads(args.days)
        for old in pathlib.Path(tempfile.gettempdir()).glob("ogyt_*_*"):  # frames a killed run left on the full drive C:
            try:  # another run may remove its own folder between glob and stat
                stale = time.time() - old.stat().st_mtime > 6 * 3600  # not a run still going
            except OSError:
                continue
            if stale:
                shutil.rmtree(old, ignore_errors=True)
        todo = [v for v in uploads if args.redo or not (PER_VIDEO / f"{v['id']}.json").exists()][:args.limit]
        print(f"{len(uploads)} uploads, {len(todo)} to read", flush=True)
        if not args.no_agy:  # uploads read before whose agy step failed or was skipped: only that step again
            for v in uploads:
                p = PER_VIDEO / f"{v['id']}.json"
                rec = json.loads(p.read_text(encoding="utf-8")) if v not in todo and p.exists() else None
                if rec and not rec.get("agy"):
                    agy_step(rec)
                    save(rec)
                    print(f"agy again {v['id']}: {'ok' if rec['agy'] else rec['note']}", flush=True)
        done = 0
        pool = cf.ThreadPoolExecutor(WORKERS)
        try:
            futs = {pool.submit(process, v, not args.no_agy): v for v in todo}
            for f in cf.as_completed(futs):
                v, done = futs[f], done + 1
                try:
                    rec = f.result()
                    kept = sum(c["caption"] is not False for c in rec["captions"])
                    print(f"[{done}/{len(todo)}] {v['upload_date']} {v['id']} {v['title'][:40]}: {kept} captions, "
                          f"{len(rec['cuts']) + 1} shots {rec['note']}", flush=True)
                except Exception as e:
                    print(f"[{done}/{len(todo)}] {v['id']} FAILED: {e}", flush=True)
        except KeyboardInterrupt:
            print("stopping after the uploads being read now", flush=True)
            pool.shutdown(wait=False, cancel_futures=True)
            raise
        pool.shutdown()
    videos, rows = write_summaries()
    print(f"{LINES.name}: {len(rows)} lines from {len(videos)} uploads; {STRUCTURE.name} written")


def _selftest() -> None:
    R = lambda t, text, y=0.85: {"t": t, "tag": "c", "text": text, "x": 0.1, "y": y, "w": 0.8, "h": 0.05}
    reads = [R(0, "넓게 부풀어 오른 리어 숄더"), R(0.5, "넓게뿌풀어 오른 리어 숄더"), R(1.0, "넓게 부풀어 오른 리어 숄더"),
             R(1.0, "亡쾨"), R(3.0, "Optic-Glass", 0.1),  # garbage and a one-frame logo are dropped
             R(5.0, "시공 전", 0.02), R(5.5, "시공 전", 0.02), R(5.0, "시공 후", 0.4), R(5.5, "시공 후", 0.4)]
    caps = captions(reads, 10.0)
    assert [c["text"] for c in caps] == ["넓게 부풀어 오른 리어 숄더", "시공 전", "시공 후"], caps
    assert caps[0]["start"] == 0 and caps[0]["end"] == 1.25 and caps[0]["frames"] == 3, caps[0]
    two = [{"start": 0, "end": 3, "x": 0.1, "y": 0.05, "w": 0.8, "h": 0.04, "text": "럭셔리의 기준이 다르다", "caption": True},
           {"start": 0, "end": 3, "x": 0.15, "y": 0.1, "w": 0.7, "h": 0.04, "text": "마이바흐의 존재감", "caption": True},
           {"start": 0, "end": 3, "x": 0.1, "y": 0.8, "w": 0.8, "h": 0.04, "text": "아래 자막", "caption": None},
           {"start": 0, "end": 3, "x": 0.1, "y": 0.5, "w": 0.8, "h": 0.04, "text": "간판", "caption": False}]
    assert [[c["text"] for c in b] for b in blocks(two)] == [["럭셔리의 기준이 다르다", "마이바흐의 존재감"], ["아래 자막"]]
    swap = [R(t, "시공 전", 0.02) for t in (0, 0.5, 1.0, 1.5)] + [R(t, "시공 후", 0.02) for t in (2.0, 2.5, 3.0)]
    assert [(c["text"], c["start"]) for c in captions(swap, 5.0)] == [("시공 전", 0), ("시공 후", 1.75)]  # one spot, new text
    side = [dict(R(t, txt, 0.02), x=x, w=0.1) for t in (0, 0.5) for txt, x in (("시공 전", 0.1), ("시공 후", 0.7))]
    assert sorted(c["text"] for c in captions(side, 5.0)) == ["시공 전", "시공 후"]  # side-by-side badges stay apart
    cap = lambda s, e, text, caption=True, frames=4, **kw: {"start": s, "end": e, "x": 0.1, "y": 0.85, "w": 0.8, "h": 0.05,
                                                             "frames": frames, "text": text, "readings": [[text, frames]],
                                                             "caption": caption, **kw}
    merged = merge_same([cap(0, 3, "광각미러가 꼭 필요한 이유", frames=6), cap(1, 2, "광각미러가 필요한 이유"),
                         cap(1, 2, "깨진글자", None, agy_stray="광각미러가 꼭 필요한 이유"), cap(6, 8, "광각미러가 꼭 필요한 이유"),
                         cap(20, 22, "광각미러가 꼭 필요한 이유"), cap(1, 2, "간판", False), cap(2, 3, "광각미러", x=0.6)])
    assert [(c["start"], c["end"], c["text"]) for c in merged] == [(0, 8, "광각미러가 꼭 필요한 이유"), (1, 2, "간판"),
                                                                   (20, 22, "광각미러가 꼭 필요한 이유")], merged
    pair = merge_same([cap(0, 3, "시공 전 시야"), cap(3, 5, "시공 후 시야"),
                       cap(0, 2, "깨진", None), cap(0, 2, "깨진", True, frames=2), cap(0.5, 2.5, "유트!극개人", None, x=0.2)])
    assert sorted((c["text"], c["caption"]) for c in pair) == [("깨진", True), ("시공 전 시야", True), ("시공 후 시야", True)], pair
    late = [dict(two[1], start=0), dict(two[0], start=0.25)]  # the top line read a frame after the bottom one
    assert [[c["text"] for c in b] for b in blocks(late)] == [["럭셔리의 기준이 다르다", "마이바흐의 존재감"]]
    assert quality("램프 진입이나") == 1 and quality("留,*j人공후") < MIN_QUALITY and not meaningful("亡")
    with tempfile.TemporaryDirectory() as td:
        lp = pathlib.Path(td) / "yt.jsonl"
        row = lambda vid, y, txt, dt="20261015": {"video_id": vid, "upload_date": dt, "format": "shortform", "checked": True,
                                                  "draft": "yt", "fc_pos": [540, y], "dur": 12.0, "duration": 15.0,
                                                  "start": 0.0, "text": txt}
        lp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
            row("v1", 326, "투명하게 다 보이는 클라쓰"), row("v1", 230, "사각지대 걱정 끝 🚨"),
            row("v2", 230, "최고출력 309마력"), row("v2", 326, "복합연비 14km"),
        ]), encoding="utf-8")
        assert shorts_headlines(6, lines_path=lp) == ["사각지대 걱정 끝 🚨\n투명하게 다 보이는 클라쓰"]
        assert shorts_headlines(6, avoid=("클라쓰",), lines_path=lp) == []
    print("youtube_lines selftest ok")


if __name__ == "__main__":
    sys.path.insert(0, str(WORK))
    main()
