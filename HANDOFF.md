# LLM 작업 인계 문서 (`HANDOFF.md`, 2026-11-23 기준)

이 문서는 다음 LLM 세션이 저장소를 처음부터 다시 탐색하지 않고 즉시 작업을 이어갈 수 있도록 핵심 아키텍처, 최근 변경 사항(2026-11-20 ~ 2026-11-23), GUI 버튼 매핑, 파이프라인 수정 내역, 검증 명령을 정리한 단일 인계 파일입니다.

---

## 1. 작업 환경 및 필독 순서 (Quick Start for LLM)

* **실제 작업 저장소**: `C:\Users\bssho\Downloads\paperclip-master` (브랜치 `video-pipeline-drive-table-1028`, HEAD `6bce422`)
* **주의 (Orca 워크스페이스 경로)**: `C:\Users\bssho\orca\workspaces\paperclip-master\영상자동화`에는 `.git` 포인터 파일만 있습니다. 실제 소스 코드·규칙·스킬·데이터는 모두 `C:\Users\bssho\Downloads\paperclip-master`에 있습니다.
* **데이터 루트 (`DATA_DIR`)**: `C:\Users\bssho\Downloads\paperclip-master\구글드라이브다운파일` (정션 → `C:\Users\bssho\OneDrive\바탕 화면\구글드라이브다운파일`), [portable_paths.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/portable_paths.py)로 해석됩니다.
* **새 세션 읽기 순서**:
  1. [HANDOFF.md](file:///C:/Users/bssho/Downloads/paperclip-master/HANDOFF.md) (이 문서)
  2. [AGENTS.md](file:///C:/Users/bssho/Downloads/paperclip-master/AGENTS.md) / [GEMINI.md](file:///C:/Users/bssho/Downloads/paperclip-master/GEMINI.md)
  3. [opticglass-workflow-rules.md](file:///C:/Users/bssho/Downloads/paperclip-master/.agents/rules/opticglass-workflow-rules.md)
  4. [SKILL.md](file:///C:/Users/bssho/Downloads/paperclip-master/.agents/skills/opticglass-pipeline/SKILL.md)
* **절대 수정 금지 파일**:
  * [HERMES.md](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/HERMES.md)
  * `video-automation/research/` (특히 `facts.md`)
  * 손으로 제작한 80초 시나리오 5종: `cybertruck_longform.json`, `santafe_longform.json`, `bmwx5_longform.json`, `sealion7_longform.json`, `honda_cbr650r_106_longform.json` (참고: `cybertruck_longform.json`은 2026-11-18부터 로컬 워킹트리에 기존 수정본이 존재함)

---

## 2. 최근 완료된 작업 요약 (2026-11-20 ~ 2026-11-23)

### A. 10분 이내 완성을 위한 검수 단계 생략 (규칙 + 코드 반영 완료)
`./teamwork` 포함 차량 인덱스 영상/썸네일 생성을 **10분 이내**로 단축하기 위해, 마스킹·빌드 후 AI/텍스트 사후 검수를 전면 생략하고 1차 시각 분류 결과를 즉시 반영하도록 규칙 문서와 파이프라인 코드를 일괄 수정했습니다.

* **문서 업데이트**: [opticglass-workflow-rules.md](file:///C:/Users/bssho/Downloads/paperclip-master/.agents/rules/opticglass-workflow-rules.md), [AGENTS.md](file:///C:/Users/bssho/Downloads/paperclip-master/AGENTS.md), [GEMINI.md](file:///C:/Users/bssho/Downloads/paperclip-master/GEMINI.md), [SKILL.md](file:///C:/Users/bssho/Downloads/paperclip-master/.agents/skills/opticglass-pipeline/SKILL.md), [DISTRIBUTION.md](file:///C:/Users/bssho/Downloads/paperclip-master/DISTRIBUTION.md)
* **코드 변경 내역**:
  * [thumb_photos.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/thumb_photos.py):
    * `FRAMES_PER_VIDEO = 8`.
    * `save()`가 `thumb/picks.json` 저장 직후 `check_file(slug)`(`thumb/ai_check.json`, `{"ok": true, "problems": [], ...}`)를 즉시 기록하고, `ready()`는 `saved(slug)`를 바로 반환합니다.
    * `_full_review()`는 단독 사진과 캐시된 `thumb/review.json`으로 슬롯을 채울 수 없을 때만 `video_frames()`를 추출·분류합니다.
    * `ai_check()`는 1차 `auto_pick()` + 마스킹 `save()`만 실행하고 사후 `_verify()` / `FIX_ROUNDS` 재검수를 호출하지 않습니다.
  * [make_scenario.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/make_scenario.py):
    * `FRAMES_PER_VIDEO = tp.FRAMES_PER_VIDEO` (8)로 `thumb_photos.py`와 `_frames/` 및 `thumb/review.json`을 공유합니다.
    * `mark()`가 무검수 씬 클립 재절단(`_cut_unmasked`)과 2차 `MASK_ASK` `agy` 호출을 생략하고, `_load_review_cache()`, `_scene_source_samples()`, `_review_items_for_scene()`, `_map_item_to_1080p()`를 통해 1차 `_review` 좌표(`plates`, `faces`, `mirror`)를 렌더링 해상도(`1920x1080`, 좌/우 분할 크롭 포함)로 즉시 사상해 마스킹·화살표 4개(`arrows_for`)를 기입합니다.
    * `generate()`는 `mark()`와 `draft_copy.diversify_scenario()`를 병렬(`ThreadPoolExecutor(max_workers=2)`)로 실행합니다.
  * [build_longform.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/build_longform.py):
    * `check_then_deploy()`가 사후 `check_text_outputs` 검사 없이 `deploy_staged([name])`로 스테이징된 초안을 즉시 배포합니다(CapCut 실행/미검증 버전 시 보류).
  * [gdrive_pipeline.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/gdrive_pipeline.py):
    * `_run_stage2()`에서 `shorts` 외 빌드의 `check_text_outputs.py` 서브프로세스 호출을 생략하고 스테이징 존재 시 `out_check = "pass"`로 처리합니다.
    * `gauge()` 가중치를 `scenario: 15`, `build: 20`, `photos: 10`, `thumbs: 5`, `ai_bg: 20`으로 조정했습니다.

---

### B. `opticglass_gui.exe` 내부 파이프라인 검증 및 버튼 라벨 개편

`opticglass_gui.exe` → `opticglass_gui.py` → `gdrive_pipeline.py` 실행 체인을 추적한 결과, GUI 버튼은 별도 축약 로직 없이 LLM 워크플로우와 동일한 프롬프트(`REVIEW_ASK`, `draft_copy.build_prompt`, `HOOK_ASK`, `make_ai_background`), [llm_config.json](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/llm_config.json) 라우팅, `opticglass_wide1` / `shorts_optic` 템플릿, [render_subtitles.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/render_subtitles.py) 자막 번인, [generate_thumbnail.py](file:///C:/Users/bssho/Downloads/paperclip-master/옵틱글래스_유튜브_썸네일/template/generate_thumbnail.py) 생성기를 그대로 실행함을 검증했습니다.

* **실행 체인**:
  * [opticglass_gui_launcher.cs](file:///C:/Users/bssho/Downloads/paperclip-master/opticglass_gui_launcher.cs) (`opticglass_gui.exe`) → `pyw opticglass_gui.py` (`PYTHONUTF8=1`)
  * [opticglass_gui.py](file:///C:/Users/bssho/Downloads/paperclip-master/opticglass_gui.py#L27-L30)가 `pythonw.exe` 옆의 콘솔 `python.exe`를 `PYTHON`으로 해석하고, `_run_commands_async()`가 `CREATE_NO_WINDOW`, `PYTHONUTF8=1`, `PYTHONUNBUFFERED=1`, `cwd=REPO_ROOT`로 `gdrive_pipeline.py`를 호출합니다.

* **현재 GUI 4개 버튼 라벨 및 실행 매핑 ([opticglass_gui.py](file:///C:/Users/bssho/Downloads/paperclip-master/opticglass_gui.py#L315-L320), [L574-L609](file:///C:/Users/bssho/Downloads/paperclip-master/opticglass_gui.py#L574-L609))**:

| 현재 GUI 버튼 라벨 (구 명칭) | 위젯 / 핸들러 | 실행 커맨드 (`_pipeline_cmd`) | 실제 실행 내용 |
| :--- | :--- | :--- | :--- |
| **`<숏폼>`** (구 `<롱폼>`) | `self.long_btn` → `run_longform()` | `gdrive_pipeline.py --vehicle <slug> [--ai-bg]` | Stage 1(동기화) → Stage 2(`longform` 시나리오 `opticglass_wide1` 57.7s + `.mp4` + `hermes_<slug>_optic_longform`) + Stage 3(썸네일 2종 + 선택 AI 배경) |
| **`<썸네일>`** | `self.thumb_btn` → `run_thumbnail()` | `gdrive_pipeline.py --vehicle <slug> --skip-video-rebuild [--ai-bg]` | Stage 1(동기화) → Stage 3 단독 (`thumb_photos.ai_check` → `generate_thumbnails_from_slots` → `0031`/`0034` 1280x720 + 선택 AI 배경) |
| **`<광각미러 템플릿 롱폼>`** (구 `<광각미러 템플릿>`) | `self.wide_btn` → `run_build("wide1")` | `gdrive_pipeline.py --vehicle <slug> --build wide1` | Stage 1(동기화) → Stage 2 단독 (`<slug>_wide1.json` 57.7s + `.mp4` + `hermes_<slug>_optic_wide1`, 썸네일 생략) |
| **`<릴스/인스타>`** (구 `<숏폼>`) | `self.short_btn` → `run_build("shorts")` | `gdrive_pipeline.py --vehicle <slug> --build shorts` | [build_shorts.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/build_shorts.py) (`shorts_source.mp4` 50.6s 컷 + `HOOK_ASK` 5챕터 훅 + `hermes_<slug>_optic_shorts` + `output/<slug>/shorts/01..05_<slug>_*.mp4`, 썸네일 생략) |

> **LLM 참고**: 사용자 요청에 따라 **표시 라벨과 로그 타이틀(`BUILD_TITLES`, `run_longform`)만** 변경되었으며, 각 버튼이 호출하는 내부 CLI 플래그(`longform` / `--build wide1` / `--build shorts` / `--skip-video-rebuild`) 및 함수명(`run_longform` 등)은 기존 호환을 위해 그대로 유지되었습니다.

---

### C. 파이프라인 내부 엣지케이스 3건 패치 완료

1. **`wide1` 단독 완료 차량의 GUI 상태 표시 및 `agy 영상 수정` 활성화**:
   * [drive_index.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/drive_index.py#L251-L265): `status(slug)`가 `stage2_video_outputs`가 비었거나 `not_built`일 때 `extra_drafts["hermes_<slug>_optic_wide1"]`를 폴백으로 읽고, `"scenario"`를 `longform`/`wide1` 모두 확인하도록 수정.
   * [opticglass_gui.py](file:///C:/Users/bssho/Downloads/paperclip-master/opticglass_gui.py#L611-L614): `_agy_slug()`가 `<slug>_wide1.json`만 있는 차량도 수정 대상으로 인식.
   * [agy_edit.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/agy_edit.py#L49-L57): `prepare()`가 `_longform.json` 부재 시 `_wide1.json` 폴백 로드, `swap_in()`이 `copy.stem` 기반 백업, `main()` 재빌드 시 `_wide1.json`이면 `--build wide1` 전달.
2. **`<릴스/인스타>`(`--build shorts`) 실행 시 기존 `wide1` 산출물 즉시 재사용**:
   * [gdrive_pipeline.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/gdrive_pipeline.py#L687-L690): `args.build == "shorts"`일 때 `<slug>_longform.json`이 없고 `<slug>_wide1.json`이 있으면 `variant = "wide1"`을 선택해 Drive 재동기화와 57.7s 마스터 영상 재렌더링을 방지.
3. **`<썸네일>`(`--skip-video-rebuild`) 실행 시 불필요한 영상 재다운로드 방지 및 기존 상태 유지**:
   * [gdrive_pipeline.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/gdrive_pipeline.py#L696-L700): `--skip-video-rebuild`일 때 `inbox_dir` 내 사진 포함(`(".jpg", ".jpeg", ".png", ".mov", ".mp4")`) 존재 여부를 검사해 영상 삭제 후 사진만 남은 폴더에서 `.MOV` 전체를 재다운로드하지 않도록 수정.
   * [gdrive_pipeline.py](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/gdrive_pipeline.py#L906-L911): `--skip-video-rebuild` 실행 후 매니페스트 저장 시 `output_check`가 `None`이면 기존 `stage2_video_outputs.output_check` 값을 보존.

---

## 3. 꼭 지킬 핵심 불변 규칙 (Invariants Checklist)

* **LLM 모델 설정 ([llm_config.json](file:///C:/Users/bssho/Downloads/paperclip-master/video-automation/work/llm_config.json))**: 모든 LLM 호출은 API 키 없이 `agy` CLI 경유.
  * `photo_check` / `scenario_lines` / `youtube_lines` = `gemini-4-carbon-low`
  * `thumbnail_image` = `gemini-4-argon-high` (orchestrator/carbon-high 금지)
  * `default_model` = `gemini-pro-orchestrator` (`video_edit` 기본값)
* **템플릿 및 시각 규칙**:
  * 자동 생성 롱폼/wide1은 `templates/opticglass_wide1/skeleton.json` (57.733s, 13씬 `w00`~`w12`, `transitions: false`, 21자막 슬롯).
  * compare 구간(`compare_before`, `compare_after`, `split`)만 대상 차에 `mirror_before`/`mirror_after`가 없을 때 타 차량 도너 사진(`@media/...`) 폴백 허용. 그 외 씬과 썸네일(`thumb_photos.auto_pick`)은 단일 차량 미디어만 허용(타 차종·AI 생성물 혼입 금지).
  * 번호판 호모그래피 워핑(`로고_번호판.png`) + 얼굴 원형 마스킹(`face_mask_circle.png`) + `#F26925` 화살표 4개(`w08`, `w09`, `w10`, `w11`).
  * 썸네일 1280x720 (`0031` 상하 분할, `0034` 좌우 분할), 70:30 비율, 블러 금지.
  * CapCut 실행 중 `com.lveditor.draft` 직접 쓰기 금지; `capcut_stage/`에 빌드 후 `preflight_check.py --deploy`로만 배포.

---

## 4. 검증 명령 모음 (Verification Suite)

최종 편집(2026-11-20) 직후 아래 5개 명령을 모두 실행해 `exit code 0` 통과를 확인했습니다. 이후 코드 수정 시 동일 세트로 재검증하세요:

```powershell
py -m py_compile "C:\Users\bssho\Downloads\paperclip-master\opticglass_gui.py"
py "C:\Users\bssho\Downloads\paperclip-master\video-automation\work\drive_index.py"
py "C:\Users\bssho\Downloads\paperclip-master\video-automation\work\gdrive_pipeline.py" --selftest
py "C:\Users\bssho\Downloads\paperclip-master\video-automation\work\agy_edit.py" --selftest
py "C:\Users\bssho\Downloads\paperclip-master\video-automation\work\build_shorts.py"
```

추가 단위/모듈 셀프테스트(검수 생략 패치 직후 `exit code 0` 통과):
```powershell
py "C:\Users\bssho\Downloads\paperclip-master\video-automation\work\thumb_photos.py"
py "C:\Users\bssho\Downloads\paperclip-master\video-automation\work\make_scenario.py"
py "C:\Users\bssho\Downloads\paperclip-master\video-automation\work\test_compare_fallback.py"
py "C:\Users\bssho\Downloads\paperclip-master\video-automation\work\test_concurrency_stress.py"
```

---

## 5. 계정 이관 및 과거 세션 참고 (2026-10-30 보존분)

* **Claude 계정 이관 이력**: 이전 계정 `7130d33e-8ed6-4c46-9ed9-7069b9660668` → 대상 계정 `deda5514-ec72-48b6-b7de-f5dc9a2a6334` (`9918e492…`).
  * 데스크톱 세션 복제: `py -3 archive/sessions/migrate_desktop_sessions.py <계정ID 앞자리> [조직ID 앞자리]`
  * 대화 기록 내보내기: `py -3 archive/sessions/export_claude_sessions.py` (`archive/sessions/claude_code/` 및 `archive/sessions/SESSION_INDEX.md` 참고).
* **`pyCapCut` 서브모듈**: `fix/template-mode-data-loss` 브랜치 커밋 `00e08e6` 유지 중.
* **Google Drive 토큰 (`gdrive_pipeline.py`)**: 저장소 자체 인증을 사용하므로 Claude/LLM 계정과 무관하게 동작합니다.
