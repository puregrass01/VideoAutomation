"""Extracts an OpticGlass longform CapCut draft into work/scenarios/templates/<key>/ for the longform builders:
- a copy of its timeline and shell files, so builds never read the live draft (a newer CapCut may re-save it encrypted;
  HERMES.md: templates are copies of plaintext drafts made on this PC)
- template.json: track roles, the video slots a scenario's scenes fill (their default timing) and the text slots its
  lines borrow animations and default timing/position/style from, in scenario units (px on the 1920x1080 canvas).
Drafts laid out differently from the polestar family are brought to the builder's layout first (normalize): the outro
on the end of the main track gets its own track, a music clip parked off-canvas on a video track becomes an audio track,
and the slots' zoom keyframes (Ken Burns on stills) go.
usage: py extract_template.py "<draft folder>" <key>
"""
import copy
import json
import pathlib
import sys
import uuid

from longform_common import CC_SIZE_PER_FC_PX, FC_CENTER_ABOVE_Y, SCENARIOS_DIR
from portable_paths import DRAFT_ROOT

SHELL_FILES = ("draft_meta_info.json", "draft_agency_config.json", "draft_biz_config.json", "timeline_layout.json")
BASE = SCENARIOS_DIR / "templates" / "polestar4_optic"  # the audio track and plaintext meta a draft without them borrows
# Line ids per template family -> a phrase its template text contains. lt01 (car title) is the first plain text in the
# first 2 s. A repeated phrase (시공 전/후) takes the next unused segment in time order, as the text pass does. A draft
# uses the family whose phrases it contains most.
FAMILIES = {
    "polestar": [("lt05a", "순정미러의 좁은 시야"), ("lt05b", "운행 시 차선"), ("lt06a", "초보운전자에게는"),
                 ("lt06b", "혼잡한 도로에서"), ("lt07", "운전고수도"), ("lt08", "옵틱글래스 광각미러로"),
                 ("lt09a", "사각지대 해소"), ("lt09b", "편리해진 차선"),
                 ("lt10", "시공 전"), ("lt11", "시공 후"), ("lt12a", "시공 전"), ("lt12b", "시공 후")],
    # 「옵틱글래스 광각미러 템플릿 1」 (2026 Tesla Model X, 57.7 s): badges, 8 captions, split labels, 4 closing lines
    "wide1": [("wb1", "광각미러 설치 전"), ("wb2", "광각미러 설치 후"),
              ("wc1", "사이드미러를 믿지 못해"), ("wc2", "불안감에 휩싸여"), ("wc3", "조수석 뒤쪽에서"), ("wc4", "대형 사고의 주인공"),
              ("wc5", "파노라마처럼"), ("wc6", "스캔하는 것처럼"), ("wc7", "칼치기 차량도"), ("wc8", "주차부터 타협 없는"),
              ("ws1", "시공 전"), ("ws2", "시공 후"), ("ws3", "시공 전"), ("ws4", "시공 후"),
              ("wz1", "넓은 시야에서"), ("wz2", "광각미러를 설치하세요"), ("wz3", "시야 업그레이드를"), ("wz4", "광각미러로 느껴보세요")],
}


def sec(us):
    return round(us / 1e6, 3)


def _slot_color(mat: dict, content: dict) -> str:
    """Line colour: mat['text_color'], or the run's solid fill when text_color stays white on a coloured line (wide1 wz2/wz4)."""
    tc = (mat.get("text_color") or "#FFFFFF").upper()[:7]
    if tc == "#FFFFFF":
        styles = content.get("styles") or []
        fc = (styles[0].get("fill", {}).get("content", {}).get("solid", {}).get("color") if styles else None) or []
        if len(fc) >= 3 and max(fc[:3]) - min(fc[:3]) > 0.1:
            return "#{:02X}{:02X}{:02X}".format(*(round(v * 255) for v in fc[:3]))
    return tc


def text_slot(seg, mat, canvas_w, canvas_h):
    """A template text segment as a scenario line: its timing, position and size (inverse of
    longform_common._style_capcut_text) and its colour (text_color: the template's 花字 presets hide the fill).
    The text pass swaps 花字 for the house look (rules 2.6): no outline and no shadow, on an opaque black box."""
    content = json.loads(mat["content"])
    size = content["styles"][0].get("size", mat.get("font_size", 10)) * seg["clip"]["scale"]["x"] / CC_SIZE_PER_FC_PX
    tf, t = seg["clip"]["transform"], seg["target_timerange"]
    return {"start": sec(t["start"]), "dur": sec(t["duration"]),
            "fc_pos": [round(canvas_w / 2 + tf["x"] * canvas_w / 2), round(canvas_h / 2 - tf["y"] * canvas_h / 2 + FC_CENTER_ABOVE_Y * size)],
            "size": round(size), "color": _slot_color(mat, content),
            "stroke_w": 0.0, "shadow": False,
            "font": "Paperlogy", "font_style": "7 Bold",  # the house font every line is rendered in
            "text": content["text"].strip()}


def plaintext(p: pathlib.Path) -> bool:
    return p.exists() and p.read_bytes()[:1] == b"{"


def timeline_file(src: pathlib.Path) -> pathlib.Path:
    """The draft's main timeline as plaintext JSON: its Timelines copy (the largest, as CapCut 9.x keeps the edit
    there), else the root draft_content.json when the Timelines copies are encrypted (a cloud-downloaded draft) and the
    root is that same main timeline."""
    tl = max((src / "Timelines").glob("*/draft_content.json"), key=lambda p: p.stat().st_size, default=None)
    if tl and plaintext(tl):
        return tl
    root, project = src / "draft_content.json", src / "Timelines" / "project.json"
    main_id = json.loads(project.read_text(encoding="utf-8")).get("main_timeline_id") if plaintext(project) else None
    if plaintext(root) and (main_id is None or json.loads(root.read_text(encoding="utf-8"))["id"] == main_id):
        print(f"  {src.name}: Timelines copies are encrypted; using the plaintext root draft_content.json (main timeline)")
        return root
    raise SystemExit(f"{src} has no plaintext main timeline; only plaintext drafts can be templates (decrypting is against CapCut's terms)")


def normalize(dc: dict) -> dict:
    """Brings a draft to the builder's layout (see the module docstring). Returns the changes made."""
    tracks, M = dc["tracks"], dc["materials"]
    vids = {v["id"]: v for v in M["videos"]}
    path_of = lambda s: vids.get(s["material_id"], {}).get("path", "")
    video = [t for t in tracks if t["type"] == "video"]
    main = max(video, key=lambda t: len(t["segments"]))
    done = {}
    if not any("아웃트로" in path_of(s) for t in video if t is not main for s in t["segments"]) and "아웃트로" in path_of(main["segments"][-1]):
        outro = copy.deepcopy(main)
        outro.update({"id": str(uuid.uuid4()).upper(), "flag": 2, "segments": [main["segments"].pop()]})
        tracks.append(outro)
        done["outro"] = "moved off the main track"
    off = lambda s: abs(s["clip"]["transform"]["x"]) > 1 or abs(s["clip"]["transform"]["y"]) > 1
    parked = [t for t in video if t is not main and t["segments"] and all(off(s) for s in t["segments"])]
    if parked:  # music carried by a video clip outside the frame: the builder re-points only audio tracks to the BGM
        dc["tracks"] = tracks = [t for t in tracks if t not in parked]
        done["parked music"] = [path_of(s).rsplit("/", 1)[-1] for t in parked for s in t["segments"]]
    if not any(t["type"] == "audio" for t in tracks):
        base = json.loads((BASE / "draft_content.json").read_text(encoding="utf-8"))
        bm = {x["id"]: (k, x) for k, v in base["materials"].items() if isinstance(v, list) for x in v if isinstance(x, dict) and "id" in x}
        audio = copy.deepcopy(next(t for t in base["tracks"] if t["type"] == "audio"))
        for seg in audio["segments"]:  # the audio material and every material its segment refers to
            for ref in [seg["material_id"], *seg.get("extra_material_refs", [])]:
                if ref in bm and not any(x.get("id") == ref for x in M.get(bm[ref][0], [])):
                    M.setdefault(bm[ref][0], []).append(copy.deepcopy(bm[ref][1]))
            if dc.get("duration"):
                seg["target_timerange"] = {"start": 0, "duration": dc["duration"]}
                seg["source_timerange"] = {"start": 0, "duration": dc["duration"]}
        tracks.append(audio)
        done["audio"] = f"track and BGM material from {BASE.name}"
    for seg in main["segments"]:
        if seg.get("common_keyframes") or seg.get("keyframe_refs"):
            seg["common_keyframes"], seg["keyframe_refs"] = [], []
            done["keyframes"] = "cleared on the main slots"
    return done


def extract(draft: str, key: str) -> pathlib.Path:
    src = DRAFT_ROOT / draft
    tl = timeline_file(src)
    dc = json.loads(tl.read_text(encoding="utf-8"))
    for what, how in normalize(dc).items():
        print(f"  normalized {what}: {how}")
    tracks, vids = dc["tracks"], {v["id"]: v for v in dc["materials"]["videos"]}
    start = lambda s: s["target_timerange"]["start"]
    end = lambda s: start(s) + s["target_timerange"]["duration"]

    video = [i for i, t in enumerate(tracks) if t["type"] == "video"]
    main = max(video, key=lambda i: len(tracks[i]["segments"]))
    outro = next((i for i in video if i != main and any("아웃트로" in vids.get(s["material_id"], {}).get("path", "") for s in tracks[i]["segments"])), None)
    if outro is None:
        raise SystemExit(f"{draft}: no outro track (a video track with an '아웃트로' clip); not an OpticGlass longform draft?")
    main_segs, outro_seg = tracks[main]["segments"], tracks[outro]["segments"][-1]
    assert main_segs == sorted(main_segs, key=start), "main track segments are out of time order"
    # The outro slot starts where the last main slot ends (templates overlap it by a frame or two) and keeps its end
    slots = [{"start": sec(start(s)), "dur": sec(s["target_timerange"]["duration"])} for s in main_segs]
    slots.append({"start": sec(end(main_segs[-1])), "dur": sec(end(outro_seg) - end(main_segs[-1]))})

    texts = {t["id"]: t for t in dc["materials"].get("texts", [])}
    pool = sorted(((s, texts[s["material_id"]]) for t in tracks if t["type"] == "text" for s in t["segments"] if s["material_id"] in texts),
                  key=lambda p: start(p[0]))
    text_of = lambda m: json.loads(m["content"])["text"]
    title = next((text_of(m).strip() for s, m in pool if start(s) < 2_000_000 and text_of(m).strip()), None)
    family = max(FAMILIES, key=lambda f: sum(any(ph in text_of(m) for _, m in pool) for _, ph in FAMILIES[f]))
    w, h = dc["canvas_config"]["width"], dc["canvas_config"]["height"]
    text_slots = {}
    for line_id, phrase in ([("lt01", title)] if title else []) + FAMILIES[family]:
        hit = next((i for i, (s, m) in enumerate(pool) if phrase in text_of(m)), None)
        if hit is not None:
            text_slots[line_id] = text_slot(*pool.pop(hit), w, h)
    if family == "wide1":
        tts = {tt["id"]: tt for tt in dc["materials"].get("text_templates", [])}
        tt_seg = next((s for t in tracks if t["type"] == "text" for s in t["segments"] if s["material_id"] in tts), None)
        if tt_seg is not None:
            sub = [text_of(texts[r["text_material_id"]]).strip()
                   for r in tts[tt_seg["material_id"]].get("text_info_resources", [])
                   if r.get("text_material_id") in texts]
            t0, td = sec(tt_seg["target_timerange"]["start"]), sec(tt_seg["target_timerange"]["duration"])
            card_defaults = [
                ("w04a", "BY OPTICGLASS", [960, 420], 38),
                ("w04b", "광각미러가 꼭 필요한 이유", [960, 535], 78),
            ]
            for idx, (cid, default_txt, pos, sz) in enumerate(card_defaults):
                txt = sub[idx] if idx < len(sub) and sub[idx] else default_txt
                text_slots[cid] = {"start": t0, "dur": td, "fc_pos": pos, "size": sz, "color": "#FFFFFF",
                                   "stroke_w": 0.0, "shadow": False, "font": "Paperlogy", "font_style": "7 Bold", "text": txt}
            ordered = {k: text_slots[k] for k in ["lt01", "w04a", "w04b"] if k in text_slots}
            ordered.update({k: v for k, v in text_slots.items() if k not in ordered})
            text_slots = ordered

    out_dir = SCENARIOS_DIR / "templates" / key
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "draft_content.json").write_text(json.dumps(dc, ensure_ascii=False), encoding="utf-8")
    for f in SHELL_FILES:
        if plaintext(src / f):
            (out_dir / f).write_bytes((src / f).read_bytes())
        elif f == "draft_meta_info.json":  # the builder rewrites its ids, paths and media bin; any plaintext one serves
            (out_dir / f).write_bytes((BASE / f).read_bytes())
            print(f"  {f} is encrypted or missing; copied {BASE.name}'s")
    row = lambda v: json.dumps(v, ensure_ascii=False)
    # a draft with no transitions at all keeps none (longform_common.check_scene_rules: every scene then avoids them)
    body = [f'  "draft": {row(draft)},', f'  "timeline": {row(dc["id"])},',
            f'  "transitions": {row(bool(dc["materials"].get("transitions")))},',
            *( [f'  "keep_stickers": true,'] if family == "wide1" and dc["materials"].get("stickers") else [] ),
            f'  "canvas": {row([w, h])},',
            f'  "tracks": {row({"main": main, "outro": outro, "overlay": [i for i in video if i not in (main, outro)]})},',
            '  "slots": [\n' + ",\n".join("    " + row(s) for s in slots) + "\n  ],",
            '  "text_slots": {\n' + ",\n".join(f"    {row(k)}: {row(v)}" for k, v in text_slots.items()) + "\n  }"]
    (out_dir / "template.json").write_text("{\n" + "\n".join(body) + "\n}\n", encoding="utf-8")
    print(f"{key}: {family} family, {len(slots)} video slots ({sec(end(outro_seg))} s), text slots {list(text_slots)} -> {out_dir}")
    return out_dir


if __name__ == "__main__":
    extract(sys.argv[1], sys.argv[2])
