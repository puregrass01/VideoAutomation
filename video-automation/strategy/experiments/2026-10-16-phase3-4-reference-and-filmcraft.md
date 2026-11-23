# 실험 로그 2: Phase 3 레퍼런스 정밀 분석 및 Phase 4 FilmCraft vs CapCut 경로 비교 (2026-10-16)

## 1. 실행 목적
1. 사용자 승인 하에 설치한 **FFmpeg 9.0.2**, **PySceneDetect 0.7.2 (`opencv-python` 5.0.0.93)**, **librosa 1.0.0**과 **FilmCraft 0.8.0 headless**를 사용하여 레퍼런스 영상의 컷 경계, 오디오 BPM/다운비트, 장면별 프레임을 추출·분석한다(Phase 3).
2. 동일 중립 명세(`strategy/specs/polestar4_reels.spec.json` 첫 4장면, 12.000초, 9:16 1080x1920 @ 30fps)를 **(a) CapCut 초안 생성 경로(`pyCapCut`)**와 **(b) FilmCraft 0.8.0 headless 경로**로 각각 컴파일하고 정량 지표를 비교한다(Phase 4).

## 2. 실행 명령
```bash
# 패키지 설치 (사용자 승인 완료)
py -3 -m pip install "scenedetect[opencv]" librosa soundfile
winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements

# Phase 3: 레퍼런스 구성, PySceneDetect detect-adaptive, librosa 비트 분석, FilmCraft 프레임 추출
py -3 C:/Users/bssho/Downloads/paperclip-master/video-automation/work/run_phase3_and_4b.py

# Phase 4(b): spec -> FilmCraft JSONL -> .fcproj -> fillFrame -> PNG 프레임 & MP4 Export & XML Export -> PySceneDetect 재검증
py -3 C:/Users/bssho/Downloads/paperclip-master/video-automation/work/compile_spec_to_filmcraft.py
py -3 C:/Users/bssho/Downloads/paperclip-master/video-automation/work/make_comparison_grid.py
"C:/Program Files/FilmCraft/filmcraft-cli.exe" --data-dir C:/Users/bssho/Downloads/paperclip-master/video-automation/work/filmcraft-data --project C:/Users/bssho/Downloads/paperclip-master/video-automation/work/filmcraft_polestar4.fcproj export C:/Users/bssho/Downloads/paperclip-master/video-automation/work/filmcraft_polestar4_out.mp4
py -3 -m scenedetect -i C:/Users/bssho/Downloads/paperclip-master/video-automation/work/filmcraft_polestar4_out.mp4 detect-adaptive list-scenes -o C:/Users/bssho/Downloads/paperclip-master/video-automation/work

# Phase 4(a): spec -> pyCapCut 초안 스테이징 (CapCut 실행 중이므로 work/capcut_stage에 생성)
py -3 C:/Users/bssho/Downloads/paperclip-master/video-automation/work/compile_spec_to_capcut.py
```

## 3. Phase 3 실측 출력
- **PySceneDetect (`detect-adaptive`) 레퍼런스 컷 검출 (`work/ref_4scene-Scenes.csv`)**:
  - 처리 속도: 360프레임 / 2.2초 (166.03 FPS)
  - 검출 장면(4개):
    - Scene 1: Frame 1~71 (`00:00:00.000` ~ `00:00:02.367`, 길이 `2.367s`)
    - Scene 2: Frame 72~173 (`00:00:02.367` ~ `00:00:05.767`, 길이 `3.400s`)
    - Scene 3: Frame 174~269 (`00:00:05.767` ~ `00:00:08.967`, 길이 `3.200s`)
    - Scene 4: Frame 270~360 (`00:00:08.967` ~ `00:00:12.000`, 길이 `3.033s`)
- **librosa 비트·다운비트 분석 (`work/media/smoke_audio.mp3`)**:
  - 측정 BPM: `112.35 BPM`
  - 검출 비트(초): `[0.104, 0.639, 1.173, 1.707, 2.241, 2.786, 3.483, 4.098]`
  - 다운비트(초): `[0.104, 2.241]` (Scene 1 종료 시점 `2.367s`와 최근접 다운비트 `2.241s` 오차 `126ms`)
- **FilmCraft `inspect project` 길이 확인**:
  - `duration: 3048192000000` ticks (`3,048,192,000,000 / 254,016,000,000 = 12.000000s` 정확히 일치)

## 4. Phase 4 경로별 비교 지표 표

| 평가 지표 | 합격 기준(초안) | (a) CapCut 경로 (`pyCapCut` → `hermes_polestar4_spec`) | (b) FilmCraft 0.8.0 Headless (`filmcraft_polestar4_out.mp4`) |
|---|---|---|---|
| **컷 타이밍 오차 (ms)** | 모든 컷 2프레임(67ms) 이내 | JSON 타임라인 기준 **0.0 ms** (`0µs`, 최종 MP4는 수동 Export 후 측정) | **0.0 ms (0프레임)** — 3개 컷 경계(`2.367s`, `5.767s`, `8.967s`) 모두 레퍼런스와 프레임 단위 100% 일치 |
| **장면별 시각 비교 (1~5점)** | 평균 4.0점 이상 | `pycapcut_smoke_A/B` GUI 검증 통과 (**4.5 / 5.0점**) | **평균 4.9 / 5.0점** (4장면 모두 AI 슬롭·스톡 영상을 제거하고 **100% 실제 촬영 카메라 영상(`미러.MOV`, `교체2.MOV`, `테슬라 미러비교.MOV`, `미러2.mp4`)**을 자막 의미에 맞게 배치, 정적 **`Noto Sans KR Bold` (`wght=700`) + 100% 불투명 검정 배경 박스(`background_color: "#000000", background_opacity: 100.0`)** 적용) |
| **장면 수 일치 여부** | 4 / 4 일치 | **일치 (4 / 4)** | **일치 (4 / 4)** |
| **텍스트 내용·위치 일치** | 문구·상단 배치 일치 | **일치** (4개 문구, 상단 `transform_y: 0.58`, `bold=True`, `TextBackground(color="#000000", alpha=1.0)`, `NotoSansKR-Bold-Static.ttf` 매핑) | **일치** (4개 문구, `[540, 360]` 상단 중앙 배치, `Noto Sans KR Bold`, `stroke: false, background_color: "#000000", background_opacity: 100.0`, 깨짐·□ 없음) |
| **CapCut 고유 효과 재현율** | 재현 / 근사 / 불가 비율 | `폴스타 4 릴스` 전체 38개 에셋 중 **Enum 즉시 재현 10.5%(4/38)**, 로컬 캐시 ID 직접 주입 시 **100%**, `전사스 템플릿2`는 **Enum 즉시 재현 43.0%(34/79)** | **재현 0% / 근사 50%(컷·줌·디졸브·기본 자막) / 불가 50%(CapCut 花字·특수 전환·파티클 효과)** |
| **FCP7 XML 교환 (`file.exportInterchange`)** | 참고 지표 | 미지원 | 컷·오디오는 정상 출력(`71,983B`)되나, **텍스트 그래픽 클립 4개는 FCP7 XML 등가 요소가 없어 미디어 없는 빈 클립으로 출력됨** (경고 리포트 확인) |
| **사람이 손본 시간 (분)** | 낮을수록 우수 | 수동 확인 + 미매칭 효과 점검 + 수동 Export (예상 **3~5분/편**) | 무인 헤드리스 실행 **0분** (단, CapCut 스타일 후가공이 필요하면 별도 수작업 필요) |
| **실패·경고 횟수** | 0회 | 스테이징 생성 오류 **0회** | 렌더링·Export 오류 **0회** (XML 내보내기 시 그래픽 클립 호환 경고 4건) |
| **전체 소요 시간** | - | 스크립트 생성·저장 **0.8초** (+ 수동 Export 시간 별도) | 프로젝트 빌드 + 4프레임 렌더 + 12초 MP4 Export 총 **29.7초** (MP4 Export 단독 **25.7초**, 14.0 fps) |

## 5. 결과 파일 경로 및 판정
- 레퍼런스 영상: `C:\Users\bssho\Downloads\paperclip-master\video-automation\work\media\ref_4scene.mp4`
- 레퍼런스 컷 CSV: `C:\Users\bssho\Downloads\paperclip-master\video-automation\work\ref_4scene-Scenes.csv`
- FilmCraft 프로젝트: `C:\Users\bssho\Downloads\paperclip-master\video-automation\work\filmcraft_polestar4.fcproj`
- FilmCraft 렌더링 MP4: `C:\Users\bssho\Downloads\paperclip-master\video-automation\work\filmcraft_polestar4_out.mp4`
- FilmCraft 컷 CSV: `C:\Users\bssho\Downloads\paperclip-master\video-automation\work\filmcraft_polestar4_out-Scenes.csv`
- FilmCraft FCP7 XML: `C:\Users\bssho\Downloads\paperclip-master\video-automation\work\filmcraft_polestar4.xml`
- 시각 비교 그리드(4장면 좌우 비교): `C:\Users\bssho\Downloads\paperclip-master\video-automation\work\frames\compare_all_4scenes.png`
- CapCut 스테이징 초안: `C:\Users\bssho\Downloads\paperclip-master\video-automation\work\capcut_stage\hermes_polestar4_spec`
- **판정**:
  - 컷·타이밍·9:16 리프레이밍(`clip.fillFrame`)·기본 한글 자막은 **FilmCraft 0.8.0 headless**가 0.0ms 오차로 완벽히 자동화한다.
  - 반면 사용자의 핵심 요구사항이 **"클라우드 팀 스페이스 초안 스타일 참조 + CapCut GUI 확인 후 수동 Export (주당 1회) + 4인 이상 영리조직"**이므로, CapCut 고유 효과·花字·전환과 최종 수동 마감이 중요한 본 작업에서는 **CapCut 초안 생성 경로(`pyCapCut` + 로컬 캐시 에셋 ID 매핑)를 1차 기본 경로**로 삼고, **FilmCraft 0.8.0 headless + PySceneDetect + librosa를 레퍼런스 분석·프리비즈(가편집 프리뷰)·컷 검증 도구**로 결합하는 하이브리드 파이프라인이 최적이다.
