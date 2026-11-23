# 다른 PC 배포 체크리스트

이 PC(원본)에서 2026-11-05에 확인한 버전입니다. 기준은 공용 롱폼 빌더 커밋 `6269d64`와 그 뒤의 배포 수정입니다.
"필수"가 빠지면 롱폼 빌드가 멈추고, "선택"은 해당 기능만 안 됩니다.
`setup.bat`이 아래 1장에서 없는 프로그램을 winget으로 설치하고(Python 3.14, ffmpeg, CapCut, agy, Node.js) 모두 확인합니다. 필수 프로그램이 없으면 무엇이 없는지 출력하고 종료 코드 1로 끝납니다.

## 1. 설치할 프로그램

| 프로그램 | 원본 PC 버전 | 필수 | 코드가 찾는 위치 / 제약 |
|---|---|---|---|
| Python (64-bit, py/pyw 런처, **tcl/tk 포함**) | 3.14.7 (Tk 9.0) | 필수 | `py`, `pyw`. **3.12 이상** (고정된 numpy 2.5.4가 요구). GUI는 tkinter |
| ffmpeg (PATH에) | 9.0.2 full_build (gyan.dev) | 필수 | 그냥 `ffmpeg`. lavfi, libx264, libmp3lame 필요 (`winget install Gyan.FFmpeg`). `longform_common`을 import하는 순간 실행되므로, 없으면 모든 빌드·검사가 바로 실패 |
| CapCut 데스크톱 | 9.6.0.4097, 9.7.0.4153 | 필수 | `%LOCALAPPDATA%\CapCut`. 자동 배포는 **9.7.0.4139 이하만** (`preflight_check.py` `VERIFIED_MAX_VERSION`), 10.x는 차단. 더 새 버전이면 초안이 `capcut_stage`에만 남음 |
| gdrive CLI | 런처 0.0.7, CLI 999922155 | 필수 (Drive 내려받기) | 저장소의 `.agents/skills/gdrive/scripts/gdrive.cmd`. 처음 실행할 때 curl로 exe를 받음 (인터넷 필요) |
| agy (Antigravity CLI) | 1.5.0 (자동 업데이트) | 필수 (썸네일: agy가 사진을 고르고 가림, 검수 생략, 사람이 고르지 않음). AI 배경, 대사 초안, GUI 영상 수정에도 씀 | `llm_config.json`의 `agy_path`, 없으면 `%USERPROFILE%\.gemini\bin\agy.exe`, 그것도 없으면 PATH의 `agy` |
| NVIDIA 드라이버 | RTX 3060, 610.88 | 선택 | 있으면 NVENC로 빠르게 인코딩, 없으면 자동으로 libx264 |
| .NET Framework 4 | Windows 기본 | 선택 | `opticglass_gui.exe` 실행 |

## 2. Python 패키지

저장소 루트의 [requirements.txt](requirements.txt)에 원본 PC 버전이 고정되어 있고, setup이 이 버전으로 설치합니다.

```powershell
py -m pip install -r requirements.txt -e ./pyCapCut
```

- **opencv-python** 5.0.0.93, **numpy** 2.5.4, **pillow** 12.3.0, **pillow-heif** 1.8.1
- **pycapcut** 0.0.3: 반드시 저장소의 패치본(`pyCapCut/`, 브랜치 `fix/template-mode-data-loss`, 커밋 `00e08e6`)을 editable로 설치합니다. 함께 깔리는 패키지는 pymediainfo 7.0.1, imageio 2.38.1, uiautomation 2.0.29, comtypes 1.4.17입니다.
- **scenedetect** 0.7.2: 파이프라인 빌드에는 쓰지 않습니다. 참조 영상 컷 분석(`video-editing-automation` 스킬)에만 씁니다.
- **필요 없음:** librosa, scipy, requests, google-auth, google-genai, fontTools는 지금 파이프라인이 쓰지 않습니다. LLM은 agy로만 부릅니다.

## 3. 저장소에 들어 있어야 하는 것

| 무엇 | 경로 | 비고 |
|---|---|---|
| 코드 전체 | `opticglass_gui.py`·`.exe`, `video-automation/work/*.py` (`build_longform.py`, `gdrive_pipeline.py` …), `옵틱글래스_유튜브_썸네일/template/` | |
| 패치된 pyCapCut | `pyCapCut/` | **git clone으로는 빈 폴더가 옵니다** (gitlink, `.gitmodules` 없음). zip이나 폴더 복사로 옮겨야 합니다 |
| 시나리오·템플릿 | `video-automation/work/scenarios/*_longform.json`, `templates/` | |
| Drive 연결 | `scenarios/drive_folders.json`, `datasets/drive_vehicle_index.json` | 아직 git에 없음 (작업 폴더와 zip에는 있음) |
| LLM 설정 | `video-automation/work/llm_config.json` | |
| 공용 에셋 | `video-automation/assets/`: fonts 5개, logos 86개, 조견표 1,085장, BGM 2곡, 아웃트로 3개, 마스크 | 저장소 밖 원본(Downloads, OneDrive)이 없을 때 자동으로 이쪽을 씁니다 |
| 번호판·얼굴 마스크 | `구글드라이브다운파일/media/<차>/로고_번호판.png`, `구글드라이브다운파일/media/face_mask_circle.png` | |
| 썸네일 사진 선택 | `구글드라이브다운파일/media/<차>/thumb_picks.json`, `thumb/` | santafe, sealion7만 있음 (git에 없음, zip에는 있음) |
| 원본 영상 (.MOV) | `구글드라이브다운파일/media/<차>/gdrive_raw/` | 롱폼 4대 약 5.5 GB, bmwx7 769 MB. 가벼운 zip에서는 빠지고, 첫 실행 때 Drive에서 자동으로 받습니다 |

## 4. 계정별로 새 PC에서 직접 해야 하는 것 (zip으로 옮길 수 없음)

1. **Google Drive:** `& .agents\skills\gdrive\scripts\gdrive.cmd auth login`. Drive 폴더 `1TT2v1sLCQdBIISjDucJPJGcineVIB76B`이 보이는 계정이어야 합니다. 토큰은 사용자 폴더(`~/.gemini/antigravity/plugin_data/…`)에 생깁니다.
2. **Antigravity:** agy 로그인 (구독 계정).
3. **CapCut:** 로그인한 뒤 한 번 실행합니다. 전환 효과 5종은 새 PC에서 CapCut이 내려받습니다.
4. **Claude:** 커넥터를 다시 연결합니다 (HANDOFF.md 참고).

## 5. 배포 순서

1. 이 PC에서 zip을 만듭니다: `py create_portable_release.py`. 영상까지 넣으려면 `--with-raw`를 붙입니다.
   - 가벼운 zip은 약 1.3 GB입니다. `.MOV`와 씬 클립, 빌드 캐시, 백업, 로그인 토큰은 빠집니다.
   - 텍스트 파일 속 API 키·토큰은 zip 안에서 `<REDACTED>`로 가려집니다.
2. (선택) 1장의 프로그램을 직접 설치합니다. 안 하면 4번의 `setup.bat`이 winget으로 설치합니다.
3. zip을 풉니다. 메신저나 브라우저로 받았다면 zip 속성에서 "차단 해제"를 먼저 합니다.
4. `setup.bat`을 더블클릭합니다.
   - 없는 프로그램을 winget으로 설치하고 확인한 뒤, 폰트와 `requirements.txt` 버전의 패키지를 설치한 뒤 검사를 돌립니다.
   - `[없음]`이 나오면 그 프로그램을 설치하고 다시 실행합니다.
5. 4장의 로그인을 합니다.
6. GUI에서 차를 골라 실행합니다. 시나리오가 쓰는 영상이 없으면(가벼운 zip) 그 차의 Drive 폴더에서 자동으로 내려받습니다. `gdrive_pipeline.py --vehicle <slug>`로 직접 실행해도 같습니다.

## 6. 지금 알려진 문제

- **API 키 폐기 필요:** `archive/sessions/antigravity_brain/742a7a43…/transcript*.jsonl`에 Google API 키(`AIzaSy…`) 6개가 평문으로 있습니다. 새 zip에서는 가려지지만, git 기록과 예전 zip(10-27)에는 남아 있습니다. Google Cloud 콘솔에서 키를 폐기해야 합니다.
- **CapCut 버전 제한:** 새로 설치한 CapCut은 9.7.0.4139보다 새것이라 자동 배포가 막힙니다. 초안은 `capcut_stage`에 만들어지므로, 스모크 테스트 후 `preflight_check.py`의 `VERIFIED_MAX_VERSION`을 올리거나 직접 옮겨야 합니다.
- **BMW X7 숏폼:** 전용 빌더 `build_bmwx7_shorts.py`는 2026-11-16에 지웠습니다 (이미 배포된 초안만 남음). `구글드라이브다운파일/media/bmwx7/`의 `.MOV`는 Drive 연결이 없어 다시 받을 수 없으니, 필요하면 `--with-raw` zip을 쓰거나 그 폴더를 따로 복사합니다.
- **썸네일 사진:** agy가 고르고 번호판·얼굴을 가린 뒤 **별도 AI 재검수를 생략하고 즉시 사용**합니다(10분 이내 완성 규칙). 사진에 미러 화면이 없으면 영상에서 장면을 뽑고, 그래도 없으면 썸네일을 만들지 않고, 무엇이 부족한지 100자 안팎의 리포트를 GUI 메시지박스로 띄웁니다 (2026-11-10부터: 시공 장면으로 대신하지 않음. 이전에 시공 장면으로 저장된 audi_q5·트래버스 선택은 무효). 다른 차 폴더의 사진은 같은 모델이라도 쓰지 않습니다. agy가 5분 안에 답하지 않으면 한 번 더 묻습니다. 사진 분류(`photo_check`)는 `llm_config.json`에서 `gemini-4-carbon-low`를 씁니다 (2026-11-13 argon-low에서 바꿈. 나머지 작업은 기본 Orchestrator (Carbon), 썸네일 AI 배경만 argon-high: orchestrator는 그림을 5분 안에 못 만듦). high는 사진 8장에 중앙값 2.5분이 걸렸고, 약 10%가 5분을 넘겼습니다(2026-11-09). low는 약 1분이고 얼굴·번호판을 high만큼 찾습니다. 로그의 `[AI] agy 5분 시간 초과` / `안전 필터 차단`이 다시 자주 보이면 이 값을 먼저 보세요. 저장된 선택은 santafe, sealion7, audi_q5에 있습니다.
- **새 차 롱폼:** 시나리오가 없는 차는 롱폼을 누르면 `make_scenario.py`가 agy 1차 분류(`_review`) 결과로 「광각미러 템플릿 1」(57.7초, 전환 없음) 시나리오를 만듭니다 (2차 장면 프레임 검수 및 사후 `check_text_outputs` 검수는 생략하여 `/teamwork`로도 10분 이내 완성). 전/후 비교 구간(`compare_before`·`compare_after`·`split`)은 대상 차량 인덱스에 적절한 `mirror_before`/`mirror_after` 레퍼런스가 있으면 정상 대상 차량 선택을 유지하되, 없을 때만 다른 차량 인덱스의 적절한 전/후 비교 사진에서 추가 공여 차량 제약 없이 폴백합니다. 일반 역할(외관 등)이 없거나 전/후 비교 구간에서 다른 차량 인덱스에도 적절한 사진이 없으면 "영상 부족"으로 표시하고 만들지 않습니다. 만든 시나리오는 빌드 뒤 배포된 CapCut 초안을 열어 필요 시 사람이 바로 확인할 수 있습니다 (자동 배포가 막힌 PC에서는 `capcut_stage`의 초안을 옮겨서 엽니다).
- **Python이 여러 개인 PC:** 모든 실행(GUI exe, `.bat`, setup, 사용법의 `py ...`)은 `-3` 없이 `py`/`pyw`로 그 PC의 기본 Python을 씁니다. `py -3`는 설정과 상관없이 가장 최신 3.x를 고르기 때문입니다. 패키지를 깐 버전을 기본으로 정합니다: 사용자 환경 변수 `PYTHON_MANAGER_DEFAULT=3.14` (Python 설치 관리자), 옛 py 런처면 `PY_PYTHON=3.14`. 원본 PC는 11-06에 다른 도구용 3.15가 깔려 이렇게 3.14로 고정했습니다.
- **광각미러 템플릿 / 숏폼 버튼:** 처음 누르면 「광각미러 템플릿」은 롱폼이 80초인 차(손으로 만든 차와 11-11 이전에 생성된 c40·honda24 등)에서만 시나리오를 agy로 새로 만들고 (가림 표시 agy 호출 약 15회; 자동 생성 롱폼 차는 롱폼 시나리오를 복사), 「숏폼」은 훅 문구를 agy에 한 번 묻습니다. 숏폼은 그 차의 롱폼 시나리오가 있어야 하며, 없으면 롱폼 시나리오부터 만듭니다. 숏폼 초안은 CapCut 다중 타임라인 프로젝트(타임라인 5개)입니다. 글로우 훅 문구는 CapCut 캐시의 텍스트 템플릿·도현 글꼴을 쓰므로, 새 PC에서는 CapCut이 로그인 상태로 한 번 내려받아야 보입니다.
- **CapCut 전환 효과 5종:** 새 PC의 CapCut이 로그인 상태에서 내려받아야 보입니다.

## 7. 2026-11-05에 고친 것

- **`setup_on_new_pc.ps1` (11-13부터 `setup.bat`):** 필수 프로그램을 확인하고, 패키지를 고정 버전으로 설치하고, 실패하면 종료 코드 1로 끝납니다. 다시 돌릴 때 Hermes 스킬 폴더가 겹치던 문제도 고쳤습니다.
- **`check_text_outputs.py`:** 아직 빌드하지 않은 초안은 건너뜁니다 (새 PC의 bmwx7 숏폼 등).
- **`longform_common.py`:** 한글 경로에서도 얼굴 마스크를 읽습니다 (`cv2.imdecode`).
- **`build_longform.py`:** FilmCraft가 없어도 CapCut 초안을 만듭니다 (11-06에 FilmCraft를 파이프라인에서 완전히 뺌).
- **`llm.py`:** agy를 `~/.gemini/bin`에서 못 찾으면 PATH에서 찾습니다.
- **`build_bmwx7_shorts.py`:** 고정 사용자 경로(python.exe, 글꼴, BGM)를 없앴습니다.
- **`gdrive_pipeline.py`·GUI:** 시나리오가 쓰는 영상이 없으면 Drive에서 자동으로 다시 받습니다 (`drive_index.missing_footage`).
- **`create_portable_release.py`:**
  - 포함: HANDOFF, DISTRIBUTION, docs, requirements, 런처 소스
  - 제외: 백업, 빌드 캐시, 토큰
  - 비밀값을 가립니다.
