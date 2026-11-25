---
trigger: always_on
description: 옵틱글래스(OpticGlass) 영상 편집·썸네일·구글 드라이브 자동화 파이프라인 필수 규칙 및 품질 지침
---

# 옵틱글래스(OpticGlass) 유튜브 자동화 워크플로우 절대 규칙

이 워크스페이스를 다른 컴퓨터에서 열더라도 동일한 퀄리티의 결과물을 보장하기 위해 모든 에이전트가 반드시 준수해야 하는 누적 규칙 및 지침입니다.

## 0. 영상편집 병렬 팀워크 (/teamwork) 협업 의무화

사용자 지침에 따라 **영상편집 작업은 단일 직렬 실행을 금지하며, 반드시 `/teamwork` 멀티에이전트 병렬 아키텍처를 가동하여 하위 작업을 전문 서브에이전트 간 분업으로 병렬 수행**한다:
> "영상편집 시 항상 /teamwork 를 통하여 병렬로 작업하세요.(e.g. 이미지 분류, 전처리, 영상 인식, 편집)"

### 0.1 5대 병렬 서브에이전트 역할 분담
1. **미디어 분류 에이전트 (`media_classifier`)**:
   - Google Drive 다운로드 미디어 수집 및 단일 차종 폴더 격리 검증 (`allowed_vehicle_dir`).
   - 사진(`.jpg`/`.png`) 및 영상(`.mp4`/`.MOV`) 확인. 썸네일용 사진 분류(외관·시공 전·시공 후)는 `thumb_photos.py`에서 agy가 한다.
2. **전처리·프라이버시 에이전트 (`privacy_preprocessor`)**:
   - 번호판 4개 꼭짓점 원근 변환(Homography) 좌표 추적 및 `로고_번호판.png` 합성.
   - 작업자/인물 얼굴 `face_mask_circle.png` 원형 추적 마스킹 및 노출 프레임 0화.
   - EXIF 정방향 보정 및 `.MOV` 대표 프레임(`_frames/`) 추출.
3. **영상 인식·시나리오 에이전트 (`vision_scenario`)**:
   - 촬영 영상별 장면 인식 (`car_exterior`, `car_detail`, `mirror_before`, `mirror_after`, `install_*`).
   - 씬 타이밍 및 역할(`ROLES`) 매핑, 시나리오 생성 (`make_scenario.py`).
   - 옵틱 미러 베젤 경계 4개 오렌지 화살표(`#F26925`) 벡터 좌표 추출.
   - 채널 수집 대사(`datasets/youtube_lines.jsonl`)를 반영한 자막 및 썸네일 카피 다변화.
4. **타임라인 편집·빌드 에이전트 (`video_editor`)**:
   - CapCut 헤드리스 빌드 (`build_longform.py`, `build_shorts.py`): 16:9 롱폼, 57.7초 wide1, 9:16 숏폼 초안 조립.
   - BGM 100% 전 구간 커버(무빈틈 루프) 및 원본 현장음 음소거.
   - 정적 한글 폰트(`NotoSansKR-Bold-Static.ttf`, `Paperlogy-7Bold.ttf` 등) 기반 자막 필수 합성(`opticglass_wide1`·신규 롱폼은 불투명 검정 배경 박스 없이 템플릿·`@optic_glass` 스타일 준수, 기존 수동 80초 5대 시나리오만 검정 박스 유지).
   - 비교 구간 전·중·후 화면 전환(Transition) 완전 배제.
5. **썸네일·패키징 에이전트 (`qa_thumbnail`)**:
   - 1280x720 유튜브 썸네일 생성 (`generate_thumbnail.py`, 레이아웃은 2장: `split_horizontal`, `split_vertical`): 하단 자막 바 없음, 가우시안 블러(GaussianBlur) 전면 금지.
   - 차량 인덱스 영상/썸네일 생성 시 사후 회귀 검수(`check_text_outputs.py`, `check_templates.py`) 및 가린 사진 AI 재검수는 생략한다.
   - 최종 패키지 매니페스트(`package_manifest.json`) 작성.

### 0.2 팀워크 작업 규칙, 검수 생략 및 10분 이내 완성
- **같은 차는 한 번에 한 실행**: `gdrive_pipeline.py`(GUI 버튼 포함)는 한 실행 안에서 이미 병렬로 돈다 (Drive 다운로드 3개, 장면 클립 인코딩, 빌드와 썸네일 동시 진행). 병렬 분업은 **서로 다른 차** 사이로 나눈다. 같은 차의 파이프라인·빌더(`build_longform.py`, `build_shorts.py`, `make_scenario.py`, `thumb_photos.py`)를 두 에이전트가 동시에 돌리지 않는다: 같은 클립 캐시·시나리오·`ai_check.json`·CapCut 초안을 함께 덮어쓴다.
- **차량 인덱스 영상/썸네일 생성 시 검수 전면 생략 및 10분 이내 완성 (필수)**:
  - 차량 인덱스 영상/썸네일 생성 워크플로우에서는 검수에 소요되는 과도한 시간을 없애기 위해 **모든 사후 검수 단계를 전면 생략**한다:
    1. 썸네일 가린 사진 AI 검수·재가림·재검수 루프(`thumb_photos.py`의 `_verify` / `FIX_ROUNDS` 호출) 생략 — `save()` 즉시 `ready()` 통과 처리.
    2. 시나리오 생성 시 씬별 0.5초 간격 비마스킹 컷 추출 및 2차 AI 프레임 검수(`make_scenario.py`의 `mark()` 내 `MASK_ASK` 반복 호출) 생략 — 1차 미디어 분류(`_review`)에서 얻은 번호판·얼굴·미러 좌표를 렌더링 씬 좌표계로 즉시 변환 적용.
    3. 빌드 후 `check_text_outputs.py` 사후 검수(서브프로세스 및 `check_then_deploy` 내부 검사) 생략 — CapCut 초안 및 자막 합성 `.mp4` 생성 즉시 완료·배포.
    4. `/teamwork`로 차량 영상/썸네일 생성을 실행할 때도 Reviewer·Challenger·Auditor·Victory Auditor 등 다단계 검수/감사 게이트 및 프레임 추출 시각 검수를 생략하고 워커가 생성 산출물을 만든 즉시 완료 보고한다.
  - 영상/썸네일 생성은 **`/teamwork`로 실행하더라도 반드시 10분 이내에 완성**되어야 한다.
- **메타데이터 격리 규칙**: 각 에이전트는 `.agents/teamwork/<agent_name>/` 내부만 수정(계획, 진행상황, 인계 보고서 등 메타데이터 보관)하며, 소스 코드나 미디어 산출물은 프로젝트 정규 디렉터리(`video-automation/`, `구글드라이브다운파일/`)에 배치한다.
- **인계 프로토콜**: 에이전트 간 전달은 5-Component Handoff Protocol(`handoff.md`)을 준수하여 자기완결적(Self-contained)으로 인계한다.

---

## 1. 전체 4단계 파이프라인 구조 (`work/gdrive_pipeline.py`)
1. **Stage 1 — 미디어 자동 수집 (Google Photos → Google Drive → Local)**:
   - 촬영된 차량 사진/영상이 구글 포토 백업 후 Google Drive `0.옵틱 광각` (`1TT2v1sLCQdBIISjDucJPJGcineVIB76B`, 잔여 차량은 `1. 잔여 차량` `10p1isRRpD4uv447Q8qtVD9sPUQBbc6az`) 하위의 차종별 폴더에 업로드되면 `gdrive` CLI로 Drive 경로와 같은 `구글드라이브다운파일/media/<Drive 루트>/<차종 폴더명>/gdrive_raw/`에 다운로드한다 (GUI가 폴더명으로 영문 id를 자동으로 만든다: `drive_index.auto_slug`, `media_dir`. 기존 12대는 `media/<slug>/` 유지).
   - **단일 차량 폴더 격리 (`allowed_vehicle_dir`)**: Stage 1 미디어 수집·일반 씬·Stage 3 썸네일은 대상 차량 외 다른 차량의 사진·영상이 섞이지 않도록 `preflight_check.py`의 `validate_media_paths(..., allowed_vehicle_dir=...)` 검증을 통과해야 한다. **단, 전/후 비교 구간(`compare_before`, `compare_after`, `split`)에 한해 대상 차량 인덱스에 적절한 `mirror_before`/`mirror_after` 레퍼런스가 없을 때만 다른 차량 인덱스의 전/후 비교 사진(`mirror_before`/`mirror_after`) 폴백을 허용한다**(추가 공여 차량 제약 없음).
2. **Stage 2 — 롱폼(`16:9`) / 숏폼(`9:16`) 템플릿 기반 영상 편집**:
   - **롱폼(`16:9`, `1920x1080`)과 숏폼(`9:16`, `1080x1920`) 엄격 분리**: 롱폼과 숏폼은 구성, 비율, 자막 배치, 길이, BGM이 완전히 다르므로 절대 혼용하지 않는다.
   - **시나리오/템플릿 기반 빌드**:
     - 템플릿 쉘: `video-automation/work/scenarios/templates/{polestar4_optic,bmw_aceman_optic,porsche997_optic,opticglass_wide1}/`
     - 차종별 시나리오: `video-automation/work/scenarios/<slug>_longform.json` (57.7초 판은 `<slug>_wide1.json`)
     - 공용 롱폼 빌더: `video-automation/work/build_longform.py <slug>` (차종별 편집은 전부 `scenarios/<slug>_longform.json`: 씬별 `plates`/`faces`/`arrows`, 상단 `car` 블록의 `logo`·`logo_size`·`logo_scale`·`compat_cards`; 차종별 .py 빌더를 만들지 않는다), 공통 함수 `longform_common.py` 및 `portable_paths.py`
     - **시나리오가 없는 차는 `make_scenario.py <slug>`가 만든다** (GUI 롱폼·`gdrive_pipeline.py`가 자동 호출): 「옵틱글래스 광각미러 템플릿 1」 skeleton(`templates/opticglass_wide1/skeleton.json`, 57.7초, 13씬 w00~w12, 전환 없음)의 씬 타이밍을 쓰고, 그 차의 영상 클립(`.MOV`/`.mp4`)을 최우선 배치하되 해당 역할의 새 영상 구간이 부족하면 같은 차 폴더의 실제 촬영 사진(`.jpg`/`.png`)으로 자동 폴백해 채우며, `draft_copy.diversify_scenario`로 유튜브 수집 자막(`datasets/youtube_lines.jsonl`) 말투를 반영해 자막·썸네일 2줄을 다양화한다 (손으로 만든 80초 시나리오 cybertruck·santafe·bmwx5·sealion7·honda_cbr650r_106과 이전에 생성된 시나리오는 그대로). **전/후 비교 구간(`compare_before`·`compare_after`·`split`, `opticglass_wide1` 포함 모든 템플릿)에서는 대상 차량 인덱스에 적절한 `mirror_before`/`mirror_after` 레퍼런스가 이미 있으면 정상 대상 차량 우선순위(해당 차량 영상 우선 → 같은 차 사진)를 그대로 유지하며, 대상 차량 인덱스에 적절한 레퍼런스가 없을 때만 다른 차량 인덱스의 적절한 전/후 비교 사진(`mirror_before`/`mirror_after`)으로 폴백한다(브랜드·모델·연식 등 추가 공여 차량 제약 없음).** 번호판·얼굴·미러 위치는 1차 미디어 분류(`_review`)에서 추출한 좌표를 씬 크롭·해상도(`1920x1080`)로 즉시 변환 적용하여 2차 장면 프레임 AI 검수(`MASK_ASK`) 없이 바로 확정한다(빌드 후 `check_text_outputs` 사후 검수도 생략하고 즉시 스테이징·배포). 일반 역할이 부족하거나 전/후 비교 구간에서 대상 차량과 다른 차량 인덱스 모두에 적절한 사진이 없으면 만들지 않고 `구글드라이브다운파일/media/<차>/scenario_short.json`에 이유를 남긴다 (AI 생성물·일반 씬/썸네일 타 차종 혼입 금지).
     - **GUI 두 번째 줄 버튼** (`gdrive_pipeline.py --build`): 「광각미러 템플릿」 = 「옵틱글래스 광각미러 템플릿 1」(템플릿 키 `opticglass_wide1`, 57.7초: 외관 6컷 → 이유 카드 → 시공 전 2컷 → 시공 후 2컷(화살표 4개) → 50:50 분할 2개 → 아웃트로)을 그대로 따르는 `<slug>_wide1.json` → `hermes_<slug>_optic_wide1`. 템플릿의 사진·정지 화면 칸도 그 차의 실제 영상으로 채우고, 자막은 하우스 스타일(검정 박스)로 바뀐다. 「숏폼」 = `build_shorts.py`: 그 차의 롱폼 씬 클립(가림·화살표 완료)을 이은 영상을 「숏폼 영상 프로젝트」의 9:16 타임라인 5개에 구간별로 넣는다 (사용자가 2026-11-09에 고른 방식: 롱폼 자막은 들어가지 않고, 위쪽 훅 2줄은 agy가 쓰고 템플릿의 초록 글로우 그대로). 두 버튼은 썸네일을 만들지 않는다. 롱폼이 이미 광각미러 템플릿 1인 차(자동 생성)는 「광각미러 템플릿」이 agy 호출 없이 롱폼 시나리오를 복사하므로, 이 버튼은 롱폼이 80초인 차(손으로 만든 차, 11-11 이전에 생성된 c40·honda24)의 57.7초 판이 필요할 때 쓴다.
     - **손으로 만드는 80초 롱폼의 길이·구성은 Drive `6. 영상 템플릿 > 옵틱글래스 템플릿`의 「영상 편집 가이드라인 (광각미러)」을 따른다** (자동 생성 롱폼은 위의 57.7초 광각미러 템플릿 1): 80~100초, 8개 섹션(1 인트로 [차종]+[진행한 시공] 외관 5~6컷 → 2 「광각미러가 꼭 필요한 이유」 카드 → 3 시공 전 + 시공 과정 → 4 「한방에 해결」 → 5 시공 후 옵틱 미러 → 6 전/후 비교 분할 + 「혼잡한 도로에서도…」「비가 오나 눈이 오나…」 → 7 따뜻한 마무리 「옵틱글래스로 교체하고 언제나 안전한 운행」 → 8 아웃트로 전체). 템플릿 슬롯(18개, 41.5초)보다 씬이 많으면 시나리오의 모든 씬에 `start`/`dur`를 적고, 빌더가 슬롯을 복제한다(`fit_video_slots`).

### 1.1 광각미러 템플릿 CapCut 기준 프로젝트 및 계보·적용 범위 (필수 준수)
- **필수 준수 규칙**: **광각미러 템플릿(Google Drive 차량 `img/vid` data, `DATA_DIR` = `C:\Users\bssho\OneDrive\바탕 화면\구글드라이브다운파일`, `구글드라이브다운파일/media/`)은 지정된 두 CapCut 기준 프로젝트(`42. 09 포르쉐 997.2 옵틱 [26.03.23]` -> `옵틱글래스 광각미러 템플릿 1 (1)`)의 기준을 따라야 한다.**
- **두 CapCut 기준 프로젝트 경로**:
  1. **기준 프로젝트 1 (`porsche997_optic`, 초기 수동 원형)**: `C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\42. 09 포르쉐 997.2 옵틱 [26.03.23]` (`id=1D4243F2-179F-43c2-AC12-977981653637`, `42.367s`, `17`트랙, `18`슬롯).
  2. **기준 프로젝트 2 (`opticglass_wide1`, 표준 광각미러 템플릿 1)**: `C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\.cloud_cache_7327546324319568897\옵틱글래스 광각미러 템플릿 1 (1)` (`main_timeline_id=27112FC3-97E2-43fc-A81C-C439DFFB1BAD`, `57.733s`, `7`트랙, `13`슬롯).
     - 기준 프로젝트 2의 클라우드 캐시 `draft_content.json` 및 `Timelines/*/draft_content.json`은 `.locked` 암호화 상태이므로 **절대 복호화하지 않고**, 평문 `template.json.bak` / `Timelines/project.json` 및 동일 타임라인(`27112FC3-97E2-43fc-A81C-C439DFFB1BAD`)의 로컬 평문 프로젝트 `C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\옵틱글래스 광각미러 템플릿 1`만 참조·추출한다.
- **두 프로젝트의 관계**: 두 프로젝트는 동일한 CapCut 컨테이너 ID(`1D4243F2-179F-43c2-AC12-977981653637`)와 `draft_virtual_store.json` 루트 ID(`cd484075-d92a-4bc9-b45c-d093d2f9e71b`)를 공유한다. 기준 프로젝트 1(`타임라인 01`, 42.367s)이 초기 포르쉐 997.2 수동 편집 원형이며, 기준 프로젝트 2(`타임라인 33`, 57.733s)는 그 컨테이너 내부에 `타임라인 01`을 유지한 채 비전환·크롭 기반 50:50 분할·13슬롯 재사용 규격으로 표준화한 후속 광각미러 템플릿이다(동일 프로젝트 내 `타임라인 37`에서도 포르쉐 997.2 클립을 템플릿 규격으로 재편집함).
- **도출된 표준 템플릿 기준 (`opticglass_wide1`)**:
  - **캔버스/길이/전환**: `1920x1080`, `30fps`, `57.733s`(`57,733,333us`), `"transitions": false`(화면 전환 없음).
  - **13개 비디오 슬롯 (`w00`~`w12`)**: `w00`(`0.000–4.667s`, `exterior`), `w01`(`4.667–7.833s`, `detail`), `w02`(`7.833–10.067s`, `detail`), `w03`(`10.067–12.567s`, `exterior`), `w04`(`12.567–18.200s`, `card`), `w05`(`18.200–22.600s`, `card`), `w06`–`w07`(`22.600–32.600s`, 각 `5.000s`, `compare_before` 운전석/조수석 순정), `w08`–`w09`(`32.600–42.600s`, 각 `5.000s`, `compare_after` 운전석/조수석 옵틱), `w10`–`w11`(`42.600–50.600s`, 각 `4.000s`, `split` 크롭 기반 좌 순정:우 광각 50:50 분할), `w12`(`50.600–57.733s`, `7.133s`, `outro` `옵틱글래스 광각미러 아웃트로.mp4`).
  - **21개 텍스트 슬롯 (`lt01`, `w04a`/`w04b`, `wb1`/`wb2`, `wc1`~`wc8`, `ws1`~`ws4`, `wz1`~`wz4`)**: `lt01`(`0.000–12.567s`, `{car}`, `[960, 588]`, `size=119`), `w04a`(`12.567–22.600s`, `BY OPTICGLASS`, `[960, 420]`, `size=38`), `w04b`(`12.567–22.600s`, `광각미러가 꼭 필요한 이유`, `[960, 535]`, `size=78`), `wb1`/`wb2`(`22.600s+2.967s`, `32.600s+2.967s`, `[1611, 84]`, `size=56`), `wc1`~`wc8`(`22.600–42.600s`, 각 `2.500s`, `[960, 1002]`, `size=54`), `ws1`/`ws3`(`시공 전`, `[453, 90]`, `#FFFFFF`), `ws2`/`ws4`(`시공 후`, `[1467, 86]`, **`#F4C70F`**), `wz1`~`wz4`(`42.600–50.600s`, 각 `2.000s`, `[960, 1027/1032]`, `size=48`; `wz1`/`wz3` `#FFFFFF`, **`wz2`/`wz4` `#F4C70F`**).
  - **배지 지시 스티커 (`Track[4]`)**: `Guidance EN - Arrow`(`22.600s+2.967s`, `32.600s+2.967s`)는 `wb1`/`wb2` 배지 지시용으로 `opticglass_wide1`(`keep_stickers: true`)에서 유지한다.
  - **오디오 및 `DATA_DIR` 매핑**: 원본 클립 음소거(`volume=0.0`) + BGM `0.000–57.733s` 전 구간 커버; `DATA_DIR/media/<차종>/gdrive_raw/`에서 해당 차종 영상(`.MOV`/`.mp4`) 최우선 + 부족 역할은 동일 차종 사진(`.jpg`/`.png`) 폴백으로 채우며, 전/후 비교 구간(`w06`~`w11`: `compare_before`, `compare_after`, `split`)에 대상 차량 인덱스의 적절한 `mirror_before`/`mirror_after` 레퍼런스가 없을 때만 다른 차량 인덱스의 적절한 전/후 비교 사진으로 폴백한다(대상 차량 인덱스에 적절한 레퍼런스가 있으면 정상 대상 차량 선택을 그대로 유지).
- **CapCut 광각미러 템플릿 · `@optic_glass` 유튜브 자막 스타일 준수 (불투명 검정 박스 오버라이드 폐기)**:
  - `opticglass_wide1` 기반 CapCut 초안과 렌더링되는 `.mp4` 영상은 **현재 CapCut `옵틱글래스 광각미러 템플릿 1` 원본 스타일과 `https://www.youtube.com/@optic_glass` 실제 영상 자막 스타일**을 따른다(**불투명 `#000000` 검정 배경 박스 없음**, `background_style=0`).
  - 슬롯별 스타일: `lt01`(중앙 반투명 화이트 산세리프 `NotoSansKR-Regular`, `alpha≈0.50~0.60`), `w04a`/`w04b`(`GalleryModern.otf` + `BlackHanSans-Regular.ttf` 흰색+그림자), `wb1`/`wb2`(우상단 흰색+검정 외곽선 `0.06` + `Guidance EN - Arrow` 빨간 곡선 화살표), `wc1`~`wc8`(배경 박스 없이 4종 컬러 외곽선·글로우 `花字` 교차: 모노크롬/시안블루/핑크마젠타/골드오렌지), `ws1`~`ws4` 및 `wz1`~`wz4`(`#FFFFFF` / `#F4C70F` + 검정 외곽선 `0.06`).
  - `compare_after`·`split` 씬에는 **`#F26925` 시야 확장 화살표 4개**를 합성한다.
  - 번호판 원근 호모그래피(`로고_번호판.png`)와 작업자/인물 얼굴 원형(`face_mask_circle.png`) 마스킹을 적용한다.
  - BGM은 화면 밖 비디오 트랙 대신 CapCut `audio` 트랙으로 전 구간 배치한다.
- **적용 범위 제한 (R3)**: 위 기준은 **앞으로 생성·빌드하는 광각미러 템플릿(`opticglass_wide1`) 기반 작업부터 적용**하며, **기존 수동 작성 80초 차종별 시나리오(`cybertruck`, `santafe`, `bmwx5`, `sealion7`, `honda_cbr650r_106`)는 변경하지 않고 그대로 유지한다(단, `.mp4` 출력 시 자막 합성은 필수 적용).**
3. **Stage 3 — 유튜브 썸네일(`1280x720`) 생성**:
   - 사진은 `thumb_photos.py`가 고른다: agy가 그 차 폴더의 사진(미러 사진이 없으면 그 차 영상에서 뽑은 장면 `gdrive_raw/_frames/`)을 외관·시공 전·시공 후로 분류하고 번호판·얼굴을 가린 뒤, **별도 AI 재검수(`_verify`, `FIX_ROUNDS`)를 생략하고 즉시 썸네일 생성에 사용한다 (`save` 즉시 `ready`).** 부족하면 썸네일을 만들지 않고 이유를 알린다. 다른 차 사진으로 대신하지 않는다.
   - `옵틱글래스_유튜브_썸네일/template/generate_thumbnail.py`로 `1280x720` JPG 썸네일 2장(`split_horizontal`, `split_vertical`)을 합성한다.
4. **Stage 4 — CapCut 초안·MP4 생성 완료 (차량 생성 시 사후 검수 생략)**:
   - 차량 인덱스 영상/썸네일 생성 시에는 사후 검수 단계를 생략하며, `hermes_<slug>_optic_longform` / `hermes_<slug>_optic_wide1` / `hermes_<slug>_optic_shorts` 초안과 자막 합성 `.mp4`가 생성되는 즉시 완료 처리한다.
   - 국제판 CapCut Desktop(`9.6.x`)은 외부 무인 MP4 export를 지원하지 않으므로, 최종 납품물 CapCut GUI 내보내기가 필요할 때는 사용자가 CapCut GUI에서 MP4로 내보낸다.

---

## 2. 영상 편집 핵심 품질 규칙 (Longform & Shortform)

### 2.1 실제 촬영 영상 최우선 + 같은 차 사진 자동 폴백 (전/후 비교 구간 타 차종 사진 폴백 예외, AI 생성물 금지)
- AI 생성 영상(Runway, Kling, Midjourney 등)이나 무관한 스톡 미디어를 절대 사용하지 않는다. 일반 씬(`exterior`, `detail`, `card`, `before`, `install`, `after`, `close`) 및 Stage 3 유튜브 썸네일은 타 차종 미디어 혼입을 엄격히 금지한다.
- 롱폼·광각미러 템플릿·숏폼·썸네일 4종 모두 해당 차 폴더의 **실제 촬영 영상(`.MOV`/`.mp4`)을 최우선**으로 사용하고, 특정 역할(`외관`, `디테일`, `시공 전`, `시공 후`, `50:50 분할`)에 쓸 영상이 부족할 때만 같은 차 폴더의 **실제 촬영 사진(`.jpg`/`.jpeg`/`.png`, EXIF 정방향 보정 + 번호판/얼굴/화살표 동일 합성)**으로 자동 폴백한다.
- **전/후 비교 구간 타 차종 사진 폴백 (`compare_before`, `compare_after`, `split`)**: `opticglass_wide1`을 포함한 모든 템플릿의 전/후 비교 구간(`compare_before`, `compare_after`, `split`)에서 대상 차량 자체 인덱스에 적절한 `mirror_before`/`mirror_after` 레퍼런스가 이미 존재하면 정상 대상 차량 선택(해당 차 영상 최우선 → 같은 차 사진)을 그대로 유지한다. 단, 대상 차량 인덱스에 적절한 `mirror_before` 또는 `mirror_after` 레퍼런스가 없는 경우에 한해 부족한 쪽만 다른 차량 인덱스의 적절한 전/후 비교 사진(`mirror_before`/`mirror_after`)에서 브랜드·모델·연식 등 추가 공여 차량 제약 없이 자동 폴백한다.
- 매장에서 탈거한 순정 유리를 하우징 앞에 손으로 대어 좁은 반사 시야를 보여주는 비교 컷은 `mirror_before`, 순정 유리를 하우징 위/옆으로 들어 올려 장착된 옵틱글래스의 넓은 반사 시야를 보여주는 비교 컷은 `mirror_after`로 인정한다(단순 배선·분해 작업 컷은 `install_*`로 분리).

### 2.2 사이드미러 전체 프레임 노출 (`Full sidemirror had to be shown`)
- 사이드미러가 나오는 모든 씬(특히 비교 씬 `s13`, `s14` 및 시공 완료 씬)에서 **사이드미러 외곽 베젤(테두리)이 잘리지 않고 미러 전체(100%)가 화면 안에 온전히 보여야 한다.**
- 과도한 확대(`scale`)나 잘못된 크롭으로 미러 끝부분이 잘리는 것을 엄격히 금지한다.

### 2.3 시야 확장 화살표 이펙트 4개 (`arrow effects had to be 4`) 및 정적 점선 제거
- 옵틱 미러 시야를 보여주는 씬(역할 `after`·`compare_after`·`split`: s12·s12b·s12c·s14·s15·s16·s16b·s16c 등)에서는 **굵은 오렌지색(`#F26925`) 화살표 4개(상·하·좌·우 대각 방향)**가 사이드미러 베젤 경계를 가로지르며 바깥쪽으로 뻗어 나갔다 돌아오는 키프레임 애니메이션을 적용한다.
- 핸드헬드(손으로 들고 촬영한) 영상에서 미러 움직임과 따로 노는 정적 점선(static dotted lines) 오버레이는 제거한다.

### 2.4 화면 전환(Transition) 규칙 및 분할화면(Split-Screen) 예외
- 일반 씬 사이에는 역동적인 전환 효과(`cross_dissolve`, `wipe`, `slide`, `fade`, `zoom`)를 교차 적용하여 단조로운 하드컷을 방지한다.
- **절대 예외**: 비교 구간의 직전·진행 중·직후에는 화면 전환 효과를 절대 넣지 않는다 (`should_apply_transition() == False`). 비교 구간은 역할(role)이 `compare_before`·`compare_after`(단독 시공 전/후 컷, 보통 s13·s14·s16c)와 `split`(50:50, s15·s16·s16b)인 씬이다. 전환 효과가 없는 템플릿(`"transitions": false`)은 전체에 넣지 않는다.
- **역할이 규칙을 정한다** (`longform_common.ROLES`, `GLOSSARY.md`): 씬마다 `role` 하나를 두고, `load_scenario`가 역할에서 화살표 4개·전환 금지·장면 종류(옵틱/순정 미러 시야 자리에 시공 장면 금지)를 인메모리로 즉시 확인해 어기면 빌드를 거부한다(분할·화살표 장면에서도 번호판이 실제 노출되면 `로고_번호판.png` 원근 호모그래피 커버를 허용·적용한다). 차량 영상/썸네일 빌드 시 빌드 후 `check_text_outputs` 사후 검수는 생략하고 즉시 스테이징·배포한다.

### 2.5 개인정보 및 프라이버시 완벽 보호 (번호판 & 얼굴 마스킹)
- **차량 번호판 마스킹**: 차량 외관 씬(`s00`, `s01` 등)에서 번호판이 노출될 경우, 단순 블러나 고정 스티커가 아니라 **`로고_번호판.png`(`로고_번호판_롱.png` / `로고_번호판_숏.png`)를 번호판 4개 꼭짓점 원근 변환(Perspective Homography, `cv2.getPerspectiveTransform` + `cv2.warpPerspective`) 및 프레임별 템플릿 추적(NCC tracking)으로 합성**하여 카메라가 흔들려도 번호판에 완벽히 밀착되게 가린다.
- **작업자/인물 얼굴 마스킹**: 시공 과정(`s03`~`s09`) 등에서 작업자나 행인의 얼굴(측면/숙인 얼굴 포함)이 노출되는 모든 프레임은 **`face_mask_circle.png` (불투명 검정 원형 마스크 + 옵틱글래스 로고)**로 프레임별 추적 마스킹하여 얼굴 노출 프레임을 0으로 만든다.

### 2.6 오디오(BGM) 및 자막 필수 합성·타이포그래피 절대 규칙
- **BGM 100% 구간 커버**: 배경음악(`031 - Mood Audio Edit (Non Copyright).wav` 또는 지정 BGM)은 영상 시작(`0.0s`)부터 아웃트로 끝까지 빈 구간 없이 100% 채워야 하며, 영상이 BGM보다 길면 자연스럽게 루프 연결한다. 원본 현장음(잡음·대화)은 음소거(`mute`)한다.
- **모든 영상 자막 필수 포함·합성 (무자막 출력 절대 금지)**:
  - CapCut 초안(롱폼, 광각미러 템플릿, 숏폼 5개 전 타임라인 — **`비트` 포함**)뿐 아니라 디스크에 생성되는 **모든 완성·프리뷰 `.mp4` 영상(`media/<차>/<slug>_<variant>.mp4`, `output/<slug>/<slug>_optic_<variant>.mp4`, `output/<slug>/shorts/01..05_*.mp4`)에는 반드시 자막이 합성(번인)되어 있어야 한다.** 자막 없는 완성/프리뷰 `.mp4` 출력은 엄격히 금지한다.
- **자막 스타일**:
  - **광각미러 템플릿(`opticglass_wide1`) 및 신규 롱폼**: CapCut `옵틱글래스 광각미러 템플릿 1` 원본 스타일과 `https://www.youtube.com/@optic_glass` 실제 영상 스타일을 따른다(불투명 검정 배경 박스 없음, 슬롯별 반투명 타이틀/이유 카드/4종 컬러 외곽선·글로우/화이트·`#F4C70F` 검정 외곽선).
  - **숏폼 5종(`비트`, `외관`, `시공 전`, `시공 후`, `전후 비교`)**: `@optic_glass/shorts` 실제 영상 스타일을 따른다(순검정 `1080x1920` 캔버스 + 상단 순백색 `#FFFFFF` 굵은 2줄 훅 자막 + 중앙 16:9 자막 포함 본 영상 + 하단 `Optic-Glass` 로고).
  - **한글 폰트 무결성**: 정적 내장 한글 글꼴(`NotoSansKR-Bold-Static.ttf`, `NotoSansKR-Regular.otf`, `BlackHanSans-Regular.ttf`, `Paperlogy-7Bold.ttf` 등)을 사용하며, 영문 전용 폰트 단독 사용으로 인한 한글 깨짐(`□`)이나 가변 글꼴 단독 사용을 금지한다. CapCut 텍스트 소재에는 반드시 `fonts` 배열과 `content.styles[].font`에 `{id, path}`를 모두 기록한다.
  - **기존 80초 수동 5대 시나리오(R3)**: 기존 시나리오의 검정 배경 박스(`box: true`) 설정은 유지하되 `.mp4` 빌드 시 자막을 반드시 합성한다.

---

## 3. 유튜브 썸네일(`1280x720`) 제작 절대 규칙 (`옵틱글래스_유튜브_썸네일/template/`)
좌표·글자 크기의 기준은 `generate_thumbnail.py`의 `render_split_horizontal`·`render_split_vertical` 코드다. 이 문서에 맞추려고 생성기를 고치지 않는다.
1. **레이아웃 (하단 자막 바 없음)**:
   - 배경: 화면 전체(1280x720)에 그 차의 외관 사진 (위쪽·오른쪽만 살짝 어둡게).
   - 왼쪽 위: 2줄 제목 (1줄 차 이름, 2줄 카피).
   - 오른쪽 약 30%: `시공 전`/`시공 후` 사진 카드 2장. `split_horizontal`은 나란히(가운데 화살표), `split_vertical`은 위아래. `시공 후` 카드는 강조색 테두리.
2. **블러(Blur) 효과 전면 금지**:
   - 썸네일 내 모든 텍스트, 배지, 외곽선, 그림자에서 가우시안 블러(`GaussianBlur`)를 절대 사용하지 않는다(선명한 하드 외곽선만 사용).
3. **타이포그래피**: 제목과 카드 라벨 모두 `Paperlogy-9Black.ttf`의 기울인 그라데이션 글자. 제목은 검정 하드 외곽선(카드 라벨은 레이아웃에 따라 외곽선 없음).
4. **옵틱글래스 로고**: `옵틱글래스 로고.png`를 왼쪽 아래에 높이 40px로, 배지 없이 합성한다.

---

## 4. CapCut 안전 가드레일 및 포터블 실행 규칙
1. **복호화 금지 및 기존 초안 보호**:
   - 암호화된 CapCut 초안(`draft_content.json` 또는 `Timelines/*/draft_content.json`의 첫 바이트가 `{`가 아닌 초안)은 절대 복호화하거나 수정하지 않는다.
   - CapCut drafts 폴더에는 오직 `hermes_` 또는 `pycapcut_smoke_`로 시작하는 새 폴더만 생성/업데이트한다.
2. **CapCut 실행 중 직접 쓰기 금지**:
   - `CapCut.exe`가 실행 중이면 `work/capcut_stage/`에 스테이징하고, CapCut 종료 후 배포(`deploy_staged`)한다.
3. **포터블 에셋 및 동적 경로 해석 (`video-automation/work/portable_paths.py`)**:
   - 다른 컴퓨터에서도 동일하게 동작하도록 모든 외부 에셋(폰트, 브랜드 로고, 번호판/얼굴 마스크, 아웃트로, BGM, 전 차종 조견표)은 `video-automation/assets/` 아래에 내장되어 있다.
   - 스크립트와 시나리오는 하드코딩된 사용자 경로(`C:\Users\bssho\...`)가 없더라도 `video-automation/assets/` 및 현재 로그인된 사용자의 `%LOCALAPPDATA%\CapCut` 경로로 자동 폴백(fallback)해야 한다.
4. **개발용 회귀 검증 스크립트 (차량 영상/썸네일 생성 시 생략)**:
   - `check_templates.py` 및 `check_text_outputs.py`는 템플릿이나 빌더 코드 자체를 개발·수정할 때만 단독 실행하는 개발용 도구이며, **차량 인덱스 영상/썸네일 생성 워크플로우에서는 실행하지 않고 생략**한다:
     - `py video-automation/work/check_templates.py`
     - `py video-automation/work/check_text_outputs.py`
