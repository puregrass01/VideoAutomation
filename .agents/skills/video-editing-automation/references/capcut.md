# CapCut (`pyCapCut`) Reference

## 1. CapCut Draft Encryption & Integrity Check

Run this one-liner via `terminal` after CapCut exits to verify whether a draft (including nested `Timelines/`) is plaintext JSON (`b'{'`):

```bash
py -c "import sys,pathlib; d=pathlib.Path(sys.argv[1]); [print(p, open(p,'rb').read(1)) for p in [d/'draft_content.json', *d.glob('Timelines/*/draft_content.json')] if p.exists()]" "<draft_folder_path>"
```

- **Plaintext**: Every existing `draft_content.json` (root and `Timelines/*`) starts with `b'{'`.
- **Encrypted / Partial-Encrypted**: Any `draft_content.json` starts with a non-`{` byte (e.g., base64/cipher header). Do not attempt decryption and do not load partial-encrypted drafts via `pyCapCut` template mode.

## 2. CapCut Text Font & Background Injection (`draft_content.json`)

When injecting a cached CapCut font (such as static `NotoSansKR-Regular.otf` under `User Data/Cache/effect/<resource_id>/<hash>/NotoSansKR-Regular.otf`), populate both `materials.texts[].fonts` and `content.styles[].font`:

```python
noto_id = "7189852363404874242"
noto_path = "C:/Users/<user>/AppData/Local/CapCut/User Data/Cache/effect/7189852363404874242/4867c0fc2fd7265ca0c71e2f16e01ef2/NotoSansKR-Regular.otf"

for tx in dc.get("materials", {}).get("texts", []):
    tx["fonts"] = [{
        "id": str(uuid.uuid4()).upper(),
        "resource_id": noto_id,
        "third_resource_id": "",
        "category_id": "",
        "category_name": "",
        "source_platform": 1,
        "path": noto_path,
        "effect_id": "",
        "title": "Noto Sans KR",
        "team_id": "",
        "file_uri": "",
        "request_id": ""
    }]
    cobj = json.loads(tx.get("content", "{}"))
    for st in cobj.get("styles", []):
        st["font"] = {"id": noto_id, "path": noto_path}
        st["strokes"] = []  # No text outline per user preference
    tx["content"] = json.dumps(cobj, ensure_ascii=False)
```

For the text background box in `pyCapCut`:

```python
tseg = cc.TextSegment(
    text_str,
    cc.trange(start_str, dur_str),
    style=cc.TextStyle(size=12.0, color=(1.0, 1.0, 0.0), align=1),
    clip_settings=cc.ClipSettings(transform_y=-0.55),
    background=cc.TextBackground(
        color="#000000",
        style=1,
        alpha=0.75,
        round_radius=0.14,
        height=0.18,
        width=0.18,
    ),
)
```
