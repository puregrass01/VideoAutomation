"""The one place the pipeline talks to an LLM: the Antigravity CLI (~/.gemini/bin/agy.exe), the same agent, Google
account and subscription as the Antigravity desktop app, so no API key anywhere. llm_config.json picks the agent model
(default: Orchestrator (Carbon), gemini-pro-orchestrator; or Gemini 4 Carbon / Argon low/medium/high) per task; a task left empty uses default_model.

Each call also carries the agent's own ~22k-token system prompt.
- Text tasks (scenario_lines: draft_copy.py) run in plan mode from an empty temp folder and get a JSON answer back.
- photo_check (thumb_photos.py) is the same, with photos copied into that folder for the agent to look at: it sorts a
  car's photos into the thumbnail slots, finds plates and faces, and checks the masked copies.
- thumbnail_image (prompt_generator.py) asks the agent to call its own generate_image tool (the subscription picks the
  image model) with up to 3 reference photos copied into a temp folder, then takes the picture from the conversation's
  folder (~/.gemini/antigravity-cli/brain/<conversation id>/).
- video_edit (agy_edit.py) lets the agent edit files inside one folder only (edits allowed, terminal sandboxed, no
  access outside the folder) and can continue an earlier conversation, like the desktop app's chat.

usage: py llm.py --status        model per task, and whether agy is ready
       py llm.py --list          the model IDs agy can use
       py llm.py --selftest      checks the image lookup and the hook check without calling a model
"""
import argparse
import json
import pathlib
import re
import shlex
import shutil
import subprocess
import tempfile
import time

CONFIG = pathlib.Path(__file__).resolve().parent / "llm_config.json"
AGY_TIMEOUT_S = 300
GEMINI_HOME = pathlib.Path.home() / ".gemini"
AGY_BRAIN = GEMINI_HOME / "antigravity-cli" / "brain"  # where agy keeps each conversation's files
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
AGY_IMAGE_NAME = "car_hero_background"  # generate_image wants lowercase words with underscores, at most 3
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # agy.exe is a console app: no terminal popping up over the GUI


class LLMUnavailable(RuntimeError):
    """agy is not installed: callers fall back and say why."""


def config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def model_for(task: str) -> str:
    cfg = config()
    return (cfg.get("tasks") or {}).get(task) or cfg["default_model"]


def _agy() -> pathlib.Path:
    """llm_config.json agy_path, else the Antigravity install (~/.gemini/bin/agy.exe), else an agy on PATH."""
    if config().get("agy_path"):
        return pathlib.Path(config()["agy_path"])
    default = GEMINI_HOME / "bin" / "agy.exe"
    on_path = shutil.which("agy.exe")  # not an agy.cmd shim: cmd would mangle the multi-line prompt
    return default if default.exists() or not on_path else pathlib.Path(on_path)


def broken_hooks(hooks_file: pathlib.Path = GEMINI_HOME / "config" / "hooks.json") -> list:
    """Hook scripts named in Antigravity's hooks.json that no longer exist. Each tool call runs them; on this PC the
    missing-file error comes out in Korean (CP949), agy then stops with 'invalid UTF-8', and so image generation fails."""
    try:
        data = json.loads(hooks_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    found, todo = set(), [data]
    while todo:
        v = todo.pop()
        if isinstance(v, dict):
            if v.get("type") == "command" and isinstance(v.get("command"), str) and v["command"].strip():
                try:
                    exe = shlex.split(v["command"], posix=False)[0].strip('"')
                except ValueError:  # an unclosed quote: cmd still runs it, so just skip this entry
                    exe = ""
                if ("/" in exe or "\\" in exe) and not pathlib.Path(exe).exists():  # "node x.js" is not a path
                    found.add(exe)
            todo.extend(v.values())
        elif isinstance(v, list):
            todo.extend(v)
    return sorted(found)


def status() -> dict:
    """{model, ready, note} for the GUI and --status."""
    ok = _agy().exists()
    hooks = broken_hooks() if ok else []
    note = "Antigravity 구독" if ok else "agy.exe 없음 (Antigravity CLI 설치 필요)"
    if hooks:
        note += f" · 없는 훅 파일 {len(hooks)}개 (~/.gemini/config/hooks.json): 도구·이미지 사용 불가"
    return {"model": config()["default_model"], "ready": ok, "note": note}


def _parse_json_answer(text: str, who: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = fenced.group(1) if fenced else text[text.find("{"):text.rfind("}") + 1]
    try:
        answer = json.loads(raw)
    except ValueError:
        raise ValueError(f"{who} did not answer with JSON: {text[:200]!r}")
    if not isinstance(answer, dict):
        raise ValueError(f"{who} answered {type(answer).__name__}, not a JSON object")
    return answer


class _AgyLog:
    """agy's stream-json events as log lines, printed as they arrive (the GUI's 실행 로그 shows a job's stdout live):
    the agent's text line by line, each finished step, the result. Lines carry the conversation id's first 4
    characters, since photo checks run two agy calls at once."""

    def __init__(self, emit=lambda s: print(s, flush=True)):
        self.emit, self.tag, self.text = emit, "agy", {}

    def feed(self, line: str):
        """One stdout line; returns the result object when this is the final event."""
        try:
            ev = json.loads(line)
        except ValueError:
            if line.strip():
                self.emit(f"[{self.tag}] {line.rstrip()}")
            return None
        kind = ev.get("event")
        body = ev.get(kind) if isinstance(ev.get(kind), dict) else {}
        cid = body.get("conversation_id") or ev.get("conversation_id")  # init carries it at the top level
        if cid:
            self.tag = f"agy {cid[:4]}"
        if kind == "init":
            self.emit(f"[{self.tag}] 시작: {body.get('model')} @ {body.get('cwd')}")
        elif kind == "step_update":
            step, state, typ = body.get("step_index"), body.get("state"), body.get("step_type")
            if "text_delta" in body:
                buf = self.text.get(step, "") + body["text_delta"]
                *done, buf = buf.split("\n")
                for t in done:
                    self.emit(f"[{self.tag}] {t}")
                self.text[step] = buf
            if state == "DONE":
                if self.text.get(step):
                    self.emit(f"[{self.tag}] {self.text.pop(step)}")
                extra = {k: v for k, v in body.items() if k not in
                         ("conversation_id", "step_index", "state", "step_type", "text_delta", "duration_seconds", "usage")}
                took = f" {body['duration_seconds']:.1f}s" if isinstance(body.get("duration_seconds"), (int, float)) else ""
                if typ not in ("user_input", "agent_response") or extra:
                    self.emit(f"[{self.tag}] · {typ} 완료{took}" + (f" {json.dumps(extra, ensure_ascii=False)[:300]}" if extra else ""))
        elif kind == "result":
            u = body.get("usage") or {}
            took = f" {body['duration_seconds']:.0f}s" if isinstance(body.get("duration_seconds"), (int, float)) else ""
            self.emit(f"[{self.tag}] 끝: {body.get('status')}{took}, 토큰 {u.get('total_tokens', '?')}"
                      + (f" | {str(body.get('error'))[:300]}" if body.get("error") else ""))
            return body
        else:
            self.emit(f"[{self.tag}] {json.dumps(ev, ensure_ascii=False)[:300]}")
        return None


def _stream_agy(cmd: list, work: str) -> tuple:
    """Runs agy with --output-format stream-json, logging every event as it comes (_AgyLog) and stderr too.
    (exit code, the result object or None, stderr, raw stdout). Raises ValueError("agy timeout ...") past the time limit."""
    import threading
    log, raw, err = _AgyLog(), [], []
    p = subprocess.Popen(cmd, cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    timer = threading.Timer(AGY_TIMEOUT_S + 30, p.kill)
    timer.start()

    def drain_err():
        for line in p.stderr:
            err.append(line)
            if line.strip():
                log.emit(f"[{log.tag} stderr] {line.rstrip()}")
    t = threading.Thread(target=drain_err, daemon=True)
    t.start()
    result = None
    try:
        for line in p.stdout:
            raw.append(line)
            result = log.feed(line) or result
        p.wait()
    finally:
        expired = not timer.is_alive() and p.returncode not in (0, None) and result is None
        timer.cancel()
        t.join(5)
    if expired:
        raise ValueError(f"agy timeout: killed after {AGY_TIMEOUT_S + 30}s")  # a ValueError, so callers retry it
    return p.returncode, result, "".join(err), "".join(raw)


def _agy_run(prompt: str, model: str, work: str, edit: bool = False, conversation: str | None = None) -> dict:
    """One agy turn from the folder `work`: its JSON result (status SUCCESS) or ValueError. Plan mode (read-only) unless
    `edit`, which allows file edits inside `work` only."""
    exe = _agy()
    if not exe.exists():
        raise LLMUnavailable(f"{exe} not found: install the Antigravity CLI and sign in")
    if len(prompt) > 28_000:  # Windows caps a command line at 32,767 characters
        raise ValueError(f"prompt is {len(prompt)} characters; the CLI takes at most ~28,000")
    cmd = [str(exe), "-p", prompt, "--model", model, "--output-format", "stream-json", "--print-timeout", f"{AGY_TIMEOUT_S}s"]
    if edit:  # the user's settings allow access outside the workspace; this session must not
        cmd += ["--mode", "accept-edits", "--sandbox", "--settings", json.dumps({"allowNonWorkspaceAccess": False})]
    else:
        cmd += ["--mode", "plan"]
    if conversation:
        cmd += ["--conversation", conversation]
    rc, out, stderr, raw = _stream_agy(cmd, work)
    if out is None:
        raise ValueError(f"agy exit {rc}: {(stderr or raw)[:300]}")
    if out.get("status") != "SUCCESS":  # not signed in, quota, model name, a broken hook, ...
        error = str(out.get("error") or stderr[:300])
        hooks = broken_hooks() if "UTF-8" in error else []
        hint = (f" | 원인: ~/.gemini/config/hooks.json의 훅 파일이 없습니다 ({', '.join(hooks)}). 도구를 쓸 때마다 그 훅이 "
                "한글 오류를 내서 agy가 멈춥니다. 훅을 다시 설치하거나 hooks.json에서 빼야 합니다.") if hooks else ""
        raise ValueError(f"agy {out.get('status')}: {error}{hint}")
    return out


def edit_turn(prompt: str, work: pathlib.Path, conversation: str | None = None) -> tuple:
    """task video_edit: one turn in which the agent may edit files inside `work` (and nowhere else), continuing
    `conversation` when given. (answer text, conversation id)."""
    out = _agy_run(prompt, model_for("video_edit"), str(work), edit=True, conversation=conversation)
    return out.get("response") or "", out.get("conversation_id") or conversation


def chat_turn(prompt: str, work: pathlib.Path, conversation: str | None = None) -> tuple:
    """task video_edit's model, read-only (plan mode) from `work`: a plain conversation turn, continuing
    `conversation` when given. (answer text, conversation id)."""
    out = _agy_run(prompt, model_for("video_edit"), str(work), conversation=conversation)
    return out.get("response") or "", out.get("conversation_id") or conversation


def _generated_image(conversation_id: str, response: str, since: float, brain: pathlib.Path = AGY_BRAIN) -> pathlib.Path | None:
    """The picture generate_image saved during this call (written at or after `since`):
    <brain>/<conversation id>/<AGY_IMAGE_NAME>_<ms>.<ext> (newest), else the path the agent answered with. Older files
    (the reference copies, another car's earlier picture) never count, so a run that made no picture fails."""
    folder = brain / conversation_id if conversation_id else None
    found = [p for p in folder.glob(f"{AGY_IMAGE_NAME}*") if p.suffix.lower() in IMAGE_EXTS] if folder else []
    said = pathlib.Path(response.strip().strip("`'\" \n"))
    if said.suffix.lower() in IMAGE_EXTS and said.is_file():
        found.append(said)
    found = [p for p in found if p.stat().st_mtime >= since]
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def generate_image(task: str, prompt: str, images: list, out_path: pathlib.Path, aspect_ratio: str = "16:9") -> pathlib.Path:
    """One picture from a prompt and up to 3 reference photos, saved to out_path. Send only photos whose plates and
    faces are already covered: they leave this PC."""
    images = [pathlib.Path(p) for p in images]
    if len(images) > 3:
        raise ValueError(f"{len(images)} reference photos; image generation takes at most 3")
    missing = [str(p) for p in images if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"reference photo not found: {', '.join(missing)}")
    with tempfile.TemporaryDirectory(prefix="agy_img_") as work:  # holds only the reference copies
        refs = []
        for i, p in enumerate(images, 1):
            ref = pathlib.Path(work) / f"ref_{i}{p.suffix.lower()}"  # ASCII names: the photos sit under Korean folders
            shutil.copyfile(p, ref)
            refs.append(str(ref))
        ask = ("Call the generate_image tool exactly once and do nothing else, with these arguments:\n"
               f"- image_name: {AGY_IMAGE_NAME}\n"
               f"- aspect_ratio: {aspect_ratio}\n"
               f"- image_paths: {json.dumps(refs)}\n"
               "- prompt: the text between the PROMPT markers below, copied exactly, without the markers\n"
               f"<<<PROMPT\n{prompt}\nPROMPT>>>\n"
               "Then answer with only the absolute path of the saved image.")
        start = time.time()  # after the reference copies were written, so they never pass for the result
        out = _agy_run(ask, model_for(task), work)
        src = _generated_image(out.get("conversation_id") or "", out.get("response") or "", start)
        if src is None:
            raise ValueError(f"agy finished without an image ({AGY_IMAGE_NAME}): {(out.get('response') or '')[:300]!r}")
        from PIL import Image
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im.convert("RGB").save(out_path)
    return out_path


def generate_json(task: str, prompt: str, files: dict | None = None) -> dict:
    """Ask the task's model for a JSON object. files = {name the prompt uses: local path}: copied into the agent's
    folder for it to open (ASCII names: the photos sit under Korean folders). They leave this PC."""
    who = f"agy {model_for(task)}"
    if not files and "do not call any tool" not in prompt.lower():
        prompt = (f"{prompt}\n\nIMPORTANT: Do NOT call any tools (do not call read_file, search_web, invoke_subagent, "
                  "write_file, or run_command). Answer immediately in this turn with ONLY the raw JSON object.")
    with tempfile.TemporaryDirectory(prefix="agy_") as work:  # nothing else for the agent to read or edit
        for name, src in (files or {}).items():
            shutil.copyfile(src, pathlib.Path(work) / name)
        out = _agy_run(prompt, model_for(task), work)
        try:
            return _parse_json_answer(out.get("response") or "", who)
        except ValueError:
            if not out.get("conversation_id"):
                raise
            # The agent sometimes tries to run a command (plan mode denies it, ending the turn with no answer) or writes
            # an implementation_plan.md artifact under --mode plan and asks for review instead of outputting the JSON.
            # Continuing the same conversation keeps the images it already inspected.
            out = _agy_run("Your last turn did not include the JSON object (do not write a plan artifact or run commands). "
                           "From what you already looked at, answer now with only the JSON object.", model_for(task), work,
                           conversation=out["conversation_id"])
    return _parse_json_answer(out.get("response") or "", who)


def list_models() -> list:
    exe = _agy()
    if not exe.exists():
        raise LLMUnavailable(f"{exe} not found")
    r = subprocess.run([str(exe), "models"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120, creationflags=NO_WINDOW)
    return [line.strip() for line in r.stdout.splitlines() if "\t" in line]


def _selftest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        brain = pathlib.Path(tmp)
        (brain / "c1").mkdir()
        ref = brain / "ref_1.jpg"  # a reference copy, written before the call starts
        ref.write_bytes(b"x")
        time.sleep(0.05)
        start = time.time()
        for name in (f"{AGY_IMAGE_NAME}_1.jpg", f"{AGY_IMAGE_NAME}_2.png", "other_3.png", f"{AGY_IMAGE_NAME}.txt"):
            (brain / "c1" / name).write_bytes(b"x")
            time.sleep(0.02)
        assert _generated_image("c1", "", start, brain).name == f"{AGY_IMAGE_NAME}_2.png", "newest generated image"
        said = brain / "said.webp"
        said.write_bytes(b"x")
        assert _generated_image("c2", f"`{said}`\n", start, brain) == said, "falls back to the path the agent answered"
        assert _generated_image("c2", str(ref), start, brain) is None, "a reference copy is not a result"
        assert _generated_image("c1", "", time.time() + 5, brain) is None, "pictures from before the call do not count"
        assert _generated_image("", "no image made", start, brain) is None
        hooks = brain / "hooks.json"
        hooks.write_text(json.dumps({"x": {"Pre": [{"type": "command", "command": f"{tmp}/gone.cmd --flag"},
                                                   {"type": "command", "command": f'"{said}" arg'},
                                                   {"type": "command", "command": "node hook.js"},
                                                   {"type": "command", "command": '"C:/gone/unclosed.cmd'}],
                                           "PreToolUse": [{"hooks": [{"type": "command", "command": "C:/nope/x.cmd"}]}]}}))
        assert broken_hooks(hooks) == sorted([f"{tmp}/gone.cmd", "C:/nope/x.cmd"]), broken_hooks(hooks)
        assert broken_hooks(brain / "missing.json") == []
    got = []  # agy's stream-json events (as agy 1.x prints them) become log lines as they arrive
    log = _AgyLog(got.append)
    su = lambda **kw: json.dumps({"event": "step_update", "step_update": {"conversation_id": "3d97-x", **kw}})
    events = [json.dumps({"event": "init", "conversation_id": "3d97-x", "init": {"model": "m", "cwd": "C:/w"}}),
              su(step_index=0, state="DONE", step_type="user_input"),
              su(step_index=1, state="DONE", step_type="tool_call", duration_seconds=2.0, tool="view_file"),
              su(step_index=2, state="ACTIVE", step_type="agent_response", text_delta="첫 줄\n둘"),
              su(step_index=2, state="DONE", step_type="agent_response", text_delta="째 줄", duration_seconds=1.0),
              json.dumps({"event": "result", "result": {"conversation_id": "3d97-x", "status": "SUCCESS", "response": "첫 줄\n둘째 줄",
                                                       "duration_seconds": 3, "usage": {"total_tokens": 9}}})]
    res = [log.feed(e) for e in events]
    assert res[-1]["response"] == "첫 줄\n둘째 줄" and res[:-1] == [None] * 5
    assert got == ["[agy 3d97] 시작: m @ C:/w", '[agy 3d97] · tool_call 완료 2.0s {"tool": "view_file"}',
                   "[agy 3d97] 첫 줄", "[agy 3d97] 둘째 줄", "[agy 3d97] 끝: SUCCESS 3s, 토큰 9"], got
    print("llm self-check ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
        raise SystemExit
    st = status()
    print(f"agy ({st['note']}) | ready: {st['ready']}")
    for task in config().get("tasks") or {}:
        print(f"  {task:16} -> {model_for(task)}")
    if a.list:
        for name in list_models():
            print("  ", name)
