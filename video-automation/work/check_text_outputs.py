"""The output check: a staged CapCut draft keeps the house rules and its scenario. Longform drafts: the scenario's
role rules (load_scenario), every scene and line in place, no transition next to a comparison scene, the BGM over the
whole cut, the caption style. Shorts: five timelines on the car's source with its own hooks and BGM.
The builders run it before deploying (check_draft(slug, variant)); a draft that fails stays staged.
Run after a build:  py check_text_outputs.py [slug ...] [--variant longform|wide1|shorts]
(no slug: every car; no --variant: every variant built for the car)"""
import json
import pathlib
import subprocess
import sys

WORK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(WORK))
import longform_common as lc  # noqa: E402
from portable_paths import OUTPUT_DIR, find_ffmpeg  # noqa: E402
import render_subtitles  # noqa: E402

fails = []
BUNDLED_FONT_FILES = {
    "Paperlogy-7Bold.ttf", "Paperlogy-9Black.ttf",
    "NotoSansKR-Bold-Static.ttf", "NotoSansKR-Regular.otf",
    "GalleryModern.otf", "BlackHanSans-Regular.ttf", "강원교육튼튼.ttf",
}


def check(cond, msg):
    if not cond:
        fails.append(msg)


def _probe_subtitled_mp4(mp4: pathlib.Path, label: str, tag_prefix: str = render_subtitles.SUBTITLE_META_PREFIX):
    probe = subprocess.run([find_ffmpeg(), "-hide_banner", "-i", str(mp4)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("Audio:" in probe.stderr, f"{label}: {mp4.name} has no audio/BGM stream")
    check(tag_prefix in probe.stderr, f"{label}: {mp4.name} is missing burned-in subtitle tag ({tag_prefix}) — rebuild required")


def capcut_texts(draft, stage_dir=None, preserve_template_style=False):
    base = pathlib.Path(stage_dir) if stage_dir is not None else (WORK / "capcut_stage")
    dc = json.loads((base / draft / "draft_content.json").read_text(encoding="utf-8"))
    mats = {t["id"]: t for t in dc["materials"]["texts"]}
    fx = {e["id"] for e in dc["materials"].get("effects", []) if e.get("type") in ("text_effect", "bloom")}
    segs = []
    for tr in dc["tracks"]:
        if tr["type"] != "text":
            continue
        spans = sorted((s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]) for s in tr["segments"])
        check(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), f"{draft}: overlapping segments on text track {tr['id']}")
        for s in tr["segments"]:
            m = mats.get(s["material_id"])
            check(m is not None, f"{draft}: text segment {s['id']} has no plain text material (template leftover?)")
            if m:
                segs.append((s, m, json.loads(m["content"])))
                if not preserve_template_style:
                    check(not (set(s.get("extra_material_refs", [])) & fx), f"{draft}: '{json.loads(m['content'])['text']}' still has a 花字 effect")
    check(not dc["materials"].get("text_templates"), f"{draft}: text_templates left in the draft")
    return dc, segs


WIDE1_TEXT_IDS = {"lt01", "w04a", "w04b", "wb1", "wb2", *(f"wc{i}" for i in range(1, 9)),
                  *(f"ws{i}" for i in range(1, 5)), *(f"wz{i}" for i in range(1, 5))}
WIDE1_GOLD_IDS = {"ws2", "ws4", "wz2", "wz4"}


def check_longform(slug, draft, variant="longform", stage_dir=None, scenario_name=None):
    try:
        scenario = lc.load_scenario(scenario_name or f"{slug}_{variant}")
    except ValueError as e:  # a role rule the scenario breaks (arrows, shot kind, plate on an arrow clip, ...)
        check(False, f"{draft}: {e}")
        return
    plan = scenario["lines"]
    preserve_tpl = bool(scenario["tpl"].get("preserve_template_style"))
    dc, segs = capcut_texts(draft, stage_dir=stage_dir, preserve_template_style=preserve_tpl)
    vpath = {v["id"]: v["path"] for v in dc["materials"]["videos"]}
    seg_of = {pathlib.Path(vpath.get(s["material_id"], "")).name: s for tr in dc["tracks"] if tr["type"] == "video" for s in tr["segments"]}
    vsegs = {name: s["target_timerange"] for name, s in seg_of.items()}
    transitions = {t["id"] for t in dc["materials"].get("transitions", [])}
    scenes = scenario["scenes"]
    for i, sc in enumerate(scenes):  # each scene's clip sits in its CapCut video slot at the scenario timing
        start, end = lc._frame_us(sc["start"]), lc._frame_us(sc["start"] + sc["dur"])
        clip = f"lf_{sc['id']}_{sc['name']}.mp4"
        check(vsegs.get(clip) == {"start": start, "duration": end - start}, f"{draft}: scene {sc['id']} video slot timing")
        nxt = scenes[i + 1] if i + 1 < len(scenes) else None  # rule 2.5: none into, out of or inside the comparison
        if clip in seg_of and nxt and (sc["compare"] or nxt["compare"]):
            check(not set(seg_of[clip].get("extra_material_refs", [])) & transitions, f"{draft}: {sc['id']}와 {nxt['id']} 사이에 전환 효과 (비교 구간, 규칙 2.5)")
    audio = [g for tr in dc["tracks"] if tr["type"] == "audio" for g in tr["segments"]]  # rule 2.6: BGM over the whole cut
    check(bool(audio) and all(g["target_timerange"] == {"start": 0, "duration": dc["duration"]} for g in audio), f"{draft}: BGM이 영상 전체를 덮지 않습니다 (오디오 {len(audio)}개, 규칙 2.6)")
    w, h = dc["canvas_config"]["width"], dc["canvas_config"]["height"]
    check(len(segs) > 0 and len(segs) == len(plan), f"{draft}: {len(segs)} text segments for {len(plan)} plan rows")
    unused = list(segs)
    for row in plan:
        start, end = lc._frame_us(row["start"]), lc._frame_us(row["start"] + row["dur"])
        hit = next((x for x in unused if x[2]["text"] == row["text"] and x[0]["target_timerange"]["start"] == start), None)
        check(hit is not None, f"{draft}: {row['id']} '{row['text']}' at {start}us missing")
        if not hit:
            continue
        unused.remove(hit)
        seg, mat, content = hit
        style = content["styles"][0]
        check(seg["target_timerange"]["duration"] == end - start, f"{draft}: {row['id']} duration")
        cy = row["fc_pos"][1] - lc.FC_CENTER_ABOVE_Y * row["size"]
        tf = seg["clip"]["transform"]
        check(abs(tf["x"] - (row["fc_pos"][0] - w / 2) / (w / 2)) < 1e-3 and abs(tf["y"] - (h / 2 - cy) / (h / 2)) < 1e-3, f"{draft}: {row['id']} position {tf}")
        rgb = [int(row["color"][i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
        has_fx = bool(style.get("effectStyle"))
        if not has_fx:
            check(style["fill"]["content"]["solid"]["color"] == rgb and mat["text_color"] == row["color"], f"{draft}: {row['id']} colour")
        else:
            check(mat["text_color"] == row["color"], f"{draft}: {row['id']} colour")
        check(style["range"] == [0, len(row["text"])] and len(content["styles"]) == 1, f"{draft}: {row['id']} style range")
        box = bool(row.get("box", not preserve_tpl))
        if preserve_tpl:
            check(not box and not mat.get("background_style"), f"{draft}: {row['id']} wide1 template must not have opaque black box")
            if not has_fx:
                check(bool(style.get("strokes")) == (row["stroke_w"] > 0), f"{draft}: {row['id']} outline")
        else:
            check(bool(style.get("strokes")) == (row["stroke_w"] > 0), f"{draft}: {row['id']} outline")
            check(row["stroke_w"] == 0 or not box, f"{draft}: {row['id']} has both an outline and the black box")
            check((mat.get("background_style") == 1 and mat.get("background_color") == "#000000" and mat.get("background_alpha") == 1.0)
                  if box else not mat.get("background_style"), f"{draft}: {row['id']} black box")
            flag = mat.get("check_flag", 0)  # CapCut's feature bits must agree with the styles: 8 stroke, 16 box, 32 shadow, 64 glow
            check(bool(flag & 8) == (row["stroke_w"] > 0) and bool(flag & 16) == box and bool(flag & 32) == bool(row.get("shadow"))
                  and not flag & 64, f"{draft}: {row['id']} check_flag {flag}")
        check(not style.get("bold"), f"{draft}: {row['id']} synthetic bold")
        fonts = mat.get("fonts") or [{}]
        font_name = pathlib.Path(mat["font_path"]).name
        expected_font_ok = (font_name in BUNDLED_FONT_FILES) if preserve_tpl else mat["font_path"].endswith("Paperlogy-7Bold.ttf")
        check(expected_font_ok and len(mat.get("fonts", [])) == 1 and fonts[0].get("id")
              and style["font"] == {"id": fonts[0]["id"], "path": fonts[0]["path"]} == {"id": fonts[0]["id"], "path": mat["font_path"]},
              f"{draft}: {row['id']} font ({{id, path}} in fonts and styles[].font, got {font_name})")
    if scenario["template"] == "opticglass_wide1":
        check((w, h) == (1920, 1080), f"{draft}: opticglass_wide1 canvas {w}x{h} != 1920x1080")
        check(dc["duration"] == 57733333, f"{draft}: opticglass_wide1 duration {dc['duration']} != 57733333")
        check([sc["id"] for sc in scenes] == [f"w{i:02d}" for i in range(13)], f"{draft}: opticglass_wide1 scenes must be w00..w12")
        check(not transitions, f"{draft}: opticglass_wide1 must have 0 transitions (got {len(transitions)})")
        check({row["id"] for row in plan} == WIDE1_TEXT_IDS, f"{draft}: opticglass_wide1 must have all 21 text slots")
        for row in plan:
            want_color = "#F4C70F" if row["id"] in WIDE1_GOLD_IDS else "#FFFFFF"
            check(row["color"] == want_color, f"{draft}: {row['id']} color {row['color']} != {want_color}")
        stickers = dc["materials"].get("stickers", [])
        sticker_ids = {st.get("id") for st in stickers}
        check(len(stickers) == 2 and all(st.get("name") == "Guidance EN - Arrow" for st in stickers),
              f"{draft}: opticglass_wide1 must have 2 'Guidance EN - Arrow' sticker materials (got {len(stickers)})")
        for st in stickers:
            st_path = st.get("path", "")
            check(bool(st_path) and pathlib.Path(st_path).is_absolute()
                  and not any(u in st_path for u in ("정민석", "회장님", "C:/Users/wish/", "C:/Users/melly/")),
                  f"{draft}: sticker path invalid or has foreign user prefix: {st_path}")
        expected_sticker_spans = [(22600000, 2966666), (32600000, 2966666)]
        sticker_segs = [seg for tr in dc["tracks"] if tr["type"] == "sticker" for seg in tr["segments"]]
        got_sticker_spans = sorted((seg["target_timerange"]["start"], seg["target_timerange"]["duration"]) for seg in sticker_segs)
        check(got_sticker_spans == expected_sticker_spans,
              f"{draft}: opticglass_wide1 sticker segments {got_sticker_spans} != {expected_sticker_spans}")
        for seg in sticker_segs:
            t0 = seg["target_timerange"]["start"]
            check(seg.get("material_id") in sticker_ids, f"{draft}: sticker segment references missing material {seg.get('material_id')}")
            check(0 <= t0 and t0 + seg["target_timerange"]["duration"] <= dc["duration"], f"{draft}: sticker segment out of bounds")
    if stage_dir is None:
        import drive_index
        mdir = drive_index.media_dir(slug)
        mp4 = mdir / f"{slug}_{variant}.mp4"
        if mp4.exists():
            _probe_subtitled_mp4(mp4, draft)
        out_mp4 = OUTPUT_DIR / slug / f"{slug}_optic_{variant}.mp4"
        if out_mp4.exists():
            _probe_subtitled_mp4(out_mp4, draft)


def check_shorts(slug, draft):
    """build_shorts.py's project: all 5 timelines (including 비트) have hook text, BGM, and 5 subtitled MP4s."""
    stage = WORK / "capcut_stage" / draft
    project = json.loads((stage / "Timelines" / "project.json").read_text(encoding="utf-8"))
    tls = [t for t in project["timelines"] if not t.get("is_marked_delete")]
    check(len(tls) == 5, f"{draft}: {len(tls)} timelines, 5 expected")
    tpl_texts = {json.loads(m["content"])["text"] for f in (lc.SCENARIOS_DIR / "templates" / "shorts_optic" / "Timelines").glob("*/draft_content.json")
                 for m in json.loads(f.read_text(encoding="utf-8"))["materials"].get("texts", [])}
    root = json.loads((stage / "draft_content.json").read_text(encoding="utf-8"))
    check(root["id"] == project["main_timeline_id"], f"{draft}: the root draft is not the main timeline")
    sources = set()
    for t in tls:
        dc = json.loads((stage / "Timelines" / t["id"] / "draft_content.json").read_text(encoding="utf-8"))
        vids = {v["id"]: v for v in dc["materials"]["videos"]}
        check(dc["duration"] > 0, f"{draft} {t['name']}: empty")
        for v in vids.values():
            check(pathlib.Path(v["path"]).exists(), f"{draft} {t['name']}: missing media {v['path']}")
            if v["type"] == "video":
                sources.add(v["path"])
        t_segs = 0
        for tr in dc["tracks"]:
            if tr["type"] == "text":
                t_segs += len(tr["segments"])
            for g in tr["segments"]:
                v = vids.get(g["material_id"])
                if tr["type"] == "video" and v and v["type"] == "video":
                    st = g["source_timerange"]
                    check(st["start"] + st["duration"] <= v["duration"], f"{draft} {t['name']}: plays past the end of {pathlib.Path(v['path']).name}")
        texts = dc["materials"].get("texts", [])
        check(len(texts) >= 1 and t_segs >= 1, f"{draft} {t['name']}: missing subtitle text (rule 2.6: all 5 timelines require subtitles)")
        for m in texts:
            text = json.loads(m["content"])["text"]
            check(text.strip() and text not in tpl_texts, f"{draft} {t['name']}: the template's own hook is still there ('{text[:20]}')")
    for src in sources:  # the BGM is mixed into the source clip (the template has no audio track)
        probe = subprocess.run([find_ffmpeg(), "-hide_banner", "-i", src], capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("Audio:" in probe.stderr, f"{draft}: {pathlib.Path(src).name} has no BGM")
    shorts_dir = OUTPUT_DIR / slug / "shorts"
    expected_chapters = ["비트", "외관", "시공 전", "시공 후", "전후 비교"]
    for idx, ch in enumerate(expected_chapters, start=1):
        mp4 = shorts_dir / render_subtitles.short_mp4_name(idx, slug, ch)
        check(mp4.exists() and mp4.stat().st_size >= 10_000, f"{draft}: missing subtitled shorts MP4 {mp4.name}")
        if mp4.exists():
            _probe_subtitled_mp4(mp4, f"{draft} {ch}")


VARIANTS = ("longform", "wide1", "shorts")  # scenarios/<slug>_<variant>.json -> capcut_stage/hermes_<slug>_optic_<variant>


def staged(slug, v):
    import drive_index
    if v == "shorts":
        has_sc = (lc.SCENARIOS_DIR / f"{slug}_longform.json").exists() or (lc.SCENARIOS_DIR / f"{slug}_wide1.json").exists()
    else:
        has_sc = (lc.SCENARIOS_DIR / f"{slug}_{v}.json").exists()
    return ((WORK / "capcut_stage" / f"hermes_{slug}_optic_{v}").exists() and has_sc
            and (v != "shorts" or drive_index.media_dir(slug).exists()))


def check_draft(slug, variant):
    """The failures of one staged draft (empty = it keeps the rules)."""
    del fails[:]
    draft = f"hermes_{slug}_optic_{variant}"
    if variant == "shorts":
        check_shorts(slug, draft)
    else:
        check_longform(slug, draft, variant)
    return list(fails)


def main():
    argv = sys.argv[1:]
    only = argv.pop(argv.index("--variant") + 1) if "--variant" in argv else None
    argv = [a for a in argv if a != "--variant"]
    # no slug: every car whose draft has been built here (a fresh PC from the release zip has no capcut_stage yet)
    slugs = sorted({p.name.removesuffix("_longform.json").removesuffix("_wide1.json")
                    for pat in ("*_longform.json", "*_wide1.json") for p in lc.SCENARIOS_DIR.glob(pat)})
    built = [s for s in slugs if any(staged(s, v) for v in VARIANTS)]
    if not argv and not built:
        print("OK: no built drafts to check yet (build a car first)")
    found = []
    for slug in argv or built:
        for v in [only] if only else [v for v in VARIANTS if staged(slug, v)]:
            found += check_draft(slug, v)
    print("\n".join(found) if found else "OK: every output keeps the rules and its scenario")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
