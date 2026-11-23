---
name: opticglass-pipeline
description: 옵틱글래스(OpticGlass) 와이드 미러 4단계 유튜브 자동화 스킬 (Google Drive 차량 폴더 수집 -> 16:9 롱폼 / 9:16 숏폼 CapCut 초안 생성 -> 썸네일 사진 고르기 및 1280x720 썸네일 제작; 차량 생성 시 사후 검수 생략 · 10분 이내 완성)
---

# OpticGlass 4-Stage YouTube Automation Pipeline

옵틱글래스(OpticGlass) 와이드 미러 장착 영상 및 유튜브 썸네일을 제작할 때 이 스킬을 따릅니다.
**차량 인덱스 영상/썸네일 생성 과정에서는 검수에 소요되는 시간을 없애기 위해 사후 검수를 전면 생략하며, `/teamwork` 실행을 포함해 반드시 10분 이내에 완성해야 합니다.**

## 1. 4단계 워크플로우 개요

1. **Stage 1: Google Drive 차량 미디어 자동 수집 (`gdrive_pipeline.py`)**
   - 루트 폴더: `0.옵틱 광각` (`1TT2v1sLCQdBIISjDucJPJGcineVIB76B`), 잔여 차량 폴더: `1. 잔여 차량` (`10p1isRRpD4uv447Q8qtVD9sPUQBbc6az`)
   - 로컬 다운로드 경로: Drive 경로 그대로 `구글드라이브다운파일/media/<Drive 루트>/<차종 폴더명>/gdrive_raw/` (`drive_index.media_dir(slug)`; 기존 차는 `media/<slug>/gdrive_raw/`)
   - `preflight_check.py`의 `validate_media_paths(..., allowed_vehicle_dir=...)`로 Stage 1 수집·일반 씬·Stage 3 썸네일의 단일 차종 폴더 격리를 강제하여 타 차종 혼입을 차단합니다(전/후 비교 구간 `compare_before`·`compare_after`·`split`에서 대상 차량 인덱스에 적절한 레퍼런스가 없을 때만 허용되는 타 차종 전/후 비교 사진 폴백은 예외).
2. **Stage 2: 템플릿 기반 영상 편집 (`build_longform.py <slug>` + `scenarios/<slug>_longform.json` / `longform_common.py` / `build_shorts.py`)**
   - 추출된 템플릿(`video-automation/work/scenarios/templates/{polestar4_optic,bmw_aceman_optic,porsche997_optic,opticglass_wide1}`)과 차종별 시나리오(`video-automation/work/scenarios/<slug>_longform.json`)를 `build_longform.py <slug>`가 결합해 CapCut 초안(`hermes_<slug>_optic_longform`)을 생성합니다. 차종별 .py는 없습니다.
   - `make_scenario.py`는 1차 미디어 분류(`_review`)에서 얻은 번호판·얼굴·미러 좌표를 렌더링 씬 좌표로 즉시 변환 적용하여 **2차 프레임 AI 검수(`MASK_ASK`)를 생략**하며, 빌드 후 `check_text_outputs.py` 사후 검수 없이 즉시 스테이징·배포합니다.
   - `portable_paths.py`를 통해 다른 PC에서도 `video-automation/assets/` 내 폰트·로고·마스크·아웃트로·BGM·조견표로 자동 매핑됩니다.
3. **Stage 3: 썸네일 사진 고르기 (`thumb_photos.py`) 및 `1280x720` 썸네일 합성 (`generate_thumbnail.py`)**
   - agy가 그 차 사진(미러 사진이 없으면 그 차 영상에서 뽑은 장면 `gdrive_raw/_frames/`)을 외관·시공 전·시공 후로 분류하고, 번호판·얼굴을 가린 뒤 **별도 AI 재검수(`_verify`, `FIX_ROUNDS`)를 생략하고 즉시 썸네일 생성에 씁니다 (`save` 즉시 `ready`).** 부족하면 썸네일을 만들지 않습니다.
   - `옵틱글래스_유튜브_썸네일/template/generate_thumbnail.py`가 무블러, 하단 자막 바 없는 `1280x720` 썸네일 2장(`split_horizontal`, `split_vertical`)을 만듭니다. 레이아웃은 규칙 파일 3장.
4. **Stage 4: CapCut 초안·MP4 생성 완료 (차량 생성 시 사후 검수 생략)**
   - 차량 인덱스 영상/썸네일 생성 시에는 `check_text_outputs.py` 사후 검수 및 `/teamwork` 다단계 검수·감사 게이트를 생략하고, CapCut 초안 및 자막 합성 `.mp4` 생성 즉시 완료 처리합니다(`/teamwork` 포함 10분 이내 완성). `check_templates.py` / `check_text_outputs.py`는 템플릿·빌더 코드 수정 시에만 단독 실행합니다.

## 2. 새 차종 추가 절차 (New Vehicle Onboarding)

1. Google Drive에서 새 차종 폴더 확인:
   ```powershell
   py video-automation/work/gdrive_pipeline.py --list-drive
   ```
2. `video-automation/work/scenarios/<new_slug>_longform.json`: GUI 롱폼(또는 `py make_scenario.py <new_slug>`)이 「옵틱글래스 광각미러 템플릿 1」(57.733초, `opticglass_wide1`)로 자동 생성합니다.
   - **CapCut 기준 프로젝트 준수 규칙**: 광각미러 템플릿(Google Drive 차량 `img/vid` data, `DATA_DIR` = `C:\Users\bssho\OneDrive\바탕 화면\구글드라이브다운파일`)은 지정된 두 CapCut 기준 프로젝트(`C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\42. 09 포르쉐 997.2 옵틱 [26.03.23]` -> `C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\.cloud_cache_7327546324319568897\옵틱글래스 광각미러 템플릿 1 (1)`)에서 도출된 `opticglass_wide1` 기준(`1920x1080`, `30fps`, `57.733s`, 13씬 `w00`~`w12`, `transitions: false`, 크롭 50:50 분할, 21개 텍스트 슬롯 및 `#F4C70F` 강조색, `Track[4]` 배지 지시 스티커, 전 구간 BGM·음소거, 하우스 스타일 오버라이드)을 따라야 합니다. 클라우드 `.locked` 파일은 복호화하지 않고 평문 `template.json.bak` / 로컬 `옵틱글래스 광각미러 템플릿 1`을 사용합니다.
   - **적용 범위 (R3)**: 앞으로 생성·빌드하는 광각미러 템플릿(`opticglass_wide1`) 기반 작업부터 적용하며, 기존 수동 작성 80초 시나리오(`cybertruck`, `santafe`, `bmwx5`, `sealion7`, `honda_cbr650r_106`)는 변경하지 않고 유지합니다.
   - 손으로 쓸 때 (코드 작성 없음, `build_longform.py <new_slug>`로 빌드):
   - `template`: `"opticglass_wide1"`(w00~w12 13씬, 57.733초), `"polestar4_optic"`, `"bmw_aceman_optic"`, `"porsche997_optic"` 중 선택
   - `scenes`: 실제 촬영 `.MOV` 클립 배정(`s00`~`s17` 기본, 80~100초 가이드라인 컷은 `s08b`처럼 씬을 추가하고 모든 씬에 `start`/`dur` 기재, 마지막은 `src: "outro"`)
   - `lines`: 화면 자막 (템플릿 text slot 기본값 사용 가능)
   - 번호판이 노출되는 씬은 `"plates": [[frac, [[x,y]x4]], ...]` (`로고_번호판.png` 원근 호모그래피 추적 마스킹; 분할 `split` 및 화살표 씬에서도 노출 시 동일 적용)
   - 얼굴이 노출되는 씬은 `"faces": [[[frac, cx, cy, r], ...], ...]` (`face_mask_circle.png` 원형 추적 마스킹, r=0이면 숨김)
   - 시공 후 미러 씬은 `"arrows": [[x, y, ux, uy, len] x4]`
   - 상단 `car` 블록: `logo`(CarLogos/assets/logos 파일명, 없으면 차종명으로 자동), `logo_size`, `logo_scale`, `compat_cards`(조견표 glob)
   - 비교 씬(역할 `compare_before`·`compare_after`·`split`)에서는 사이드미러 베젤 전체가 100% 보이도록 스케일/포지션 조정 및 전·중·후 화면 전환 비활성화
   - **전/후 비교 구간 타 차종 사진 폴백**: `opticglass_wide1` 포함 모든 템플릿의 비교 씬(`compare_before`·`compare_after`·`split`)은 대상 차량 인덱스에 적절한 `mirror_before`/`mirror_after` 레퍼런스가 있으면 정상 대상 차량 선택(영상 우선 → 같은 차 사진)을 그대로 유지하며, 대상 차량 인덱스에 적절한 레퍼런스가 없을 때만 다른 차량 인덱스의 적절한 전/후 비교 사진(`mirror_before`/`mirror_after`)에서 브랜드·모델·연식 등 추가 공여 차량 제약 없이 자동 폴백합니다.
3. 통합 파이프라인 실행 (검수 생략 · `/teamwork` 포함 10분 이내 완성):
   ```powershell
   py video-automation/work/gdrive_pipeline.py --vehicle <new_slug>
   ```
