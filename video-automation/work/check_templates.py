"""Builds the Cybertruck CapCut draft (build_longform.build_capcut) on every other template in work/scenarios/templates into a temp folder (no deploy,
no project files touched) and checks it follows each one: track roles, slot timing, length, the text slots used as
line defaults, no 花字/text_templates left. Run after adding a template:  py check_templates.py"""
import atexit
import json
import pathlib
import shutil
import sys
import tempfile

WORK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(WORK))
import longform_common as lc  # noqa: E402
import build_longform  # noqa: E402
import check_text_outputs as cto  # noqa: E402
import make_scenario  # noqa: E402

tmp = pathlib.Path(tempfile.mkdtemp())
atexit.register(shutil.rmtree, tmp, True)  # also on sys.exit and on an exception
shutil.copytree(lc.SCENARIOS_DIR / "templates", tmp / "templates")
base = json.loads((lc.SCENARIOS_DIR / "cybertruck_longform.json").read_text(encoding="utf-8"))
lc.SCENARIOS_DIR = tmp
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


# A line that only gives text where the template has no slot for it must be refused with a clear message
bad = json.loads(json.dumps(base))
bad["template"] = "bmw_aceman_optic"
bad["lines"][0] = {"id": "lt01", "text": "2026 테슬라 사이버트럭"}
(tmp / "bad.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
try:
    lc.load_scenario("bad")
    fails.append("aceman lt01 without a slot was accepted")
except ValueError as e:
    print("refused as expected:", e)

longform = lambda d: "slots" in json.loads((d / "template.json").read_text(encoding="utf-8"))  # not shorts_optic (build_shorts.py)
for key in sorted(d.name for d in (tmp / "templates").iterdir() if d.name != base["template"] and longform(d)):
    sc = json.loads(json.dumps(base))
    sc["template"] = key
    slots = json.loads((tmp / "templates" / key / "template.json").read_text(encoding="utf-8"))["text_slots"]
    sc["lines"] = [{"id": l["id"], "text": l["text"]} if l["id"] in slots else l for l in sc["lines"]]
    (tmp / f"test_{key}.json").write_text(json.dumps(sc, ensure_ascii=False), encoding="utf-8")
    s = lc.load_scenario(f"test_{key}")
    tpl = s["tpl"]
    car = build_longform.Car("cybertruck", s, draft_name=f"test_{key}")
    prepared = [{"id": x["id"], "start": x["start"], "dur": x["dur"], "path": car.media / f"lf_{x['id']}_{x['name']}.mp4",
                 "is_split_compare": "split" in x or x.get("compare", False)} for x in s["scenes"]]
    build_longform.build_capcut(car, prepared, stage_dir=tmp / "stage")
    dc = json.loads((tmp / "stage" / f"test_{key}" / "draft_content.json").read_text(encoding="utf-8"))
    M, T, roles = dc["materials"], dc["tracks"], tpl["tracks"]
    vpath = {v["id"]: pathlib.Path(v["path"]).name for v in M["videos"]}
    seg_at = {vpath.get(g["material_id"]): (i, g["target_timerange"]) for i, t in enumerate(T) if t["type"] == "video" for g in t["segments"]}
    for x in s["scenes"]:  # scene timing: the template slot's unless the scenario gives its own (the 80-100 s cut does)
        a, b = lc._frame_us(x["start"]), lc._frame_us(x["start"] + x["dur"])
        got = seg_at.get(f"lf_{x['id']}_{x['name']}.mp4")
        want_track = roles["outro"] if x is s["scenes"][-1] else roles["main"]
        check(got == (want_track, {"start": a, "duration": b - a}), f"{key}: {x['id']} slot {got}")
    check([len(T[i]["segments"]) for i in roles["overlay"]] == [1] + [0] * (len(roles["overlay"]) - 1), f"{key}: overlays not cleared / logo missing")
    check(dc["duration"] == lc._frame_us(car.total_s) == lc._frame_us(s["scenes"][-1]["start"] + s["scenes"][-1]["dur"]), f"{key}: length")
    check(all(g["target_timerange"] == {"start": 0, "duration": dc["duration"]} for t in T if t["type"] == "audio" for g in t["segments"]), f"{key}: BGM not covering the whole cut")
    texts = {t["id"]: json.loads(t["content"])["text"] for t in M["texts"]}
    tsegs = [(texts.get(g["material_id"]), g["target_timerange"]["start"]) for t in T if t["type"] == "text" for g in t["segments"]]
    check(len(tsegs) == len(s["lines"]) and None not in [t for t, _ in tsegs], f"{key}: {len(tsegs)} text segments for {len(s['lines'])} lines")
    for line in s["lines"]:
        check((line["text"], lc._frame_us(line["start"])) in tsegs, f"{key}: {line['id']} not at {line['start']}")
        if line["id"] in slots:
            check(line["start"] == slots[line["id"]]["start"] and line["fc_pos"] == slots[line["id"]]["fc_pos"], f"{key}: {line['id']} defaults")
    fx = {e["id"] for e in M.get("effects", []) if e.get("type") in ("text_effect", "bloom")}
    check(not M.get("text_templates") and (bool(tpl.get("preserve_template_style"))
          or not any(set(g.get("extra_material_refs", [])) & fx for t in T if t["type"] == "text" for g in t["segments"])),
          f"{key}: 花字 or text_template left")
    if key == "porsche997_optic":
        check(tpl.get("transitions") is True and len(tpl["slots"]) == 18 and roles["outro"] == 8, f"{key}: metadata mismatch")
        check(len(slots) == 13 and "lt01" in slots and "lt12b" in slots, f"{key}: expected 13 text_slots")
        tr_ids = {t["id"] for t in M.get("transitions", [])}
        check(bool(tr_ids), f"{key}: expected transitions on non-compare scenes")
        main_segs = {vpath.get(g["material_id"]): g for g in T[roles["main"]]["segments"]}
        for idx, x in enumerate(s["scenes"][:-1]):
            nxt = s["scenes"][idx + 1]
            g = main_segs.get(f"lf_{x['id']}_{x['name']}.mp4")
            if g and (x["compare"] or nxt["compare"]):
                check(not (set(g.get("extra_material_refs", [])) & tr_ids), f"{key}: transition adjacent to compare {x['id']}->{nxt['id']}")
    print(f"{key}: {car.total_s}s, outro track {roles['outro']} at {s['scenes'][-1]['start']}s, {len(tsegs)} lines, "
          f"lt09a from template at {next(l['start'] for l in s['lines'] if l['id'] == 'lt09a')}s")

# Native opticglass_wide1 validation: template.json + skeleton.json + make_scenario.plan() + build_capcut + check_text_outputs
w1_dir = tmp / "templates" / "opticglass_wide1"
w1_tpl = json.loads((w1_dir / "template.json").read_text(encoding="utf-8"))
w1_skel = json.loads((w1_dir / "skeleton.json").read_text(encoding="utf-8"))
w1_shell_dc = json.loads((w1_dir / "draft_content.json").read_text(encoding="utf-8"))
check(w1_tpl.get("canvas") == [1920, 1080] and w1_tpl.get("transitions") is False and w1_tpl.get("keep_stickers") is True,
      "opticglass_wide1: template flags/canvas mismatch")
check(len(w1_tpl["slots"]) == 13 and round(w1_tpl["slots"][-1]["start"] + w1_tpl["slots"][-1]["dur"], 3) == 57.733,
      "opticglass_wide1: expected 13 slots totaling 57.733s")
check(len(w1_tpl["text_slots"]) == 21 and {"lt01", "w04a", "w04b", "wb1", "wb2"}.issubset(w1_tpl["text_slots"]),
      "opticglass_wide1: expected 21 text_slots including w04a/w04b")
for tid, tslot in w1_tpl["text_slots"].items():
    want_c = "#F4C70F" if tid in ("ws2", "ws4", "wz2", "wz4") else "#FFFFFF"
    check(tslot["color"] == want_c, f"opticglass_wide1: template text_slot {tid} color {tslot['color']} != {want_c}")
check(w1_shell_dc["duration"] == 57733333, "opticglass_wide1: shell draft_content duration != 57733333")
check(all(g["target_timerange"] == {"start": 0, "duration": 57733333}
          for t in w1_shell_dc["tracks"] if t["type"] == "audio" for g in t["segments"]),
      "opticglass_wide1: shell audio segment must cover 57.733s")

cand = lambda src, t, kind, score=5: {"src": src, "t": t, "len": 30.0, "kind": kind, "score": score, "box": None, "size": (3840, 2160), "photo": False}
real_stills = make_scenario.stills
make_scenario.stills = lambda slug, review: [cand(f"{k}{i}.mov", 5, k) for k in ("car_exterior", "car_detail", "mirror_before", "mirror_after") for i in range(6)]
try:
    w1_scenes = make_scenario.plan("cybertruck", {}, w1_skel)
finally:
    make_scenario.stills = real_stills
for x in w1_scenes:
    if lc.ROLES[x["role"]].get("arrows"):
        x["arrows"] = [[0, 0, 1, 0, 100]] * 4
w1_lines = [{"id": l["id"], "text": "2026 테슬라 사이버트럭" if l["id"] == "lt01" else l["text"].replace("{car}", "2026 테슬라 사이버트럭")}
            for l in w1_skel["lines"]]
w1_sc = {"template": "opticglass_wide1", "car": {}, "scenes": w1_scenes, "lines": w1_lines}
(tmp / "wide1_native_longform.json").write_text(json.dumps(w1_sc, ensure_ascii=False), encoding="utf-8")
s_w1 = lc.load_scenario("wide1_native_longform")
car_w1 = build_longform.Car("cybertruck", s_w1, draft_name="test_wide1_native")
w1_prepared = [{"id": x["id"], "start": x["start"], "dur": x["dur"], "path": car_w1.media / f"lf_{x['id']}_{x['name']}.mp4",
                "is_split_compare": "split" in x or x.get("compare", False)} for x in s_w1["scenes"]]
build_longform.build_capcut(car_w1, w1_prepared, stage_dir=tmp / "stage")
w1_dc = json.loads((tmp / "stage" / "test_wide1_native" / "draft_content.json").read_text(encoding="utf-8"))
check(len(w1_dc["materials"].get("stickers", [])) == 2, "opticglass_wide1: Track[4] Guidance EN - Arrow stickers not preserved")
sticker_segs = [g for t in w1_dc["tracks"] if t["type"] == "sticker" for g in t["segments"]]
check([(g["target_timerange"]["start"], g["target_timerange"]["duration"]) for g in sticker_segs] == [(22600000, 2966666), (32600000, 2966666)],
      f"opticglass_wide1: unexpected sticker segment timings {sticker_segs}")
del cto.fails[:]
cto.check_longform("cybertruck", "test_wide1_native", stage_dir=tmp / "stage", scenario_name="wide1_native_longform")
for msg in cto.fails:
    fails.append(f"opticglass_wide1 native check_text_outputs: {msg}")
print(f"opticglass_wide1 native: {car_w1.total_s}s, {len(s_w1['scenes'])} scenes, {len(s_w1['lines'])} lines, "
      f"stickers={len(sticker_segs)}, transitions={len(w1_dc['materials'].get('transitions', []))}")

print("\n".join(fails) if fails else "OK: every template builds with its own tracks, timing and text slots")
sys.exit(1 if fails else 0)
