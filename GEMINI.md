# OpticGlass (옵틱글래스) 유튜브 영상·썸네일 자동화 워크스페이스 지침 (`GEMINI.md`)

이 저장소는 **옵틱글래스(OpticGlass) 와이드 미러 유튜브 콘텐츠(16:9 롱폼, 9:16 숏폼, 1280x720 썸네일) 엔드투엔드 자동화 시스템**의 포터블 배포판입니다.
다른 컴퓨터에서 이 폴더를 열었을 때도 이전 세션의 모든 대화 내역, 피드백, 편집 규칙을 100% 동일하게 유지하며 작동하도록 구성되어 있습니다.

---

## 1. 포터블 폴더 구조 (Directory Architecture)

| 경로 | 설명 |
|---|---|
| `.agents/rules/opticglass-workflow-rules.md` | **항상 적용되는 핵심 워크플로우/품질 규칙** (/teamwork 병렬 협업 의무화, 롱폼·숏폼 분리, 미러 100% 노출, 화살표 4개, 번호판 호모그래피/얼굴 원형 마스킹, 70:30 무블러 썸네일 등) |
| `.agents/teamwork/` | **팀워크 멀티에이전트 메타데이터 전용 공간** (계획, 진행 보고, 에이전트 인계 `handoff.md` 등 보관. 소스 코드·미디어 파일 저장 금지) |
| `.agents/skills/video-editing-automation/` | CapCut(`pyCapCut`) 헤드리스 영상 편집 스킬 및 레퍼런스 |
| `.agents/skills/opticglass-pipeline/` | Google Drive 수집 → 영상 편집 → 썸네일 생성 통합 파이프라인 스킬 |
| `archive/sessions/SESSION_INDEX.md` | **전체 세션 대화 내역 인덱스** (`antigravity_brain/` 17개 세션 전체 트랜스크립트 + `hermes_json/` 15개 세션 219개 메시지 백업) |
| `video-automation/assets/` | **포터블 공용 에셋 번들** (`fonts/`, `logos/`, `masks/`, `outro/`, `audio/`, `compat_cards/` 전 차종 조견표 1,085장) |
| `구글드라이브다운파일/` | **git 제외 작업 데이터** (`media/` Drive 다운로드·장면 클립·사진, `output/` 썸네일, `frames/` 확인 프레임). 코드는 `portable_paths.DATA_DIR`(`C:\Users\bssho\OneDrive\바탕 화면\구글드라이브다운파일`)로 찾음 |
| `video-automation/work/portable_paths.py` | 다른 PC에서도 `C:\Users\bssho\...` 경로를 현재 PC의 `video-automation/assets/` 및 `%LOCALAPPDATA%\CapCut` 경로로 자동 매핑하는 포터블 리졸버 |
| `video-automation/work/build_longform.py` | **모든 차종 공용 16:9 롱폼 빌더** (`py build_longform.py <slug>`): 차종별 코드 없이 `scenarios/<slug>_longform.json` 하나로 빌드 (씬·번호판/얼굴 키프레임·화살표·자막·`car` 블록) |
| `video-automation/work/make_scenario.py` | **시나리오 자동 생성기** (`py make_scenario.py <slug>`): 시나리오 없는 차에 「옵틱글래스 광각미러 템플릿 1」(`opticglass_wide1`, 57.733초·13씬·전환 없음, `templates/opticglass_wide1/skeleton.json`) 타이밍·자막으로 그 차 영상(부족 시 같은 차 사진 폴백; 전/후 비교 구간 `compare_before`·`compare_after`·`split`은 대상 차량 인덱스에 적절한 레퍼런스가 없을 때만 다른 차량 인덱스의 전/후 비교 사진으로 추가 제약 없이 폴백)을 agy가 배치하고 1차 분류(`_review`)의 번호판·얼굴·화살표 좌표를 2차 프레임 검수 없이 즉시 변환 적용. `--variant wide1`은 `<slug>_wide1.json` 생성 |
| `video-automation/work/build_shorts.py` | **9:16 숏폼 빌더** (`py build_shorts.py <slug>`): `templates/shorts_optic`(타임라인 5개)에 롱폼 씬 클립(`shorts_source.mp4`)을 구간별로 넣어 숏폼 5개(`hermes_<slug>_optic_shorts`) 생성 |
| `video-automation/work/youtube_lines.py` | **유튜브 채널 대사·구조 학습** (`py youtube_lines.py`): 채널 최근 영상·숏츠 자막을 OCR+agy로 정리해 `datasets/youtube_lines.jsonl` 등 생성 (`draft_copy.py`가 예시로 사용) |
| `video-automation/work/longform_common.py` | 템플릿 기반 16:9 롱폼 클립 인코딩·마스킹·CapCut 자막 공통 빌더 엔진 |
| `video-automation/work/gdrive_pipeline.py` | Stage 1(Google Drive 다운로드) → Stage 2(영상 빌드) → Stage 3(`thumb_photos`로 사진 고르기·가리기 + 썸네일 생성, 사후 검수 생략) 통합 실행기 |
| `video-automation/work/scenarios/` | 차종별 편집 시나리오 JSON (`<slug>_longform.json`, 57.7초 판 `<slug>_wide1.json`) 및 추출된 CapCut 템플릿 쉘 (`templates/`) |
| `옵틱글래스_유튜브_썸네일/template/` | `generate_thumbnail.py` (1280x720 무블러 Paperlogy 썸네일 생성기, 레퍼런스 `catalog_0002_0043.json`) |
| `pyCapCut/` | 템플릿 모드 및 메타데이터 보존 패치가 적용된 로컬 `pyCapCut` 패키지 (`pip install -e ./pyCapCut`) |
| `setup.bat` | 새 컴퓨터에서 없는 프로그램(Python·ffmpeg·CapCut·agy·Node.js) winget 설치, 폰트 설치, `pyCapCut` editable 설치, 세션 브레인 복원, 검증 테스트를 한 번에 수행하는 부트스트랩 스크립트 |

---

## 2. 핵심 불변 규칙 요약 (상세 내용은 `.agents/rules/opticglass-workflow-rules.md` 참조)

0. **영상편집 병렬 팀워크(/teamwork) 의무화 · 검수 생략 · 10분 이내 완성**: 영상편집 시 항상 /teamwork를 통하여 병렬로 작업한다 (e.g. 이미지 분류, 전처리, 영상 인식, 편집). 단일 직렬 실행을 지양하고 역할 분담형 병렬 서브에이전트를 통해 작업 속도와 파이프라인 무결성을 보장한다. 단, **같은 차의 파이프라인·빌더는 한 번에 한 실행만** 돌린다 (GUI 포함; 실행 안에서 이미 병렬로 돎). **차량 인덱스 영상/썸네일 생성 과정에서는 검수에 걸리는 시간을 없애기 위해 모든 사후 검수 단계(썸네일 가린 사진 AI 재검수, 시나리오 2차 프레임 검수, 빌드 후 `check_text_outputs` 사후 검수, `/teamwork` 다단계 검수·감사 게이트)를 전면 생략하며, 영상 생성은 `/teamwork`로도 반드시 10분 이내에 완성되어야 한다** (규칙 파일 0.2).
1. **롱폼(`16:9`) vs 숏폼(`9:16`) 분리 및 영상 우선·사진 폴백**: 두 포맷을 절대 섞지 않으며, 해당 차종 폴더의 실제 촬영 `.MOV`/`.mp4` 영상을 최우선 사용하고 부족한 역할은 같은 차종의 실제 촬영 사진(`.jpg`/`.png`)으로 자동 폴백한다(AI 생성 영상 금지; 일반 씬 및 Stage 3 썸네일은 타 차종 혼입 금지). **전/후 비교 구간(`compare_before`·`compare_after`·`split`, `opticglass_wide1` 포함 모든 템플릿)**에서는 대상 차량 인덱스에 적절한 `mirror_before`/`mirror_after` 레퍼런스가 있으면 정상 대상 차량 선택을 그대로 유지하되, 대상 차량 인덱스에 적절한 레퍼런스가 없을 때만 다른 차량 인덱스의 적절한 전/후 비교 사진(`mirror_before`/`mirror_after`)에서 브랜드·모델·연식 등 추가 공여 차량 제약 없이 폴백한다.
2. **단일 차종 폴더 격리**: Google Drive `0.옵틱 광각` (`1TT2v1sLCQdBIISjDucJPJGcineVIB76B`) 내 해당 차종 폴더의 미디어만 사용하며(Stage 1 수집·일반 씬·Stage 3 썸네일 타 차종 혼입 금지), 위 1항의 전/후 비교 구간(`compare_before`·`compare_after`·`split`) 타 차종 사진 폴백만 예외로 허용한다.
3. **사이드미러 100% 노출 (`Full sidemirror had to be shown`)**: 사이드미러 외곽 베젤이 화면 밖으로 잘리지 않도록 전체 미러 형상을 온전히 보여준다.
4. **시야 확장 화살표 4개 (`arrow effects had to be 4`)**: 굵은 오렌지색(`#F26925`) 화살표 4개가 미러 베젤 경계를 넘어 바깥으로 뻗어 나갔다 돌아오며, 핸드헬드 영상에서 어긋나는 정적 점선은 제거한다. 역할(role)이 `after`·`compare_after`·`split`인 장면은 화살표 4개가 없으면 `load_scenario`가 빌드를 거부한다 (`GLOSSARY.md` 장면 역할).
5. **화면 전환(Transition) 규칙**: 일반 씬 간에는 `cross_dissolve`, `wipe`, `slide`, `fade`, `zoom`을 교차 적용하되, **비교 구간(역할 `compare_before`·`compare_after`·`split`, 80초 시나리오는 보통 s13·s14·s15·s16·s16b·s16c, 광각미러 템플릿 1은 w06~w11) 전·중·후에는 전환 효과를 절대 넣지 않는다.** 전환 효과가 없는 템플릿(`template.json`의 `"transitions": false`, `opticglass_wide1`)은 전체에 넣지 않는다. (`load_scenario`가 역할 규칙을 즉시 확인하며, 차량 영상 빌드·배포 시 사후 `check_text_outputs` 검수는 생략한다.)
6. **프라이버시 마스킹**:
   - 번호판: `로고_번호판.png`를 번호판 4개 꼭짓점 원근 호모그래피(`warpPerspective`) + 프레임 추적으로 밀착 합성 (분할·화살표 장면에서도 번호판이 실제 노출되면 동일 적용).
   - 얼굴: 작업자/인물 얼굴이 나오는 모든 프레임에 `face_mask_circle.png` 원형 추적 마스킹 적용.
7. **BGM 100% 커버 및 모든 영상 자막 필수 합성**: BGM은 영상 시작부터 끝까지 빈 구간 없이 채우고 현장음은 음소거한다. CapCut 초안(롱폼·광각·숏폼 `비트` 포함 전 5개 타임라인)과 디스크에 생성되는 모든 `.mp4` 영상에는 반드시 자막이 포함·합성되어야 하며 무자막 출력을 금지한다. 광각미러 템플릿(`opticglass_wide1`)과 숏폼은 CapCut 광각미러 템플릿 원본 스타일 및 `https://www.youtube.com/@optic_glass` 실제 영상 자막 스타일(불투명 검정 배경 박스 없음, 슬롯별 반투명 타이틀/이유 카드/4종 컬러 글로우·외곽선/화이트·`#F4C70F` 검정 외곽선, 숏폼 상단 순백 볼드 2줄 훅)을 따른다.
8. **유튜브 썸네일(`1280x720`)**: 그 차 외관 사진 전체 배경 + 왼쪽 위 2줄 제목 + 오른쪽 `시공 전`/`시공 후` 카드 2장, 하단 자막 바 없음, **블러(GaussianBlur) 전면 금지**. 좌표·글꼴·크기는 `generate_thumbnail.py` 코드가 기준이다 (규칙 파일 3장). 사진은 `thumb_photos.py`가 고른다: agy가 그 차 사진(미러 사진이 없으면 그 차 영상에서 뽑은 장면)을 분류하고 번호판·얼굴을 가린 뒤 **별도 검수를 생략하고 즉시 사용한다** (`save` 즉시 `ready`).
9. **LLM은 Antigravity 구독(agy)만**: 대사 초안, 썸네일 AI 배경, GUI의 agy 영상 수정은 모두 `video-automation/work/llm.py`를 거쳐 agy CLI(데스크톱 앱과 같은 계정, 기본 Orchestrator (Carbon), 작업별 모델은 `llm_config.json`)로 실행한다. API 키 경로는 없다.
10. **광각미러 템플릿 CapCut 기준 프로젝트 준수 및 적용 범위 (R1/R3)**:
    - **필수 준수**: 광각미러 템플릿(Google Drive 차량 `img/vid` data, `DATA_DIR` = `C:\Users\bssho\OneDrive\바탕 화면\구글드라이브다운파일`)은 지정된 두 CapCut 기준 프로젝트의 기준을 따라야 한다:
      1. 기준 프로젝트 1 (`porsche997_optic`, `1D4243F2-179F-43c2-AC12-977981653637`, 42.367s): `C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\42. 09 포르쉐 997.2 옵틱 [26.03.23]`
      2. 기준 프로젝트 2 (`opticglass_wide1`, `27112FC3-97E2-43fc-A81C-C439DFFB1BAD`, 57.733s): `C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\.cloud_cache_7327546324319568897\옵틱글래스 광각미러 템플릿 1 (1)` (클라우드 `.locked` 암호화 파일은 복호화 금지; 평문 `template.json.bak` / `Timelines/project.json` 및 로컬 평문 `옵틱글래스 광각미러 템플릿 1` 참조)
    - **계보 및 기준**: 프로젝트 1(`타임라인 01`)의 동일 컨테이너(`1D4243F2-...`)에서 발전해 표준화된 13슬롯 재사용 템플릿(`타임라인 33`)이 프로젝트 2다. `1920x1080`, `30fps`, `57.733s`, 13씬 `w00`~`w12`, `transitions: false`, 크롭 기반 50:50 분할(`w10`~`w11`), 21개 텍스트 슬롯(`ws2`/`ws4`/`wz2`/`wz4` 강조색 `#F4C70F`), 배지 지시 스티커(`Track[4]`), 전 구간 BGM·음소거를 따르며, 자막은 CapCut 원본 광각미러 템플릿 및 `https://www.youtube.com/@optic_glass` 실제 영상 스타일(검정 배경 박스 없음, 4종 컬러 글로우/검정 외곽선 보존)을 준수한다(`#F26925` 화살표 4개, 번호판/얼굴 마스킹, `audio` 트랙 BGM 유지).
    - **적용 범위 (R3)**: 앞으로 생성·빌드하는 `opticglass_wide1` 기반 작업부터 적용하며, 기존 수동 작성 80초 시나리오(`cybertruck`, `santafe`, `bmwx5`, `sealion7`, `honda_cbr650r_106`)는 변경하지 않는다(단, `.mp4` 빌드 시 자막은 필수 합성).

---

## 3. 자주 쓰는 실행 및 검증 명령어

```powershell
# 1. 새 PC 초기 세팅 (폰트 설치 + pyCapCut 설치 + 세션 복원 + 검증)
.\setup.bat

# 2. 템플릿 및 전 차종 시나리오 무결성 검증
py video-automation/work/check_templates.py
py video-automation/work/check_text_outputs.py

# 3. 차종별 통합 파이프라인 실행 (Google Drive 동기화 -> 영상 초안 빌드 -> 썸네일 사진 고르기 -> 1280x720 썸네일 생성)
py video-automation/work/gdrive_pipeline.py --vehicle cybertruck
py video-automation/work/gdrive_pipeline.py --vehicle santafe
py video-automation/work/gdrive_pipeline.py --vehicle bmwx5
py video-automation/work/gdrive_pipeline.py --vehicle sealion7

# 4. 영상 리빌드 없이 썸네일만 즉시 재생성
py video-automation/work/gdrive_pipeline.py --vehicle santafe --skip-video-rebuild
```
