# Hallmark · v2.0.0 · theme: cobalt (by request) · genre: modern-minimal · scope: app (tkinter)
# critique: a work tool, so one idea per panel; cobalt is the single signal (linked cars, the run-all key, focus), the log is the graphite panel
# tokens: the Cobalt OKLCH tokens converted to sRGB hex (tkinter has no oklch); Pretendard stands in for Familjen Grotesk / IBM Plex Sans (Korean), Consolas for JetBrains Mono

import json
import os
import time
import pathlib
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

REPO_ROOT = pathlib.Path(__file__).resolve().parent
WORK_DIR = REPO_ROOT / "video-automation" / "work"
# Jobs run on python.exe, not this pythonw.exe: started with CREATE_NO_WINDOW, python.exe gets a hidden console that
# its own console children (ffmpeg, gdrive.cmd, agy) inherit. pythonw has none, so each of those opened a terminal.
_console_py = pathlib.Path(sys.executable).with_name("python.exe")
PYTHON = str(_console_py) if _console_py.exists() else sys.executable
NO_CAR_PREVIEW = "# Drive 차종 폴더를 고르면 그 차의 썸네일이 여기에 나옵니다"
PROGRESS_RE = re.compile(r"\s*\[진행 (\d+)%\] ?(.*)")  # gdrive_pipeline.gauge(): moves the 실행 로그 gauge, not logged
sys.path.insert(0, str(WORK_DIR))
import drive_index  # noqa: E402  (Drive vehicle folder index for the section 03 table)
import llm  # noqa: E402  (which LLM model each task uses; llm_config.json)
from portable_paths import MEDIA_DIR, OUTPUT_DIR as OUTPUT_ROOT  # noqa: E402  (the data folder: 구글드라이브다운파일)

# Hallmark Cobalt tokens: cool near-white paper, blue-grey ink and hairlines, graphite for the log, one cobalt signal
PAPER          = "#F8FBFE"
PAPER_2        = "#EFF3F8"
PAPER_3        = "#E3E8EF"
INK            = "#111825"
INK_2          = "#363E49"
MUTED          = "#5D646E"
RULE           = "#DADEE4"
RULE_2         = "#C2C8CF"
ACCENT         = "#0462D3"
ACCENT_2       = "#75B4FF"
ACCENT_INK     = "#F8FBFE"
ACCENT_WASH    = "#E3F0FF"
ACCENT_EDGE    = "#003D98"
KEY_FACE       = "#FCFDFF"
KEY_EDGE       = "#B7BEC8"
GRAPHITE       = "#121823"
GRAPHITE_2     = "#1E2532"
GRAPHITE_INK   = "#E3E8EE"
GRAPHITE_MUTED = "#939CA9"
FONT_UI        = "Pretendard"
FONT_MONO      = "Consolas"

def recent_work(limit: int = 15) -> tuple:
    """(where each kind of result lives, the newest results [(modified time, kind, path)]): CapCut drafts in CapCut's
    folder and in capcut_stage (built while CapCut was open), thumbnails and reports in output/<car>/, scenarios."""
    from portable_paths import DRAFT_ROOT
    places = [("CapCut 초안", DRAFT_ROOT), ("배포 대기 초안", WORK_DIR / "capcut_stage"),
              ("썸네일·리포트", OUTPUT_ROOT), ("시나리오", WORK_DIR / "scenarios")]
    found = []
    for kind, root in places:
        if not root.is_dir():
            continue
        if kind.endswith("초안"):
            items = [d / "draft_content.json" for d in root.glob("hermes_*") if (d / "draft_content.json").exists()]
        elif kind == "시나리오":
            items = list(root.glob("*.json"))
        else:
            items = [f for f in root.glob("*/*") if f.is_file()]
        found += [(f.stat().st_mtime, kind, f.parent if f.name == "draft_content.json" else f) for f in items]
    return places, sorted(found, key=lambda x: x[0], reverse=True)[:limit]


def recent_work_log(limit: int = 15) -> str:
    """The 실행 로그 lines the window starts with: where results live, then the newest ones (modified time, file)."""
    places, items = recent_work(limit)
    out = ["", "[작업 내역 위치]"] + [f"  {k}: {p}" for k, p in places]
    out.append(f"[최근 작업 {len(items)}개] 수정한 날짜 · 종류 · 파일 이름")
    for t, kind, path in items:
        out.append(f"  {time.strftime('%Y-%m-%d %H:%M', time.localtime(t))}  {kind}  {path.name}  ({path.parent})")
    return "\n".join(out) + "\n"


class OpticGlassTerminalApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OpticGlass 영상 자동화")
        self.geometry("1360x880")
        self.minsize(1180, 780)
        self.configure(bg=PAPER)

        ico_path = REPO_ROOT / "video-automation" / "assets" / "logos" / "opticglass.ico"
        if ico_path.exists():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

        self.log_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self.current_proc: subprocess.Popen | None = None
        self.is_running = False
        self.preview_photo = None
        self.preview_paths: list = []  # the thumbnails shown in the preview, newest first (at most 2)
        self.preview_slots: list = []
        self.preview_slug: str | None = None  # the car in the preview: the picked Drive folder's, None when unlinked
        self.use_ai_bg = tk.BooleanVar(value=False)  # optional AI-background thumbnail pair (--ai-bg); off by default

        self._build_layout()
        self.after(80, self._poll_log_queue)

    def _build_layout(self) -> None:
        # Header: the product name and what it makes, ruled off by one hairline
        header = tk.Frame(self, bg=PAPER, height=56, highlightthickness=1, highlightbackground=RULE)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="OpticGlass 영상 자동화",
            bg=PAPER,
            fg=INK,
            font=(FONT_UI, 14, "bold"),
        ).pack(side="left", padx=(18, 16))

        tk.Label(
            header,
            text="유튜브 16:9 롱폼, 9:16 숏폼, 1280x720 썸네일",
            bg=PAPER,
            fg=MUTED,
            font=(FONT_UI, 9),
        ).pack(side="left")

        self.status_badge = tk.Label(
            header,
            text="대기 중",
            bg=PAPER_2,
            fg=INK_2,
            font=(FONT_UI, 9, "bold"),
            padx=10,
            pady=5,
        )
        self.status_badge.pack(side="right", padx=18)

        # the agy model the pipeline uses (llm_config.json) and whether agy is ready; 모델 설정 opens the config
        tk.Button(header, text="모델 설정", command=self._open_llm_config, **self._small_btn_style()).pack(side="right")
        self.llm_label = tk.Label(header, text="", bg=PAPER, fg=MUTED, font=(FONT_UI, 9))
        self.llm_label.pack(side="right", padx=(0, 8))
        self._refresh_llm_status()
        self.bind("<FocusIn>", lambda e: self._refresh_llm_status())  # any widget: the tree or search box keeps focus

        # Main 2-column grid (Fixed 500px left command panel + flexible right viewport)
        body = tk.Frame(self, bg=PAPER, padx=14, pady=14)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, minsize=500, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=PAPER_2, width=500, padx=16, pady=14, highlightthickness=1, highlightbackground=RULE)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_propagate(False)

        right = tk.Frame(body, bg=PAPER)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=58)
        right.rowconfigure(1, weight=42)
        right.columnconfigure(0, weight=1)

        self._build_left_controls(left)
        self._build_right_panels(right)

    def _section_label(self, parent: tk.Widget, text: str, pady=(10, 4)) -> None:
        tk.Label(
            parent,
            text=text,
            bg=PAPER_2,
            fg=MUTED,
            font=(FONT_UI, 9),
            anchor="w",
        ).pack(fill="x", pady=pady)

    def _command_row_btn(
        self,
        parent: tk.Widget,
        title: str,
        synopsis: str,
        command,
        primary: bool = False,
    ) -> None:
        bg = ACCENT if primary else KEY_FACE
        fg = ACCENT_INK if primary else INK
        syn_fg = ACCENT_WASH if primary else MUTED
        border = ACCENT_EDGE if primary else RULE_2

        edge = tk.Frame(parent, bg=ACCENT_EDGE if primary else KEY_EDGE)  # the key's bottom edge
        edge.pack(fill="x", pady=3)
        frame = tk.Frame(edge, bg=bg, highlightthickness=1, highlightbackground=border, cursor="hand2")
        frame.pack(fill="x", pady=(0, 2))

        lbl_t = tk.Label(frame, text=title, bg=bg, fg=fg, font=(FONT_UI, 10, "bold"), anchor="w", padx=12)
        lbl_t.pack(fill="x", pady=(6, 0))
        lbl_s = tk.Label(frame, text=synopsis, bg=bg, fg=syn_fg, font=(FONT_MONO, 8), anchor="w", padx=12)
        lbl_s.pack(fill="x", pady=(0, 6))

        for w in (frame, lbl_t, lbl_s):
            w.bind("<Button-1>", lambda e: command())

    def _build_left_controls(self, parent: tk.Frame) -> None:
        self._section_label(parent, "설치", pady=(0, 4))
        self._command_row_btn(
            parent,
            "[1] 새 PC 초기 세팅 실행",
            "$ setup.bat  (프로그램 설치 + 폰트 + pyCapCut + 세션 복원)",
            self.run_step1_setup,
        )

        self._section_label(parent, "Drive 차종 폴더: 고른 차로 롱폼 / 숏폼 / 썸네일")
        self._build_drive_table(parent)

        # the desktop agent's prompt box: an instruction for the car's video (agy_edit.py, llm_config.json video_edit model, subscription)
        agy_hdr = tk.Frame(parent, bg=PAPER_2)
        agy_hdr.pack(fill="x", pady=(12, 4))
        tk.Label(agy_hdr, text="agy 영상 수정", bg=PAPER_2, fg=MUTED, font=(FONT_UI, 9)).pack(side="left")
        self.agy_target = tk.Label(agy_hdr, text="", bg=PAPER_2, fg=ACCENT, font=(FONT_MONO, 9))
        self.agy_target.pack(side="left", padx=(8, 0))
        self.agy_new_btn = tk.Button(agy_hdr, text="새 대화", command=self.new_agy_session, **self._small_btn_style())
        self.agy_new_btn.pack(side="right")
        self.agy_box = tk.Text(parent, height=4, bg=PAPER, fg=INK, insertbackground=ACCENT, relief="flat", wrap="word",
                               font=(FONT_UI, 9), padx=8, pady=6, highlightthickness=1, highlightbackground=RULE_2,
                               highlightcolor=ACCENT)
        self.agy_box.pack(fill="x")
        self.agy_box.bind("<Control-Return>", lambda e: (self.send_agy(), "break")[1])
        agy_act = tk.Frame(parent, bg=PAPER_2)
        agy_act.pack(fill="x", pady=(4, 0))
        tk.Label(agy_act, text="예: s05 자막을 더 짧게, 비교 장면을 1초 늘려줘 (Ctrl+Enter)\n안티그라비티에서도 켜서 사용가능함",
                 bg=PAPER_2, fg=MUTED, font=(FONT_UI, 8), anchor="w", justify="left").pack(side="left", fill="x", expand=True)
        self.agy_send_btn = tk.Button(agy_act, text="→", command=self.send_agy, **self._small_btn_style())
        self.agy_send_btn.pack(side="right")
        self._update_agy_target()  # a car folder with a longform scenario: edit it; otherwise a plain conversation

    def _build_drive_table(self, parent: tk.Frame) -> None:
        """Drive '0.옵틱 광각' as a normalized browser (drive_index.group_of): brand buttons, then that brand's models,
        then the dated job folders of one model, where a folder is picked and run. Search jumps straight to matching
        folders across all brands; 뒤로가기 goes up one level (or clears the search)."""
        self.nav_brand: str | None = None
        self.nav_model: str | None = None
        nav = tk.Frame(parent, bg=PAPER_2)
        nav.pack(fill="x", pady=(0, 4))
        self.back_btn = tk.Button(nav, text="뒤로가기", command=self._browser_back, **self._small_btn_style())
        self.back_btn.pack(side="left")
        self.crumb = tk.Label(nav, text="", bg=PAPER_2, fg=INK, font=(FONT_UI, 9, "bold"), anchor="w")
        self.crumb.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.optic_only = tk.BooleanVar(value=True)
        self.optic_btn = tk.Button(nav, text="옵틱만 보기: 켬", command=self._toggle_optic_only, **self._small_btn_style())
        self.optic_btn.pack(side="left", padx=(6, 0))
        self.drive_refresh_btn = tk.Button(nav, text="새로고침", command=lambda: self._load_drive_index(refresh=True), **self._small_btn_style())
        self.drive_refresh_btn.pack(side="left", padx=(4, 0))

        search = tk.Frame(parent, bg=PAPER_2)
        search.pack(fill="x", pady=(0, 4))
        tk.Label(search, text="검색", bg=PAPER_2, fg=MUTED, font=(FONT_UI, 8)).pack(side="left", padx=(0, 6))
        self.vehicle_filter = tk.StringVar()
        tk.Entry(
            search, textvariable=self.vehicle_filter, bg=PAPER, fg=INK, insertbackground=ACCENT, relief="flat",
            font=(FONT_UI, 9), highlightthickness=1, highlightbackground=RULE_2, highlightcolor=ACCENT,
        ).pack(side="left", fill="x", expand=True, ipady=3)
        self.vehicle_filter.trace_add("write", lambda *_: self._render_browser())

        # one fixed-height well: brand/model buttons or the folder list
        self.browser = tk.Frame(parent, bg=PAPER, height=300, highlightthickness=1, highlightbackground=RULE_2)
        self.browser.pack(fill="x")
        self.browser.pack_propagate(False)
        self.chip_canvas = tk.Canvas(self.browser, bg=PAPER, highlightthickness=0, bd=0)
        self.chip_scroll = ttk.Scrollbar(self.browser, orient="vertical", command=self.chip_canvas.yview)
        self.chip_canvas.configure(yscrollcommand=self.chip_scroll.set)
        self.chip_frame = tk.Frame(self.chip_canvas, bg=PAPER)
        self.chip_window = self.chip_canvas.create_window((0, 0), window=self.chip_frame, anchor="nw")
        self.chip_frame.bind("<Configure>", lambda e: self.chip_canvas.configure(scrollregion=self.chip_canvas.bbox("all")))
        self.chip_canvas.bind("<Configure>", lambda e: self.chip_canvas.itemconfigure(self.chip_window, width=e.width))
        self.chip_canvas.bind("<Enter>", lambda e: self.chip_canvas.bind_all("<MouseWheel>", self._chip_wheel))
        self.chip_canvas.bind("<Leave>", lambda e: self.chip_canvas.unbind_all("<MouseWheel>"))

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Drive.Treeview", background=PAPER, fieldbackground=PAPER, foreground=INK_2, rowheight=20,
                        font=(FONT_UI, 8), borderwidth=0)
        style.configure("Drive.Treeview.Heading", background=PAPER_2, foreground=MUTED, font=(FONT_UI, 8), relief="flat")
        style.map("Drive.Treeview", background=[("selected", ACCENT_WASH)], foreground=[("selected", ACCENT)])
        style.map("Drive.Treeview.Heading", background=[("active", PAPER_3)])
        style.configure("Vertical.TScrollbar", background=PAPER_2, troughcolor=PAPER, bordercolor=RULE, arrowcolor=MUTED)
        self.tree_frame = tk.Frame(self.browser, bg=PAPER)
        self.vehicle_tree = ttk.Treeview(self.tree_frame, columns=("folder", "product", "state"), show="headings",
                                         style="Drive.Treeview", selectmode="browse")
        for col, text, width in (("folder", "Drive 폴더", 216), ("product", "제품", 44), ("state", "상태 / 작업일", 166)):
            self.vehicle_tree.heading(col, text=text, anchor="w")
            self.vehicle_tree.column(col, width=width, minwidth=40, stretch=col == "folder", anchor="w")
        self.vehicle_tree.tag_configure("linked", foreground=ACCENT)
        tree_scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.vehicle_tree.yview)
        self.vehicle_tree.configure(yscrollcommand=tree_scroll.set)
        self.vehicle_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.vehicle_tree.bind("<<TreeviewSelect>>", lambda e: self._update_drive_action())
        self.vehicle_tree.bind("<Button-3>", self._drive_menu)

        self.drive_info = tk.Label(parent, text="Drive 인덱스 불러오는 중", bg=PAPER_2, fg=MUTED, font=(FONT_UI, 8), anchor="w")
        self.drive_info.pack(fill="x", pady=(4, 0))
        # what to make from the picked folder; an unlinked folder is linked to a slug first
        act = tk.Frame(parent, bg=PAPER_2)
        act.pack(fill="x", pady=(4, 0))
        self.long_btn = tk.Button(act, text="숏폼", command=self.run_longform, state="disabled", **self._small_btn_style())
        self.thumb_btn = tk.Button(act, text="썸네일", command=self.run_thumbnail, state="disabled", **self._small_btn_style())
        # below: the CapCut templates' edits of the same car (광각미러 템플릿 1, 숏폼 영상 프로젝트), each its own draft
        self.wide_btn = tk.Button(act, text="광각미러 템플릿 롱폼", command=lambda: self.run_build("wide1"), state="disabled", **self._small_btn_style())
        self.short_btn = tk.Button(act, text="릴스/인스타", command=lambda: self.run_build("shorts"), state="disabled", **self._small_btn_style())
        for i in range(2):
            act.columnconfigure(i, weight=1, uniform="act")
        for r, row_btns in enumerate(((self.long_btn, self.thumb_btn), (self.wide_btn, self.short_btn))):
            for i, b in enumerate(row_btns):
                b.grid(row=r, column=i, sticky="ew", padx=2, pady=(0, 3) if r == 0 else 0)
        self.drive_rows: list[dict] = []
        self.drive_fetched = ""
        self.after(300, self._load_drive_index)

    def _small_btn_style(self) -> dict:
        return dict(bg=KEY_FACE, fg=INK_2, activebackground=ACCENT_WASH, activeforeground=ACCENT, relief="flat",
                    disabledforeground=RULE_2, font=(FONT_UI, 8), padx=8, pady=2, cursor="hand2",
                    highlightthickness=1, highlightbackground=RULE_2)

    def _chip_wheel(self, event) -> None:
        self.chip_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _load_drive_index(self, refresh: bool = False) -> None:
        self.drive_info.configure(text="Drive 폴더 목록 받는 중 (약 10초)" if refresh else "Drive 인덱스 불러오는 중")
        self.drive_refresh_btn.configure(state="disabled")  # one load at a time

        def work() -> None:
            try:
                rows, fetched = drive_index.load(refresh)
                self.after(0, lambda: self._set_drive_rows(rows, fetched))
            except Exception as exc:  # gdrive CLI not logged in, offline, ...
                self.after(0, lambda msg=str(exc): self.drive_info.configure(text=f"Drive 인덱스 실패: {msg[:80]}"))
            finally:
                self.after(0, lambda: self.drive_refresh_btn.configure(state="normal"))

        threading.Thread(target=work, daemon=True).start()

    def _set_drive_rows(self, rows: list[dict], fetched: str) -> None:
        for r in rows:
            r.update(drive_index.parse_name(r["name"]))  # the cache may predate the current parser
            r["brand"], r["mkey"] = drive_index.group_of(r)
        self.drive_rows, self.drive_fetched = rows, fetched
        self._render_browser()

    def _toggle_optic_only(self) -> None:
        self.optic_only.set(not self.optic_only.get())
        self.optic_btn.configure(text="옵틱만 보기: " + ("켬" if self.optic_only.get() else "끔"))
        self._render_browser()

    def _drive_links_by_id(self) -> dict:
        return {v["folder_id"]: slug for slug, v in drive_index.links().items()}

    def _browser_back(self) -> None:
        if self.vehicle_filter.get().strip():
            self.vehicle_filter.set("")  # the trace re-renders
            return
        if self.nav_model:
            self.nav_model = None
        else:
            self.nav_brand = None
        self._render_browser()

    def _open_group(self, value: str) -> None:
        if self.nav_brand is None:
            self.nav_brand = value
        else:
            self.nav_model = value
        self._render_browser()

    def _render_browser(self) -> None:
        if not self.drive_rows:
            return
        query = self.vehicle_filter.get().strip()
        rows = drive_index.find(self.drive_rows, query, {"opticglass"} if self.optic_only.get() else None)
        linked = set(self._drive_links_by_id())
        if query:
            self.crumb.configure(text=f"검색 결과: {query}")
            self._show_folders(rows)
        elif self.nav_brand and self.nav_model:
            self.crumb.configure(text=f"전체 / {self.nav_brand} / {self.nav_model}")
            self._show_folders([r for r in rows if r["brand"] == self.nav_brand and r["mkey"] == self.nav_model])
        elif self.nav_brand:
            self.crumb.configure(text=f"전체 / {self.nav_brand}")
            self._show_groups([r for r in rows if r["brand"] == self.nav_brand], "mkey", linked)
        else:
            self.crumb.configure(text="전체 브랜드")
            self._show_groups(rows, "brand", linked)
        self.back_btn.configure(state="normal" if (query or self.nav_brand) else "disabled")
        self._update_drive_action()

    def _show_groups(self, rows: list[dict], key: str, linked: set) -> None:
        """Brand or model buttons with their folder counts; a group holding a linked car is set in cobalt."""
        self.tree_frame.pack_forget()
        self.chip_scroll.pack(side="right", fill="y")
        self.chip_canvas.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        for w in self.chip_frame.winfo_children():
            w.destroy()
        counts: dict[str, int] = {}
        has_link: set = set()
        for r in rows:
            counts[r[key]] = counts.get(r[key], 0) + 1
            if r["id"] in linked:
                has_link.add(r[key])
        order = sorted(counts, key=lambda g: (g == "기타", g not in has_link, -counts[g], g))
        for i, g in enumerate(order):
            on = g in has_link
            b = tk.Button(self.chip_frame, text=f"{g}  {counts[g]}", command=lambda v=g: self._open_group(v),
                          bg=ACCENT_WASH if on else KEY_FACE, fg=ACCENT if on else INK, activebackground=ACCENT_WASH,
                          activeforeground=ACCENT, relief="flat", font=(FONT_UI, 9, "bold" if on else "normal"),
                          anchor="w", padx=8, pady=3, cursor="hand2", highlightthickness=1,
                          highlightbackground=ACCENT if on else RULE_2)
            b.grid(row=i // 4, column=i % 4, sticky="ew", padx=2, pady=2)
        for c in range(4):
            self.chip_frame.columnconfigure(c, weight=1, uniform="chip")
        self.chip_canvas.yview_moveto(0)
        self.vehicle_tree.selection_remove(self.vehicle_tree.selection())
        level = "브랜드" if key == "brand" else "모델"
        self.drive_info.configure(text=f"{level} {len(order)}개, 폴더 {len(rows)}개 ({self.drive_fetched[:16].replace('T', ' ')} 기준)")

    def _show_folders(self, rows: list[dict]) -> None:
        self.chip_canvas.pack_forget()
        self.chip_scroll.pack_forget()
        self.tree_frame.pack(fill="both", expand=True)
        self._fill_vehicle_table(rows)

    def _fill_vehicle_table(self, rows: list[dict] | None = None) -> None:
        if rows is None:  # after a run: refresh whatever level is showing
            self._render_browser()
            return
        by_id = self._drive_links_by_id()
        rows = sorted(rows, key=lambda r: r["id"] not in by_id)  # linked first; the cache is newest-first otherwise
        keep = self.vehicle_tree.selection()
        self.vehicle_tree.delete(*self.vehicle_tree.get_children())
        for r in rows[:300]:
            slug = by_id.get(r["id"])
            state = f"{slug}: {drive_index.status_text(slug)}" if slug else (r["date"] or r["modified"])
            product = "/".join(drive_index.PRODUCT_KO[p] for p in r["products"]) or "?"
            self.vehicle_tree.insert("", "end", iid=r["id"], values=(r["name"], product, state), tags=("linked",) if slug else ())
        self.vehicle_tree.yview_moveto(0)  # Tk keeps the old scroll offset across a refill otherwise
        if keep and self.vehicle_tree.exists(keep[0]):
            self.vehicle_tree.selection_set(keep[0])
            self.vehicle_tree.see(keep[0])
        more = " (300개까지 표시)" if len(rows) > 300 else ""
        self.drive_info.configure(text=f"폴더 {len(rows)}개{more}: 폴더를 고르고 아래 버튼으로 실행 (우클릭: Drive 가기 / 폴더 가기 / 영상 삭제)")
        self._update_drive_action()

    def _drive_menu(self, event) -> None:
        """Right-click a row: open its Drive folder in the browser, its folder on this PC (media/<Drive path>/:
        downloads, scene clips, thumbnails) in Explorer, or delete the videos downloaded from it."""
        fid = self.vehicle_tree.identify_row(event.y)  # the row iid is the Drive folder id
        if not fid:
            return
        self.vehicle_tree.selection_set(fid)
        slug = self._drive_links_by_id().get(fid)
        menu = tk.Menu(self, tearoff=0, bg=PAPER, fg=INK, activebackground=ACCENT_WASH, activeforeground=ACCENT,
                       font=(FONT_UI, 9))
        menu.add_command(label="드라이브 가기", command=lambda: webbrowser.open(f"https://drive.google.com/drive/folders/{fid}"))
        local = drive_index.media_dir(slug) if slug else None
        menu.add_command(label="폴더 가기", command=lambda: os.startfile(local),
                         state="normal" if local and local.is_dir() else "disabled")
        menu.add_command(label="폴더 영상 삭제", command=lambda: self._delete_downloaded_videos(slug),
                         state="normal" if slug and self._downloaded_videos(slug) else "disabled")
        menu.tk_popup(event.x_root, event.y_root)

    @staticmethod
    def _downloaded_videos(slug: str) -> list:
        raw = drive_index.media_dir(slug) / "gdrive_raw"
        return [p for p in raw.rglob("*") if p.suffix.lower() in (".mov", ".mp4") and p.is_file()] if raw.exists() else []

    def _delete_downloaded_videos(self, slug: str) -> None:
        """The videos gdrive_pipeline downloaded for this car (its gdrive_raw; photos, scene clips and drafts stay).
        Drive keeps the originals: the next 롱폼 run downloads what the scenario needs again."""
        if self._busy():
            return
        vids = self._downloaded_videos(slug)
        size_gb = sum(p.stat().st_size for p in vids) / 1024 ** 3
        if not vids or not messagebox.askokcancel(
                "폴더 영상 삭제", f"{slug}: 내려받은 영상 {len(vids)}개 ({size_gb:.1f} GB)를 이 PC에서 지웁니다.\n"
                f"{drive_index.media_dir(slug) / 'gdrive_raw'}\n\nDrive 원본은 그대로이며, 다음 롱폼·썸네일 실행 때 다시 받습니다. "
                "사진·장면 클립·CapCut 초안은 남지만, 초안 미디어함의 원본 영상은 다시 받기 전까지 '없음'으로 보입니다."):
            return
        failed = []
        for p in vids:
            try:
                p.unlink()
            except OSError:  # a player or CapCut holding the file
                failed.append(p.name)
        self._append_log(f"[영상 삭제] {slug}: {len(vids) - len(failed)}개 지움" + (f", 못 지움 {len(failed)}개: {', '.join(failed[:5])}" if failed else "") + "\n")
        self._fill_vehicle_table()

    def _selected_drive_row(self) -> dict | None:
        sel = self.vehicle_tree.selection()
        return next((r for r in self.drive_rows if r["id"] == sel[0]), None) if sel else None

    def _picked_slug(self) -> str | None:
        """The linked slug of the picked folder; None when nothing is picked or the folder is not linked yet."""
        row = self._selected_drive_row()
        return self._drive_links_by_id().get(row["id"]) if row else None

    def _update_drive_action(self) -> None:
        row, slug = self._selected_drive_row(), self._picked_slug()
        # a car without a longform scenario gets one from its own clips when 롱폼 runs (make_scenario.py)
        for b in (self.long_btn, self.thumb_btn, self.wide_btn, self.short_btn):
            b.configure(state="normal" if row else "disabled")
        self._update_agy_target()
        if slug != self.preview_slug:  # the preview follows the picked folder (empty for a folder not linked yet)
            self.load_vehicle_preview(slug)

    def _refresh_llm_status(self) -> None:
        try:
            st = llm.status()
            self.llm_label.configure(text=f"agy {llm.model_for('video_edit')} ({st['note']})", fg=INK_2 if st["ready"] else MUTED)
        except Exception as exc:  # unreadable llm_config.json
            self.llm_label.configure(text=f"LLM 설정 오류: {str(exc)[:40]}", fg=INK)

    def _open_llm_config(self) -> None:
        subprocess.Popen(["notepad", str(llm.CONFIG)])  # status refreshes when this window gets focus back

    def _busy(self) -> bool:
        if self.is_running:
            messagebox.showinfo("opticglass-gui", "이미 실행 중인 작업이 있습니다. 완료 후 다시 시도하세요.")
        return self.is_running

    def _link_picked(self) -> tuple:
        """(slug, row) of the picked folder, linking it first when it has none: its id comes from the Drive name
        (drive_index.auto_slug) and its media goes under its Drive path, so nobody names folders. (None, None) when
        nothing is picked, a job runs, or the person cancels."""
        row = self._selected_drive_row()
        if not row or self._busy():
            return None, None
        slug = self._drive_links_by_id().get(row["id"])
        if slug:
            return slug, row
        slug = drive_index.auto_slug(row)
        media_label = MEDIA_DIR.relative_to(REPO_ROOT).as_posix() if MEDIA_DIR.is_relative_to(REPO_ROOT) else str(MEDIA_DIR).replace("\\", "/")
        if not messagebox.askokcancel("새 차종 연결", f"{row['name']}\n\nDrive에서 미디어를 {media_label}/{drive_index.drive_path(row)}/gdrive_raw로 "
                                      f"내려받습니다.\n(파일·CapCut 초안 이름: {slug})"):
            return None, None
        try:
            drive_index.link(slug, row)
        except ValueError as exc:
            messagebox.showerror("opticglass-gui", str(exc))
            return None, None
        self._fill_vehicle_table()
        return slug, row

    def _thumb_flags(self) -> list:
        return ["--ai-bg"] if self.use_ai_bg.get() else []

    def _toggle_ai_bg(self) -> None:
        on = not self.use_ai_bg.get()
        self.use_ai_bg.set(on)
        self.ai_bg_btn.configure(
            text="AI 배경: " + ("켬" if on else "끔"),
            bg=ACCENT_WASH if on else KEY_FACE,
            fg=ACCENT if on else INK_2,
            highlightbackground=ACCENT if on else RULE_2,
        )

    def _pipeline_cmd(self, slug: str, *extra: str) -> list:
        # gdrive_pipeline.fetch_reason decides whether to sync the car's linked Drive folder first
        thumb_flags = [] if "--build" in extra else self._thumb_flags()
        return [PYTHON, "video-automation/work/gdrive_pipeline.py", "--vehicle", slug, *extra, *thumb_flags]

    def run_longform(self) -> None:
        """Download (first run), write the car's scenario when it has none (agy, from its clips), build the CapCut
        longform draft, check it, then the thumbnails."""
        slug, row = self._link_picked()
        if slug:
            self._run_commands_async(f"숏폼 {slug} ({row['name']})", self._pipeline_cmd(slug), slug)

    BUILD_TITLES = {"wide1": "광각미러 템플릿 롱폼", "shorts": "릴스/인스타"}

    def run_build(self, build: str) -> None:
        """광각미러 템플릿 (wide1): the car's longform on 「옵틱글래스 광각미러 템플릿 1」, its scenario written by agy from
        its clips when it has none (a copy of the longform's when that already is this template), as the draft hermes_<car>_optic_wide1. 숏폼 (shorts): five 9:16 shorts cut from the
        car's longform clips on 「숏폼 영상 프로젝트」, hooks by agy, as hermes_<car>_optic_shorts. No thumbnails."""
        slug, row = self._link_picked()
        if slug:
            self._run_commands_async(f"{self.BUILD_TITLES[build]} {slug} ({row['name']})",
                                     self._pipeline_cmd(slug, "--build", build), slug)

    def run_thumbnail(self) -> None:
        """Thumbnails only (downloading the photos first if the car never ran): agy picks and masks the photos when
        none are saved, checks the masked copies and fixes what it still sees; nobody is asked to pick photos."""
        slug, _row = self._link_picked()
        if slug:
            self.run_thumb_job(slug, self._pipeline_cmd(slug, "--skip-video-rebuild"))

    def run_thumb_job(self, slug: str, cmd: list) -> None:
        def report() -> None:  # agy picks and fixes the photos itself; the picker stays an optional override (button)
            if drive_index.status(slug)["thumb"] == "needs_photo_pick":
                self._append_log(f"[썸네일] {slug}: AI가 썸네일 사진을 완성하지 못했습니다. 위 [AI 검수 실패]/[가려지지 않음] 줄을 보세요.\n")

        self._run_commands_async(f"썸네일 {slug}", cmd, slug, then=report)

    def _agy_slug(self) -> str | None:
        """The car the agy box edits: the picked folder's car, if it has a longform or wide1 scenario."""
        slug = self._picked_slug()
        return slug if slug and any((WORK_DIR / "scenarios" / f"{slug}_{v}.json").exists() for v in ("longform", "wide1")) else None

    def _update_agy_target(self) -> None:
        slug = self._agy_slug()
        self.agy_target.configure(text=f"-> {slug} 롱폼 수정" if slug else "-> agy 대화 (롱폼 시나리오가 있는 차를 고르면 그 영상 수정)",
                                  fg=ACCENT if slug else MUTED)

    def send_agy(self) -> None:
        """The message to the Antigravity agent (agy_edit.py). With a car that has a longform scenario picked, it edits
        that scenario in the car's conversation and a change that passes the scenario check is rebuilt; otherwise it
        is a plain conversation (--chat, read-only)."""
        slug, text = self._agy_slug(), self.agy_box.get("1.0", "end").strip()
        if not text or self._busy():
            return
        self._append_log(f"\n[agy {'지시 -> ' + slug if slug else '대화'}] {text}\n")
        self.agy_box.delete("1.0", "end")
        if slug:
            # "--": a message starting with "-" stays the message, not an option
            self._run_commands_async(f"agy {slug}", [PYTHON, "video-automation/work/agy_edit.py", slug, "--", text], slug)
        else:
            self._run_commands_async("agy 대화", [PYTHON, "video-automation/work/agy_edit.py", "--chat", "--", text])

    def new_agy_session(self) -> None:
        slug = self._agy_slug()
        what, args = (f"{slug}의 agy 대화와 진행 중인 수정을", [slug]) if slug else ("차 없이 나눈 agy 대화를", ["--chat"])
        if not self._busy() and messagebox.askokcancel("새 대화", f"{what} 지우고 새로 시작합니다."):
            self._run_commands_async(f"agy {slug or '대화'} 새 대화", [PYTHON, "video-automation/work/agy_edit.py", *args, "--new"])

    def _build_right_panels(self, parent: tk.Frame) -> None:
        # Top-Right: Viewport Well
        p_well = tk.Frame(parent, bg=PAPER_2, padx=14, pady=10, highlightthickness=1, highlightbackground=RULE)
        p_well.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        p_hdr = tk.Frame(p_well, bg=PAPER_2)
        p_hdr.pack(fill="x", pady=(0, 6))
        tk.Label(
            p_hdr,
            text="썸네일 미리보기 (두 번 클릭하면 원본)",
            bg=PAPER_2,
            fg=INK,
            font=(FONT_UI, 10, "bold"),
        ).pack(side="left")

        # this car's thumbnail photos (to fix what the AI picked or masked), optional AI background, and the name on its thumbnail
        tk.Button(p_hdr, text="썸네일 사진", command=self._open_thumb_picker, **self._small_btn_style()).pack(side="right")
        self.ai_bg_btn = tk.Button(p_hdr, text="AI 배경: 끔", command=self._toggle_ai_bg, **self._small_btn_style())
        self.ai_bg_btn.pack(side="right", padx=(0, 6))
        self.car_title = tk.StringVar()
        self.title_slug: str | None = None
        title_entry = tk.Entry(p_hdr, textvariable=self.car_title, width=22, bg=PAPER, fg=INK, insertbackground=ACCENT,
                               relief="flat", font=(FONT_UI, 9), highlightthickness=1, highlightbackground=RULE_2,
                               highlightcolor=ACCENT)
        title_entry.pack(side="right", padx=(0, 6), ipady=2)
        title_entry.bind("<Return>", lambda e: self._save_car_title())
        title_entry.bind("<FocusOut>", lambda e: self._save_car_title())
        tk.Label(p_hdr, text="차 이름", bg=PAPER_2, fg=MUTED, font=(FONT_UI, 8)).pack(side="right", padx=(0, 6))
        self.thumb_picker: "ThumbPicker | None" = None

        self.preview_canvas = tk.Label(
            p_well,
            text=NO_CAR_PREVIEW,
            bg=PAPER,
            fg=MUTED,
            font=(FONT_MONO, 9),
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=RULE_2,
        )
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Double-Button-1>", self._open_current_preview_image)

        self.preview_path_label = tk.Label(
            p_well,
            text="",
            bg=PAPER_2,
            fg=MUTED,
            font=(FONT_MONO, 8),
            anchor="w",
        )
        self.preview_path_label.pack(fill="x", pady=(6, 0))

        # Bottom-Right: Live Session Well
        s_well = tk.Frame(parent, bg=PAPER_2, padx=14, pady=10, highlightthickness=1, highlightbackground=RULE)
        s_well.grid(row=1, column=0, sticky="nsew")

        s_hdr = tk.Frame(s_well, bg=PAPER_2)
        s_hdr.pack(fill="x", pady=(0, 6))
        tk.Label(
            s_hdr,
            text="실행 로그",
            bg=PAPER_2,
            fg=INK,
            font=(FONT_UI, 10, "bold"),
        ).pack(side="left")

        tk.Button(
            s_hdr,
            text="지우기",
            command=self._clear_log,
            bg=KEY_FACE,
            fg=INK_2,
            relief="flat",
            font=(FONT_UI, 8),
            padx=10,
            pady=2,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=RULE_2,
        ).pack(side="right", padx=(6, 0))

        self.stop_btn = tk.Button(
            s_hdr,
            text="작업 중지",
            command=self.stop_current_task,
            bg=PAPER,
            fg=MUTED,
            relief="flat",
            font=(FONT_UI, 8),
            padx=10,
            pady=2,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=RULE_2,
        )
        self.stop_btn.pack(side="right")

        # progress of the running job (download, longform build, photo check, thumbnails, AI background); shown from
        # the first job on (_set_gauge), so an idle window has no empty bar over the log
        g_row = self.gauge_row = tk.Frame(s_well, bg=PAPER_2)
        self.gauge_label = tk.Label(g_row, text="", bg=PAPER_2, fg=INK_2, font=(FONT_UI, 8), anchor="w", width=36)
        self.gauge_label.pack(side="right", padx=(8, 0))
        trough = tk.Frame(g_row, bg=PAPER_3, height=10, highlightthickness=1, highlightbackground=RULE_2)
        trough.pack(side="left", fill="x", expand=True)
        self.gauge_fill = tk.Frame(trough, bg=ACCENT)
        self.gauge_pct = 0.0

        self.log_text = tk.Text(  # the graphite panel: Cobalt runs machine output on graphite
            s_well,
            bg=GRAPHITE,
            fg=GRAPHITE_INK,
            insertbackground=ACCENT_2,
            selectbackground=GRAPHITE_2,
            font=(FONT_MONO, 9),
            relief="flat",
            padx=10,
            pady=8,
            wrap="word",
            state="disabled",
            highlightthickness=0,
        )
        self.log_text.pack(fill="both", expand=True)

        self._append_log(f"작업 폴더 {REPO_ROOT}\n")
        self._append_log("왼쪽 명령이나 Drive 차종 폴더를 실행하면 로그가 여기에 나옵니다.\n")
        def history() -> None:  # a file scan: off the UI thread
            try:
                self.log_queue.put((recent_work_log(), "muted"))
            except OSError as exc:  # a file vanished or locked mid-scan
                self.log_queue.put((f"[최근 작업] 읽지 못함: {exc}\n", "muted"))
        threading.Thread(target=history, daemon=True).start()

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _set_gauge(self, pct: float, label: str) -> None:
        if not self.gauge_row.winfo_ismapped():
            self.gauge_row.pack(fill="x", pady=(0, 6), before=self.log_text)
        self.gauge_pct = max(0.0, min(pct, 100.0))
        self.gauge_fill.place(x=0, y=0, relheight=1, relwidth=self.gauge_pct / 100)
        self.gauge_label.configure(text=f"{self.gauge_pct:.0f}%  {label}")

    def _poll_log_queue(self) -> None:
        """Log text, gauge moves and the job's finish, in the order the worker queued them."""
        try:
            while True:
                item, tag = self.log_queue.get_nowait()
                if tag == "progress":
                    self._set_gauge(*item)
                elif tag == "call":
                    item()
                else:
                    self._append_log(item)
        except queue.Empty:
            pass
        self.after(60, self._poll_log_queue)

    def _set_running_state(self, running: bool, status_text: str = "") -> None:
        self.is_running = running
        if running:
            self.status_badge.configure(text=f"실행 중: {status_text[:40]}", fg=ACCENT, bg=ACCENT_WASH)
            self.stop_btn.configure(fg=ACCENT, highlightbackground=ACCENT)
        else:
            self.stop_btn.configure(fg=MUTED, highlightbackground=RULE_2)

    def _run_commands_async(self, title: str, cmd: list[str], slug: str | None = None, then=None) -> None:
        """Runs cmd off the UI thread for the car slug (None: no car), streaming its output to the log; `then` runs on
        the UI thread when it exits 0."""
        if self._busy():
            return

        self._save_car_title()  # a name typed without Enter: buttons take no focus, so FocusOut has not fired
        self._set_running_state(True, title)
        self._set_gauge(0, title)
        self.log_queue.put(("\n+----------------------------------------------------------------------+\n", "rule"))
        self.log_queue.put((f"| EXEC: {title}\n", "accent"))
        self.log_queue.put(("+----------------------------------------------------------------------+\n", "rule"))

        started = time.time()

        def worker() -> None:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONUNBUFFERED"] = "1"  # a pipe is block-buffered: lines (agy's answer) would show up minutes late
            self.log_queue.put((f"\n~ $ {' '.join(cmd)}\n", "accent"))
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                self.current_proc = subprocess.Popen(
                    cmd,
                    cwd=str(REPO_ROOT),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    creationflags=creationflags,
                )
                assert self.current_proc.stdout is not None
                for line in self.current_proc.stdout:
                    m = PROGRESS_RE.fullmatch(line.rstrip("\n"))
                    self.log_queue.put(((int(m[1]), f"{title}: {m[2]}"), "progress") if m else ("  " + line, "ink"))
                self.current_proc.wait()
                last_rc = self.current_proc.returncode
            except Exception as exc:
                self.log_queue.put((f"- [ERR] {exc}\n", "muted"))
                last_rc = 1
            finally:
                self.current_proc = None

            def finish() -> None:
                self._set_running_state(False)
                if last_rc == 0:
                    self.status_badge.configure(text="완료 (exit 0)", fg=INK_2, bg=PAPER_2)
                    self._append_log("+ [OK] exit code 0\n")
                    self._set_gauge(100, f"{title}: 완료")
                else:
                    self.status_badge.configure(text=f"중단됨 (exit {last_rc})", fg=INK, bg=PAPER_3)
                    self._append_log(f"- [FAIL] exit code {last_rc}\n")
                    self._set_gauge(self.gauge_pct, f"{title}: 중단됨 (exit {last_rc})")
                if slug:  # the picked car's, not the job's: another car may be picked by now (and its 차 이름 field)
                    self.load_vehicle_preview(self._picked_slug())
                self._fill_vehicle_table()  # refresh build / deploy status
                # why the run stopped short, when the user can fix it (footage or photos short, a rule broken):
                # gdrive_pipeline.report() writes it during this run
                rep = OUTPUT_ROOT / (slug or "") / "report.txt"
                if slug and rep.exists() and rep.stat().st_mtime >= started - 1:
                    messagebox.showwarning("opticglass-gui", rep.read_text(encoding="utf-8")[:400])
                if last_rc == 0 and then:
                    then()

            self.log_queue.put((finish, "call"))  # after the last queued line, on the UI thread

        threading.Thread(target=worker, daemon=True).start()

    def stop_current_task(self) -> None:
        if not self.is_running:
            return
        if self.current_proc and self.current_proc.poll() is None:
            # the whole tree: agy.exe, ffmpeg and the builders run under the python child and would keep going
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.current_proc.pid)], capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)

    def run_step1_setup(self) -> None:
        self._run_commands_async("setup.bat", ["cmd", "/c", str(REPO_ROOT / "setup.bat"), "/nopause"])

    def _save_car_title(self) -> None:
        slug, text = self.title_slug, self.car_title.get().strip()
        if not slug or not text or text == drive_index.title(slug):
            return
        try:
            drive_index.set_title(slug, text)
            self._append_log(f"[차 이름] {slug}: {text} (다음 썸네일부터 적용)\n")
        except ValueError as exc:
            messagebox.showerror("opticglass-gui", str(exc))

    def _open_thumb_picker(self) -> None:
        slug = self.preview_slug
        if not slug:
            messagebox.showinfo("opticglass-gui", "먼저 Drive 차종 폴더를 고르고 '썸네일'을 한 번 실행하세요.")
            return
        if self.thumb_picker and self.thumb_picker.winfo_exists():
            if self.thumb_picker.slug != slug:
                messagebox.showinfo("opticglass-gui", f"{self.thumb_picker.slug}의 썸네일 사진 창이 열려 있습니다. 저장하거나 닫은 뒤 다시 누르세요.")
            self.thumb_picker.lift()
            return
        try:
            self.thumb_picker = ThumbPicker(self, slug)
        except Exception as exc:  # opencv missing, unreadable picks file, ...
            messagebox.showerror("opticglass-gui", f"썸네일 사진 창을 열 수 없습니다: {exc}")

    def load_vehicle_preview(self, slug: str | None) -> None:
        """The car's thumbnails from its last successful run, newest first and at most 2 side by side (the plain one
        and the AI-background one when that run made it)."""
        self.preview_slug = slug  # the car is picked in the Drive browser, not here
        if slug != self.title_slug:  # not while the person is typing in it
            self._save_car_title()  # an unsaved edit belongs to the car being left
            self.title_slug = slug
            self.car_title.set(drive_index.title(slug) if slug else "")

        car_out_dir = OUTPUT_ROOT / slug if slug else None
        # the plain and the AI-background thumbnail (--ai-bg makes the second, and deletes an older one)
        made = [p for p in (car_out_dir / f"{n}_1280x720_split_horizontal.jpg" for n in ("thumbnail", "thumbnail_ai"))
                if p.exists()] if slug and drive_index.status(slug)["thumb"] == "done" else []  # older files are not this run's
        self.preview_paths = sorted(made, key=lambda p: p.stat().st_mtime, reverse=True)[:2]
        self.preview_slots: list = []  # (left x, right x) of each shown image, for the double-click
        if not self.preview_paths:
            self.preview_canvas.configure(image="", text=f"# [{slug}] 아직 썸네일이 없습니다: 왼쪽 '썸네일' 버튼 (AI가 사진을 고르고 마스킹)"
                                          if slug else NO_CAR_PREVIEW)
            self.preview_path_label.configure(text="")
            return

        folder = car_out_dir.relative_to(REPO_ROOT) if car_out_dir.is_relative_to(REPO_ROOT) else car_out_dir
        rels = [p.name for p in self.preview_paths]
        self.preview_path_label.configure(text=f"{str(folder).replace(chr(92), '/')}/  " + "  |  ".join(rels))
        if not HAS_PIL:
            self.preview_canvas.configure(text="\n".join(rels))
            return

        try:
            gap, n = 12, len(self.preview_paths)
            cw = max(self.preview_canvas.winfo_width() - 16, 520)
            ch = max(self.preview_canvas.winfo_height() - 16, 160)
            imgs = []
            for p in self.preview_paths:
                im = Image.open(p).convert("RGB")
                im.thumbnail(((cw - gap * (n - 1)) // n, ch), Image.Resampling.LANCZOS)
                imgs.append(im)
            sheet = Image.new("RGB", (sum(im.width for im in imgs) + gap * (n - 1), max(im.height for im in imgs)), PAPER)
            x = 0
            for im in imgs:
                sheet.paste(im, (x, (sheet.height - im.height) // 2))
                self.preview_slots.append((x, x + im.width))
                x += im.width + gap
            self.preview_photo = ImageTk.PhotoImage(sheet)
            self.preview_canvas.configure(image=self.preview_photo, text="")
        except Exception as exc:
            self.preview_canvas.configure(image="", text=f"# error: {exc}")

    def _open_current_preview_image(self, event=None) -> None:
        """Double-click: the full-size file of the thumbnail under the pointer (the label centres the sheet)."""
        if not self.preview_paths:
            return
        idx = 0
        if event is not None and self.preview_slots:
            x = event.x - (self.preview_canvas.winfo_width() - self.preview_slots[-1][1]) // 2
            idx = next((i for i, (a, b) in enumerate(self.preview_slots) if x < b + 6), len(self.preview_slots) - 1)
        if self.preview_paths[idx].exists():
            os.startfile(str(self.preview_paths[idx]))



class ThumbPicker(tk.Toplevel):
    """Picks a car's exterior / before / after photo from its own Drive download and covers plates and faces.
    Plates: click the plate's four corners. Faces: drag from a face's centre outwards for a black circle.
    Right-click removes the mask under the cursor. Saving writes the masked copies; agy then checks them for any plate
    or face left before the thumbnails are made. AI 자동 분류 has agy pick and mask the three photos again."""

    def __init__(self, app: OpticGlassTerminalApp, slug: str) -> None:
        import thumb_photos  # opencv: loaded only when the picker opens
        self.tp = thumb_photos
        super().__init__(app)
        self.app, self.slug = app, slug
        self.title(f"썸네일 사진: {slug} ({drive_index.title(slug)})")
        self.geometry("1180x760")
        self.configure(bg=PAPER)
        self.cands = thumb_photos.candidates(slug, frames=True)  # agy may pick a still from a clip
        self.picks: dict = thumb_photos.load_picks(slug)
        # a re-download may drop a file; an agy pick of a kind its slot no longer takes is unpicked (thumb_photos.saved)
        self.picks = {s: p for s, p in self.picks.items() if p["src"] in self.cands
                      and (p.get("by") != "agy" or p.get("kind") in (None, *thumb_photos.AI_KINDS[s]))}
        self.seen = set(self.picks)  # saved picks were checked when they were saved
        self.slot = "car_exterior"
        self.images: dict = {}
        self.disp_key = None
        self.clicks: list = []  # plate corners clicked so far, image pixels
        self.drag_from = None
        self.mode = tk.StringVar(value="plate")
        if not self.picks:  # first visit: use agy's review.json if available, else Stage 1's manifest guess
            rev_f = drive_index.media_dir(slug) / "thumb" / "review.json"
            if rev_f.exists():
                try:
                    cache = json.loads(rev_f.read_text(encoding="utf-8"))
                    rev = {}
                    for k, v in cache.items():
                        parts = k.split("|")
                        if len(parts) >= 2 and parts[1] in self.cands and (parts[0] == thumb_photos.REVIEW_VERSION or parts[1] not in rev):
                            rev[parts[1]] = v
                    used = set()
                    for s in thumb_photos.SLOTS:
                        name = next(iter(thumb_photos._ranked(rev, s, used)), None)
                        if name:
                            im = self._image(name)
                            plates, faces = thumb_photos.to_pixels(rev[name], *im.size)
                            self.picks[s] = {"src": name, "plates": plates, "faces": faces}
                            used.add(name)
                except Exception:
                    pass
            manifest = OUTPUT_ROOT / slug / "package_manifest.json"
            guess = json.loads(manifest.read_text(encoding="utf-8")).get("slots", {}) if manifest.exists() else {}
            for s in thumb_photos.SLOTS:
                if s in self.picks:
                    continue
                name = pathlib.Path(guess.get(s) or "").name
                if name in self.cands:
                    try:
                        self._assign(s, name)
                    except Exception:  # unreadable or half-downloaded guess: the person picks this slot instead
                        pass
        self._build()
        self.bind("<Escape>", lambda e: self.destroy())

    def _build(self) -> None:
        top = tk.Frame(self, bg=PAPER, padx=12, pady=8)
        top.pack(fill="x")
        for value, text in (("plate", "번호판: 네 꼭짓점 클릭"), ("face", "얼굴: 드래그로 원")):
            tk.Radiobutton(top, text=text, value=value, variable=self.mode, command=self._cancel_clicks, bg=PAPER, fg=INK,
                           selectcolor=ACCENT_WASH, activebackground=PAPER, font=(FONT_UI, 9)).pack(side="left", padx=(0, 10))
        tk.Label(top, text="오른쪽 클릭: 마스크 지우기", bg=PAPER, fg=MUTED, font=(FONT_UI, 8)).pack(side="left", padx=10)
        chk = self.tp.check_file(self.slug)
        left = json.loads(chk.read_text(encoding="utf-8")).get("problems") if chk.exists() else None
        if left:  # what the AI still saw on the saved copies
            tk.Label(top, text="AI 검수: " + " · ".join(left), bg=PAPER, fg=INK, font=(FONT_UI, 9, "bold"), anchor="w",
                     wraplength=760, justify="left").pack(side="left", padx=10)

        body = tk.Frame(self, bg=PAPER, padx=12)
        body.pack(fill="both", expand=True)
        left = tk.Frame(body, bg=PAPER_2, width=280, padx=10, pady=10, highlightthickness=1, highlightbackground=RULE)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self.slot_btns = {}
        for s, label in self.tp.SLOTS.items():
            b = tk.Button(left, anchor="w", command=lambda v=s: self._select_slot(v), **self.app._small_btn_style())
            b.pack(fill="x", pady=(0, 4))
            self.slot_btns[s] = b
        tk.Label(left, text=f"이 차 사진 ({self.tp.raw_dir(self.slug).relative_to(REPO_ROOT)})", bg=PAPER_2, fg=MUTED, font=(FONT_UI, 8),
                 anchor="w").pack(fill="x", pady=(8, 2))
        lf = tk.Frame(left, bg=PAPER_2)
        lf.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(lf, bg=PAPER, fg=INK_2, selectbackground=ACCENT_WASH, selectforeground=ACCENT,
                                  font=(FONT_UI, 8), relief="flat", highlightthickness=1, highlightbackground=RULE_2,
                                  exportselection=False)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for name in self.cands:
            self.listbox.insert("end", name)
        self.listbox.bind("<<ListboxSelect>>", self._on_list)

        self.canvas = tk.Canvas(body, bg=PAPER_3, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.canvas.bind("<Configure>", lambda e: self._show())
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._remove_at)

        bottom = tk.Frame(self, bg=PAPER, padx=12, pady=10)
        bottom.pack(fill="x")
        self.info = tk.Label(bottom, text="", bg=PAPER, fg=INK_2, font=(FONT_UI, 9), anchor="w")
        self.info.pack(side="left", fill="x", expand=True)
        tk.Button(bottom, text="저장 후 썸네일 만들기", command=self._save, bg=ACCENT, fg=ACCENT_INK, activebackground=ACCENT_EDGE,
                  activeforeground=ACCENT_INK, relief="flat", font=(FONT_UI, 9, "bold"), padx=12, pady=4,
                  cursor="hand2").pack(side="right")
        tk.Button(bottom, text="닫기", command=self.destroy, **self.app._small_btn_style()).pack(side="right", padx=(0, 6))
        tk.Button(bottom, text="AI 자동 분류", command=self._auto, **self.app._small_btn_style()).pack(side="right", padx=(0, 6))
        self._select_slot(self.slot)

    # --- picks -----------------------------------------------------------------------------------------------------
    def _image(self, name: str):
        if name not in self.images:
            self.images[name] = self.tp.open_rgb(self.tp.raw_dir(self.slug) / name)
        return self.images[name]

    def _assign(self, slot: str, name: str) -> None:
        self._image(name)  # fails here, not later, on an unreadable or half-downloaded file
        self.picks[slot] = {"src": name, "plates": [], "faces": []}

    def _select_slot(self, slot: str) -> None:
        self.slot = slot
        self.clicks = []
        self.listbox.selection_clear(0, "end")
        p = self.picks.get(slot)
        if p:
            i = self.cands.index(p["src"])
            self.listbox.selection_set(i)
            self.listbox.see(i)
        self._show()

    def _on_list(self, _e=None) -> None:
        sel = self.listbox.curselection()
        if not sel or (self.picks.get(self.slot) or {}).get("src") == self.cands[sel[0]]:
            return
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            self._assign(self.slot, self.cands[sel[0]])
        except Exception as exc:  # unreadable or half-downloaded image
            messagebox.showerror("썸네일 사진", f"{self.cands[sel[0]]}을(를) 열 수 없습니다: {exc}", parent=self)
        finally:
            self.config(cursor="")
        self._cancel_clicks()
        self._show()

    def _cancel_clicks(self) -> None:
        self.clicks = []
        if hasattr(self, "canvas"):
            self._show()

    # --- canvas ----------------------------------------------------------------------------------------------------
    def _to_img(self, x: float, y: float) -> list:
        img = self._image(self.picks[self.slot]["src"])
        return [min(max((x - self.ox) / self.scale, 0), img.width - 1), min(max((y - self.oy) / self.scale, 0), img.height - 1)]

    def _to_cv(self, x: float, y: float) -> tuple:
        return self.ox + x * self.scale, self.oy + y * self.scale

    def _show(self) -> None:
        c = self.canvas
        c.delete("all")
        for s, b in self.slot_btns.items():
            p = self.picks.get(s)
            mark = "[v]" if s in self.seen and p else "[ ]"
            b.configure(text=f"{mark} {self.tp.SLOTS[s]}: {p['src'] if p else '고르지 않음'}",
                        fg=ACCENT if s == self.slot else INK_2, highlightbackground=ACCENT if s == self.slot else RULE_2)
        p = self.picks.get(self.slot)
        cw, ch = max(c.winfo_width(), 100), max(c.winfo_height(), 100)
        if not p:
            msg = f"왼쪽 목록에서 {self.tp.SLOTS[self.slot]} 사진을 고르세요" if self.cands else \
                f"{self.tp.raw_dir(self.slug).relative_to(REPO_ROOT)}에 사진이 없습니다. 먼저 이 차를 실행해 Drive 사진을 내려받으세요."
            c.create_text(cw / 2, ch / 2, text=msg, fill=MUTED, font=(FONT_UI, 10))
            self.info.configure(text="")
            return
        img = self._image(p["src"])
        self.scale = min(cw / img.width, ch / img.height)
        self.ox, self.oy = (cw - img.width * self.scale) / 2, (ch - img.height * self.scale) / 2
        key = (p["src"], cw, ch)
        if key != self.disp_key:
            self.photo = ImageTk.PhotoImage(img.resize((max(1, round(img.width * self.scale)), max(1, round(img.height * self.scale)))))
            self.disp_key = key
        c.create_image(self.ox, self.oy, image=self.photo, anchor="nw")
        for quad in p["plates"]:
            pts = [v for x, y in self.tp.order_quad(quad).tolist() for v in self._to_cv(x, y)]
            c.create_polygon(pts, fill=PAPER, stipple="gray50", outline=ACCENT, width=2)
        for cx, cy, r in p["faces"]:
            x, y = self._to_cv(cx, cy)
            rr = r * self.scale
            c.create_oval(x - rr, y - rr, x + rr, y + rr, fill="black", outline=ACCENT, width=2)
        for x, y in self.clicks:
            x, y = self._to_cv(x, y)
            c.create_oval(x - 4, y - 4, x + 4, y + 4, fill=ACCENT, outline=PAPER)
        self.seen.add(self.slot)
        self.info.configure(text=f"{self.tp.SLOTS[self.slot]}: 번호판 {len(p['plates'])} · 얼굴 {len(p['faces'])}"
                                 + (f" · 꼭짓점 {len(self.clicks)}/4" if self.clicks else ""))

    def _press(self, e) -> None:
        if not self.picks.get(self.slot):
            return
        if self.mode.get() == "plate":
            self.clicks.append(self._to_img(e.x, e.y))
            if len(self.clicks) == 4:
                self.picks[self.slot]["plates"].append(self.clicks)
                self.clicks = []
            self._show()
        else:
            self.drag_from = (e.x, e.y)

    def _motion(self, e) -> None:
        if self.drag_from:
            x0, y0 = self.drag_from
            r = ((e.x - x0) ** 2 + (e.y - y0) ** 2) ** 0.5
            self.canvas.delete("drag")
            self.canvas.create_oval(x0 - r, y0 - r, x0 + r, y0 + r, outline=ACCENT, width=2, tags="drag")

    def _release(self, e) -> None:
        if not self.drag_from:
            return
        x0, y0 = self.drag_from
        self.drag_from = None
        r = ((e.x - x0) ** 2 + (e.y - y0) ** 2) ** 0.5 / self.scale
        if r >= 4:
            cx, cy = self._to_img(x0, y0)
            self.picks[self.slot]["faces"].append([round(cx), round(cy), round(r)])
        self._show()

    def _remove_at(self, e) -> None:
        p = self.picks.get(self.slot)
        if not p:
            return
        if self.clicks:  # a half-clicked plate goes first
            self._cancel_clicks()
            return
        x, y = self._to_img(e.x, e.y)
        for f in p["faces"]:
            if (x - f[0]) ** 2 + (y - f[1]) ** 2 <= f[2] ** 2:
                p["faces"].remove(f)
                break
        else:
            import cv2
            for q in p["plates"]:
                if cv2.pointPolygonTest(self.tp.order_quad(q), (x, y), False) >= 0:
                    p["plates"].remove(q)
                    break
        self._show()

    # --- save ------------------------------------------------------------------------------------------------------
    def _save(self) -> None:
        unseen = [label for s, label in self.tp.SLOTS.items() if s not in self.picks or s not in self.seen]
        if unseen:
            messagebox.showinfo("썸네일 사진", f"아직 고르거나 확인하지 않은 사진: {', '.join(unseen)}", parent=self)
            return
        if self.clicks:
            messagebox.showinfo("썸네일 사진", "번호판 꼭짓점을 4개 다 찍거나 오른쪽 클릭으로 취소하세요.", parent=self)
            return
        if self.app.is_running:  # a running job (e.g. AI 배경) may be reading these copies; the window keeps the picks
            messagebox.showinfo("썸네일 사진", "실행 중인 작업이 끝난 뒤 다시 저장하세요.", parent=self)
            return
        try:
            self.tp.save(self.slug, self.picks)
        except Exception as exc:
            messagebox.showerror("썸네일 사진", f"저장 실패: {exc}", parent=self)
            return
        self.destroy()
        self.app._append_log(f"[썸네일 사진] {self.slug}: 가린 사진 3장 저장 ({self.tp.masked_file(self.slug, '_').parent.relative_to(REPO_ROOT)}), 바로 썸네일을 생성합니다 (검수 생략)\n")
        self.app.run_thumb_job(self.slug, self._thumb_cmd())

    def _auto(self) -> None:
        """agy picks the three photos again from all of this car's photos and masks them (replacing the picks)."""
        if self.app.is_running:
            messagebox.showinfo("썸네일 사진", "실행 중인 작업이 끝난 뒤 다시 누르세요.", parent=self)
            return
        self.destroy()
        self.app.run_thumb_job(self.slug, self._thumb_cmd("--auto-photos"))

    def _thumb_cmd(self, *extra: str) -> list:
        return self.app._pipeline_cmd(self.slug, "--skip-video-rebuild", *extra)


if __name__ == "__main__":
    app = OpticGlassTerminalApp()
    app.mainloop()
