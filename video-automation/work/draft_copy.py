"""Drafts a car's scenario lines and thumbnail second line with the LLM set for task scenario_lines (llm_config.json),
using real OpticGlass lines as examples: the channel's recent uploads first (datasets/youtube_lines.jsonl, youtube_lines.py),
then the local CapCut drafts (datasets/draft_lines.jsonl, extract_draft_lines.py).

The draft never touches the scenario: it is written to scenarios/<slug>_longform.draft.json next to the old text
(a previous draft, maybe hand-edited, is kept in scenarios/_backup/ first). --apply copies the reviewed draft into
the scenario: a line changes only if it still has the text the draft was made from, the old scenario and the used
draft go to scenarios/_backup/, and the thumbnail's second line is set for the next gdrive_pipeline run. The CapCut
draft shows the new lines after a rebuild.

Fixed lines (the car title, the BY OPTICGLASS card, the 시공 전/후 badges) are not drafted. A line may grow by about
30% or 4 characters, and never past the width the canvas leaves around its position.

usage: py draft_copy.py <slug> [--dry-run] [--apply]
       py draft_copy.py --selftest
"""
import argparse
import json
import pathlib
import sys
from datetime import datetime

WORK = pathlib.Path(__file__).resolve().parent
SCENARIOS = WORK / "scenarios"
DATASET = WORK / "datasets" / "draft_lines.jsonl"
YOUTUBE = WORK / "datasets" / "youtube_lines.jsonl"  # the channel's recent uploads (youtube_lines.py), used first
FONT = WORK.parent / "assets" / "fonts" / "Paperlogy-7Bold.ttf"  # the face every longform line is set in
FIXED_IDS = {"lt01", "lt01b", "lt04a", "lt10", "lt11", "lt12a", "lt12b",  # 80 s cuts
             "w04a", "w04b", "wb1", "wb2", "ws1", "ws2", "ws3", "ws4"}  # 광각미러 템플릿 1 (BY OPTICGLASS / 꼭 필요한 이유, 설치 전/후, 시공 전/후)
EXAMPLES_PER_PART = 6
LINE2_MAX = 10
CANVAS_W, SIDE_MARGIN = 1920, 40


def car_name(slug: str) -> str:
    import drive_index
    return drive_index.title(slug)


def max_chars(line: dict) -> int:
    """About 30% (or 4 characters) longer than now, capped so the line still fits around its centre on the canvas."""
    limit = max(len(line["text"]) + 4, int(len(line["text"]) * 1.3))
    if FONT.exists():
        from PIL import ImageFont
        per_char = ImageFont.truetype(str(FONT), int(line["size"])).getlength(line["text"]) / max(1, len(line["text"]))
        room = 2 * min(line["fc_pos"][0], CANVAS_W - line["fc_pos"][0]) - 2 * SIDE_MARGIN
        limit = min(limit, max(len(line["text"]), int(room / per_char)))
    return limit


def lines_to_draft(scenario: dict) -> list:
    from extract_draft_lines import part_of
    from longform_common import load_template
    slots = (scenario.get("tpl") or load_template(scenario["template"])).get("text_slots", {})
    scenes = scenario["scenes"]
    total = scenes[-1]["start"] + scenes[-1]["dur"]
    full = [{**slots.get(l["id"], {}), **l} for l in scenario["lines"]]
    return [{"id": l["id"], "role": part_of(l["text"], l["start"], total)[0], "current": l["text"], "max_chars": max_chars(l)}
            for l in full if l["id"] not in FIXED_IDS and len(l["text"]) > 3]


def examples(roles: set, scenario: dict, car: str, slug: str) -> dict:
    """Real OpticGlass lines by role from other cars: a row naming this car (in its draft name or its text) or
    repeating a line this scenario already has is left out, so the draft does not echo this car's own video."""
    if not DATASET.exists() and not YOUTUBE.exists():
        raise SystemExit(f"{DATASET} is missing: run py extract_draft_lines.py (or py youtube_lines.py) first")
    squash = lambda s: s.replace(" ", "").replace("\n", "").lower()
    title = next((l["text"] for l in scenario["lines"] if l["id"] == "lt01"), "")
    tokens = {squash(t) for t in (car, title, slug, car.split()[-1]) if len(squash(t)) >= 2}
    own = {squash(l["text"]) for l in scenario["lines"]}
    rows = [json.loads(l) for f in (YOUTUBE, DATASET) if f.exists() for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r["brand"] == "opticglass" and r["part"] in roles and squash(r["text"]) not in own
            and (r.get("source") != "youtube" or r.get("checked"))  # OCR text agy has not checked may be misread
            and not any(t in squash(r["draft"]) or t in squash(r["text"]) for t in tokens)]
    # the channel's own recent uploads first, newest first; then the local CapCut drafts
    newest = lambda r: -int(r.get("upload_date") or 0)
    rows.sort(key=lambda r: (r["common_drafts"] > 2, r.get("source") != "youtube", r["format"] != "longform", newest(r),
                             r["draft"], r["start"]))
    picked: dict = {}
    for r in rows:
        bucket = picked.setdefault(r["part"], [])
        text = r["text"].replace("\n", " ")
        if len(bucket) < EXAMPLES_PER_PART and text not in bucket:
            bucket.append(text)
    return picked


def build_prompt(car: str, todo: list, ex: dict, line2_now: str) -> str:
    return "\n".join([
        "너는 옵틱글래스(OpticGlass) 광각 사이드미러 시공 유튜브 롱폼 영상의 자막을 쓰는 카피라이터다.",
        f"차종: {car}",
        "규칙:",
        "- 한국어 자막 한 줄. 각 줄은 max_chars 글자 이하.",
        "- 줄마다 role(문제 제기 problem, 해결 solution, 섹션 제목 section 등)과 current(지금 문구)의 뜻을 지킨다.",
        "- 숫자, 가격, 사양, 비교 수치를 지어내지 않는다. 주어진 차종 이름 말고 다른 차종을 쓰지 않는다.",
        "- 아래 실제 영상 자막의 말투를 따르되 그대로 베끼지 않는다.",
        "실제 옵틱글래스 영상 자막 예시 (역할별):",
        json.dumps(ex, ensure_ascii=False, indent=1),
        "새로 쓸 줄:",
        json.dumps(todo, ensure_ascii=False, indent=1),
        f"썸네일 둘째 줄 후보도 3개 쓴다 (각 {LINE2_MAX}자 이하, 지금은 '{line2_now}').",
        'JSON으로만 답한다: {"lines": {"<id>": "<새 문구>"}, "thumbnail_line2": ["...", "...", "..."]}',
    ])


def validate(answer: dict, todo: list) -> tuple:
    """(accepted {id: text}, rejected [reason], thumbnail line 2 candidates); a bad line keeps its old text."""
    if not isinstance(answer, dict):
        raise ValueError(f"the model answered {type(answer).__name__}, not a JSON object")
    got, ok, bad = answer.get("lines") or {}, {}, []
    for t in todo:
        text = got.get(t["id"]) if isinstance(got, dict) else None
        if not isinstance(text, str) or not text.strip():
            bad.append(f"{t['id']}: no text")
        elif len(text.strip()) > t["max_chars"]:
            bad.append(f"{t['id']}: {len(text.strip())} chars > {t['max_chars']}")
        else:
            ok[t["id"]] = text.strip()
    l2 = answer.get("thumbnail_line2")  # a bare string would be walked letter by letter
    line2 = [s.strip() for s in (l2 if isinstance(l2, list) else []) if isinstance(s, str) and 0 < len(s.strip()) <= LINE2_MAX]
    return ok, bad, line2


def diversify_scenario(slug: str, scenario: dict) -> dict:
    """Rewrites non-fixed scenario captions and sets thumbnail.line2 in-place using YouTube channel examples first."""
    import llm
    car = car_name(slug)
    todo = lines_to_draft(scenario)
    if not todo:
        return scenario
    line2_now = (scenario.get("thumbnail") or {}).get("line2") or "광각미러 차이!"
    prompt = build_prompt(car, todo, examples({t["role"] for t in todo}, scenario, car, slug), line2_now)
    ok, _bad, line2 = validate(llm.generate_json("scenario_lines", prompt), todo)
    for ln in scenario["lines"]:
        if ln["id"] in ok:
            ln["text"] = ok[ln["id"]]
    if line2:
        scenario["thumbnail"] = {"line2": line2[0]}
    print(f"  [대사 다양화] {car}: 자막 {len(ok)}/{len(todo)}줄 반영"
          + (f", 썸네일 2줄 '{line2[0]}'" if line2 else ""), flush=True)
    return scenario


def _backup_path(name: str, suffix: str) -> pathlib.Path:
    path = SCENARIOS / "_backup" / f"{name}.{datetime.now():%Y%m%d_%H%M%S}{suffix}"
    path.parent.mkdir(exist_ok=True)
    return path


def apply(name: str, path: pathlib.Path, draft_path: pathlib.Path, slug: str) -> None:
    if not draft_path.exists():
        raise SystemExit(f"no draft for {slug}: run py draft_copy.py {slug} first")
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_id = {l["id"]: l for l in raw["lines"]}
    applied, stale = [], []
    for d in draft["lines"]:
        line = by_id.get(d["id"])
        if line is None or line["text"] != d["old"]:  # the scenario changed since this draft was made
            stale.append(d["id"])
        else:
            line["text"] = d["new"]
            applied.append(d["id"])
    if not applied and not draft["thumbnail_line2"]:
        raise SystemExit(f"nothing to apply: every drafted line changed since the draft ({', '.join(stale)})")
    backup = _backup_path(name, ".json")
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    if draft["thumbnail_line2"]:
        raw["thumbnail"] = {"line2": draft["thumbnail_line2"][0]}
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    draft_path.replace(_backup_path(name, ".draft.applied.json"))  # a used draft cannot be applied twice
    print(f"applied {len(applied)} lines and thumbnail line 2 '{raw.get('thumbnail', {}).get('line2')}' -> {path}")
    if stale:
        print(f"kept {len(stale)} lines edited since the draft: {', '.join(stale)}")
    print(f"old scenario: {backup}\nrebuild to see it: py gdrive_pipeline.py --vehicle {slug}  (then check_text_outputs.py {slug})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt, call nothing")
    ap.add_argument("--apply", action="store_true", help="copy the reviewed draft into the scenario")
    a = ap.parse_args()
    sys.path.insert(0, str(WORK))
    import llm
    from longform_common import load_scenario

    name = f"{a.slug}_longform"
    path, draft_path = SCENARIOS / f"{name}.json", SCENARIOS / f"{name}.draft.json"
    if not path.exists():
        raise SystemExit(f"{path} not found: this car has no longform scenario yet")
    if a.apply:
        apply(name, path, draft_path, a.slug)
        return

    car = car_name(a.slug)
    scenario = load_scenario(name)
    todo = lines_to_draft(scenario)
    line2_now = (scenario.get("thumbnail") or {}).get("line2") or "광각미러 차이!"
    prompt = build_prompt(car, todo, examples({t["role"] for t in todo}, scenario, car, a.slug), line2_now)
    if a.dry_run:
        print(prompt)
        return
    model = llm.model_for("scenario_lines")
    print(f"drafting {len(todo)} lines for {car} with {model} ...")
    try:
        ok, bad, line2 = validate(llm.generate_json("scenario_lines", prompt), todo)
    except Exception as exc:  # llm.LLMUnavailable, an agy error, a non-JSON answer
        raise SystemExit(f"LLM draft failed, nothing changed: {exc}")
    if draft_path.exists():  # an earlier draft may hold hand edits
        draft_path.replace(_backup_path(name, ".draft.json"))
    draft = {"model": model, "created": datetime.now().isoformat(timespec="seconds"),
             "lines": [{"id": t["id"], "old": t["current"], "new": ok[t["id"]]} for t in todo if t["id"] in ok],
             "rejected": bad, "thumbnail_line2": line2}
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=1), encoding="utf-8")
    for d in draft["lines"]:
        print(f"  {d['id']:6} {d['old']}\n         -> {d['new']}")
    for b in bad:
        print(f"  kept old text, {b}")
    print(f"thumbnail line 2: {line2}\ndraft -> {draft_path}\nreview it, then: py draft_copy.py {a.slug} --apply")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        assert validate({"lines": {}, "thumbnail_line2": "abc"}, [])[2] == [], "a string line 2 must not split into letters"
        assert validate({"lines": {}, "thumbnail_line2": ["abc", ""]}, [])[2] == ["abc"]
        from longform_common import load_template
        _w1 = load_template("opticglass_wide1")
        _todo_ids = {t["id"] for t in lines_to_draft({
            "template": "opticglass_wide1", "tpl": _w1, "scenes": _w1["slots"],
            "lines": [{"id": k, "text": v["text"]} for k, v in _w1["text_slots"].items()],
        })}
        assert {"w04a", "w04b", "wb1", "wb2", "ws1", "ws2", "ws3", "ws4"}.isdisjoint(_todo_ids), _todo_ids
        assert "wc1" in _todo_ids and "wz1" in _todo_ids
        print("draft_copy self-check ok")
    else:
        main()
