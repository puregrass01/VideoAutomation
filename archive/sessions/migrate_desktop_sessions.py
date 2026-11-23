"""Show this project's Claude desktop sessions in another account's sidebar.

Transcripts (~/.claude/projects) and memory are shared by every account on this PC.
Only the sidebar records under claude-code-sessions/<account>/<org>/ are per account,
so this copies this project's local_*.json records into the target account's org folder.

Usage: py -3 archive/sessions/migrate_desktop_sessions.py <account-id-prefix> [org-id-prefix]
Re-run any time; it only copies records that are missing or newer.
"""
import json, os, pathlib, shutil, sys

project = str(pathlib.Path(__file__).resolve().parents[2]).casefold()
root = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Claude-Data/claude_pzs8sxrjxfjjc/claude-code-sessions"
acct = next(d for d in root.iterdir() if d.name.startswith(sys.argv[1]))
orgs = [o for o in acct.iterdir() if o.is_dir() and (len(sys.argv) < 3 or o.name.startswith(sys.argv[2]))]
# without an org given, use the one where this account already keeps its sessions
target = max(orgs, key=lambda o: len(list(o.glob("local_*.json"))))

for f in root.glob("*/*/local_*.json"):
    if f.parent == target:
        continue
    if (json.loads(f.read_text(encoding="utf-8")).get("cwd") or "").casefold() != project:
        continue
    dst = target / f.name
    if dst.exists() and dst.stat().st_mtime >= f.stat().st_mtime:
        continue
    shutil.copy2(f, dst)
    print("copied", f.name, "->", target.relative_to(root))
