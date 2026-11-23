"""Write this project's Claude Code conversations (user + Claude text, no tool output) to archive/sessions/claude_code/.

Raw transcripts stay in %USERPROFILE%\\.claude\\projects\\<project>\\*.jsonl; OAuth codes and API keys are redacted here.
Usage: py -3 archive/sessions/export_claude_sessions.py
"""
import json, os, pathlib, re

repo = pathlib.Path(__file__).resolve().parents[2]
proj = pathlib.Path.home() / ".claude/projects" / re.sub(r"[^A-Za-z0-9]", "-", str(repo))
sessions = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Claude-Data/claude_pzs8sxrjxfjjc/claude-code-sessions"
out = repo / "archive/sessions/claude_code"
out.mkdir(parents=True, exist_ok=True)

titles = {}
for f in sessions.rglob("local_*.json"):
    j = json.loads(f.read_text(encoding="utf-8"))
    titles[j.get("cliSessionId")] = (j.get("title") or "", f.stem)

REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
SECRET = re.compile(r"([?&]code=)[^&\s]+|AIza[0-9A-Za-z_-]{20,}|ya29\.[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9_-]{20,}")


def text_of(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


for jl in sorted(proj.glob("*.jsonl")):
    cli = jl.stem
    title, local_id = titles.get(cli, ("(untitled)", "?"))
    lines, first_ts = [], None
    for raw in jl.open(encoding="utf-8"):
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        if e.get("type") not in ("user", "assistant") or e.get("isSidechain") or e.get("isMeta"):
            continue
        t = REMINDER.sub("", text_of(e.get("message", {}).get("content", ""))).strip()
        if not t:
            continue
        t = SECRET.sub(lambda m: (m.group(1) or "") + "[REDACTED]", t)
        ts = (e.get("timestamp") or "")[:16].replace("T", " ")
        first_ts = first_ts or ts
        who = "COMPACT SUMMARY" if e.get("isCompactSummary") else ("USER" if e["type"] == "user" else "CLAUDE")
        lines.append(f"### {who} · {ts}\n\n{t}\n")
    slug = re.sub(r"[^\w가-힣]+", "-", title).strip("-")[:40] or "untitled"
    name = f"{(first_ts or '0000-00-00')[:10]}_{cli[:8]}_{slug}.md"
    body = (f"# {title}\n\n- CLI session: `{cli}`\n- Desktop session: `{local_id}`\n"
            f"- Raw transcript: `%USERPROFILE%\\.claude\\projects\\{proj.name}\\{cli}.jsonl`\n\n---\n\n" + "\n".join(lines))
    (out / name).write_text(body, encoding="utf-8")
    print(f"{name}\t{len(body) // 1024} KB")
