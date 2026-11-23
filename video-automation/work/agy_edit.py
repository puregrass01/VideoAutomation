"""The GUI's agy prompt box: one instruction for a car's video, carried out by the Antigravity agent (agy, Gemini 4
Orchestrator (Carbon) by default, llm_config.json video_edit; the desktop app's subscription; no API key), then the car's CapCut draft is rebuilt.

The agent works in work/agy_sessions/<slug>/ only: a copy of the car's scenario (<slug>_longform.json: scenes, lines,
timing, template), the project rules (.agents/rules) and the template's slot list (template.json). Its conversation id
is kept there (session.json), so the next instruction for the same car continues the same conversation, like the
desktop chat; --new forgets it. After the turn the copy must pass longform_common.load_scenario; then the original goes
to scenarios/_backup/, the copy replaces it, and gdrive_pipeline rebuilds the car from its local media. A copy that
fails the check leaves the original untouched and stays in the folder, so the next instruction can fix it.

With no car (--chat) the box is a plain conversation with the same agent: read-only (plan mode) from
work/agy_sessions/_chat/, which holds only the project rules, and remembered there the same way.

usage: py agy_edit.py <slug> "<instruction>"
       py agy_edit.py <slug> --new        forget this car's conversation and edits in progress
       py agy_edit.py --chat "<message>"  talk to agy without a car (no file changes)
       py agy_edit.py --chat --new        forget that conversation
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from datetime import datetime

import llm

WORK_DIR = pathlib.Path(__file__).resolve().parent
SCENARIOS = WORK_DIR / "scenarios"
TEMPLATES = SCENARIOS / "templates"
RULES = WORK_DIR.parents[1] / ".agents" / "rules" / "opticglass-workflow-rules.md"


def session_dir(slug: str) -> pathlib.Path:
    return WORK_DIR / "agy_sessions" / slug


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(slug: str) -> tuple:
    """(work folder, scenario copy, session). The copy is refreshed from the original when the original changed since
    the last sync (draft_copy --apply, a hand edit); otherwise an edit in progress (one that failed the check) stays."""
    original = SCENARIOS / f"{slug}_longform.json"
    if not original.exists():
        wide1 = SCENARIOS / f"{slug}_wide1.json"
        if wide1.exists():
            original = wide1
        else:
            raise SystemExit(f"[agy] {slug}: 롱폼 시나리오가 없습니다 ({original.name}); 롱폼 시나리오가 있는 차만 고칠 수 있습니다")
    ws = session_dir(slug)
    (ws / ".agents" / "rules").mkdir(parents=True, exist_ok=True)
    session_file = ws / "session.json"
    session = json.loads(session_file.read_text(encoding="utf-8")) if session_file.exists() else {}
    copy = ws / original.name
    if not copy.exists() or session.get("synced") != _digest(original):
        shutil.copyfile(original, copy)
        session["synced"] = _digest(original)
    shutil.copyfile(RULES, ws / ".agents" / "rules" / RULES.name)
    # the original's template: the copy may hold a failed edit that is not even JSON, which the next instruction fixes
    tpl = TEMPLATES / json.loads(original.read_text(encoding="utf-8")).get("template", "") / "template.json"
    if tpl.is_file():
        shutil.copyfile(tpl, ws / "template.json")
    return ws, copy, session


def edit_prompt(slug: str, instruction: str, copy: pathlib.Path) -> str:
    import drive_index
    return (f"[옵틱글래스 {drive_index.title(slug)} ({slug}) 롱폼 영상 수정]\n"
            f"이 폴더의 {copy.name}이 이 영상의 시나리오입니다: scenes(원본 클립, 시작점, 길이, 룩, 크롭·분할), "
            "lines(화면 자막 문구, 타이밍, 스타일), template(CapCut 템플릿 이름). 지시를 이 파일만 고쳐서 수행하세요. "
            "template.json은 템플릿의 영상 슬롯·자막 슬롯 목록이며 참고만 하고 고치지 마세요. .agents/rules의 프로젝트 규칙을 지키세요. "
            "JSON 형식을 유지하고, 장면 사이에 빈틈이 없어야 하며 마지막 장면은 outro여야 합니다 "
            "(장면 개수가 템플릿 슬롯 수와 다를 때는 모든 장면에 start와 dur를 적으세요). 명령은 실행하지 마세요.\n"
            "끝나면 무엇을 바꿨는지(장면·자막 id) 한국어 1~3문장으로 답하세요. 바꿀 필요가 없으면 이유를 답하세요.\n\n"
            f"지시: {instruction}")


def swap_in(slug: str, copy: pathlib.Path) -> pathlib.Path:
    """The original to scenarios/_backup/, then the checked copy in its place. Returns the backup."""
    original = SCENARIOS / copy.name
    backup = SCENARIOS / "_backup" / f"{copy.stem}.{datetime.now():%Y%m%d_%H%M%S}.agy.json"
    backup.parent.mkdir(exist_ok=True)
    shutil.copyfile(original, backup)
    tmp = original.with_suffix(".tmp")
    shutil.copyfile(copy, tmp)
    os.replace(tmp, original)
    return backup


CHAT = "_chat"  # the no-car conversation's session folder; slugs never start with "_" (drive_index.auto_slug)


def chat(message: str) -> int:
    """One turn of the no-car conversation: read-only, from a folder holding only the project rules."""
    ws = session_dir(CHAT)
    (ws / ".agents" / "rules").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RULES, ws / ".agents" / "rules" / RULES.name)
    session_file = ws / "session.json"
    session = json.loads(session_file.read_text(encoding="utf-8")) if session_file.exists() else {}
    print(f"[agy] {llm.model_for('video_edit')}와 대화" + (" (이어서)" if session.get("conversation") else " (새 대화)"))
    prompt = ("[옵틱글래스 유튜브 영상·썸네일 자동화 GUI의 agy 대화창] 사용자가 차를 고르지 않고 보낸 말입니다. "
              ".agents/rules의 프로젝트 규칙을 참고해 한국어로 답하세요. 파일을 고치거나 명령을 실행하지 마세요. "
              "특정 차의 영상을 고쳐 달라는 말이면, 왼쪽 Drive 표에서 롱폼 시나리오가 있는 차 폴더를 고른 뒤 다시 보내 달라고 안내하세요.\n\n"
              f"사용자: {message}")
    answer, session["conversation"] = llm.chat_turn(prompt, ws, session.get("conversation"))
    session_file.write_text(json.dumps(session, indent=1), encoding="utf-8")
    if not answer.strip():  # plan mode ends the turn empty when the agent tried a command it may not run
        print("[agy] 답이 비어 있습니다 (agy가 실행할 수 없는 명령을 시도했을 수 있음). 같은 말을 다시 보내면 대화를 이어서 묻습니다.")
        return 1
    print(f"[agy] {answer.strip()}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug", nargs="?", default="", help="the car; with --chat, the message")
    ap.add_argument("instruction", nargs="?", default="")
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--chat", action="store_true")
    a = ap.parse_args()
    if a.chat:
        if a.new:
            shutil.rmtree(session_dir(CHAT), ignore_errors=True)
            print("[agy] 새 대화 (이전 대화를 지웠습니다)")
            return 0
        if not a.slug.strip():
            raise SystemExit("[agy] 보낼 말이 비어 있습니다")
        return chat(a.slug.strip())
    if not re.fullmatch(r"[a-z0-9_]+", a.slug):  # it names a folder that --new deletes
        raise SystemExit(f"[agy] 슬러그가 아닙니다: {a.slug!r}")
    if a.new:
        shutil.rmtree(session_dir(a.slug), ignore_errors=True)
        print(f"[agy] {a.slug}: 새 대화 (이전 대화와 진행 중인 수정을 지웠습니다)")
        return 0
    if not a.instruction.strip():
        raise SystemExit("[agy] 지시가 비어 있습니다")

    ws, copy, session = prepare(a.slug)
    print(f"[agy] {a.slug}: {llm.model_for('video_edit')}에게 보내는 중" + (" (대화 이어서)" if session.get("conversation") else " (새 대화)"))
    answer, session["conversation"] = llm.edit_turn(edit_prompt(a.slug, a.instruction.strip(), copy), ws, session.get("conversation"))
    (ws / "session.json").write_text(json.dumps(session, indent=1), encoding="utf-8")  # kept even if the check fails
    print(f"[agy] {answer.strip()}")

    try:
        edited = json.loads(copy.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"[agy 수정 거부] {copy.name}이 JSON이 아닙니다: {exc}. 원본은 그대로입니다; 다음 지시로 고칠 수 있습니다.")
        return 1
    if edited == json.loads((SCENARIOS / copy.name).read_text(encoding="utf-8")):
        print("[agy] 시나리오 변경 없음: 다시 빌드하지 않습니다")
        return 0
    from longform_common import load_scenario
    try:
        load_scenario(copy.stem, path=copy)
    except Exception as exc:  # gaps, a scene count that no longer matches the template, a missing line field, ...
        print(f"[agy 수정 거부] 시나리오 검사 실패: {exc}\n  원본은 그대로입니다; 다음 지시로 고칠 수 있습니다.")
        return 1
    if session.get("synced") != _digest(SCENARIOS / copy.name):  # changed during the agy turn (--apply, a hand edit)
        print("[agy 수정 거부] 원본 시나리오가 그사이 바뀌었습니다; 바뀐 원본으로 다시 지시하세요.")
        return 1
    backup = swap_in(a.slug, copy)
    session["synced"] = _digest(SCENARIOS / copy.name)
    (ws / "session.json").write_text(json.dumps(session, indent=1), encoding="utf-8")
    print(f"[agy] 시나리오를 바꿨습니다 (이전 것: scenarios/_backup/{backup.name}). 롱폼을 다시 빌드합니다.", flush=True)
    # the pipeline checks this car's scenario against the role rules and its built draft (check_text_outputs) before
    # deploying; a draft that fails stays staged and the reason goes to output/<car>/report.txt
    cmd = [sys.executable, str(WORK_DIR / "gdrive_pipeline.py"), "--vehicle", a.slug]
    if copy.name.endswith("_wide1.json"):
        cmd += ["--build", "wide1"]
    return subprocess.run(cmd).returncode


def _selftest() -> None:
    """The copy/sync/swap rules and the scenario check, on a temp copy of the Cybertruck scenario (no agy call)."""
    import tempfile
    from longform_common import load_scenario
    global WORK_DIR, SCENARIOS
    real = WORK_DIR, SCENARIOS
    WORK_DIR = pathlib.Path(tempfile.mkdtemp())
    SCENARIOS = WORK_DIR / "scenarios"
    try:
        SCENARIOS.mkdir()
        original = SCENARIOS / "t_longform.json"
        shutil.copyfile(real[1] / "cybertruck_longform.json", original)
        ws, copy, session = prepare("t")
        assert copy.read_bytes() == original.read_bytes() and (ws / "template.json").exists() and (ws / ".agents" / "rules" / RULES.name).exists()
        (ws / "session.json").write_text(json.dumps(session), encoding="utf-8")
        broken = json.loads(copy.read_text(encoding="utf-8"))
        broken["scenes"].pop()
        copy.write_text(json.dumps(broken), encoding="utf-8")
        try:
            load_scenario(copy.stem, path=copy)
            raise AssertionError("a scene count that no longer matches the template must fail the check")
        except ValueError:
            pass
        _, copy, session = prepare("t")
        assert json.loads(copy.read_text(encoding="utf-8")) == broken, "an edit in progress stays for the next instruction"
        copy.write_text("{ not json", encoding="utf-8")
        _, copy, session = prepare("t")  # a copy the agent left as broken JSON must not block the next instruction
        assert copy.read_text(encoding="utf-8") == "{ not json"
        original.write_text(original.read_text(encoding="utf-8") + "\n", encoding="utf-8")  # changed outside agy
        _, copy, session = prepare("t")
        assert copy.read_bytes() == original.read_bytes(), "a changed original replaces the copy"
        good = json.loads(copy.read_text(encoding="utf-8"))
        good["lines"][0]["text"] = "바뀐 자막"
        copy.write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
        load_scenario(copy.stem, path=copy)
        backup = swap_in("t", copy)
        assert json.loads(original.read_text(encoding="utf-8"))["lines"][0]["text"] == "바뀐 자막" and backup.exists()
    finally:
        shutil.rmtree(WORK_DIR, ignore_errors=True)
        WORK_DIR, SCENARIOS = real
    print("agy_edit self-check ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        _selftest()
        sys.exit(0)
    sys.exit(main())
