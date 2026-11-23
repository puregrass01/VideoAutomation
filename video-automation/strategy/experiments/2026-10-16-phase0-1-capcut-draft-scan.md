# 실험 로그 1: Phase 0 초안 전수 분석 및 Phase 1 CapCut 9.6.0 홈 스캔 확인 (2026-10-16)

## 1. 실행 목적
1. `C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft` 내 35개 초안의 암호화 상태, 타임라인 구조, 미디어 유효성, `pyCapCut` 메타데이터(4,936개 `resource_id`) 매칭률 및 `is_vip` 비율을 정량 측정한다.
2. CapCut 9.6.0.4097 실행 시 스모크 테스트 초안(`pycapcut_smoke_A`, `pycapcut_smoke_B`)의 자동 인식 여부와 메타 파일(`draft_meta_info.json`, `root_meta_info.json`) 변화를 확인한다.

## 2. 실행 명령
```bash
py -3 C:/Users/bssho/Downloads/paperclip-master/video-automation/work/analyze_phase0.py
py -3 C:/Users/bssho/Downloads/paperclip-master/video-automation/work/extract_specs.py
```

## 3. 실측 결과 요약

### 3-1. 주요 초안별 `pyCapCut` Enum 매칭률 및 타이밍 정밀도
`pyCapCut`의 13개 메타데이터 Enum(`TransitionType`, `FilterType`, `FontType`, `TextIntro`, `TextOutro`, `TextLoopAnim`, `IntroType`, `OutroType`, `GroupAnimationType`, `VideoSceneEffectType`, `VideoCharacterEffectType`, `AudioSceneEffectType`, `MaskType`, 총 4,936개 `resource_id`) 대비 각 초안의 에셋 매칭률은 다음과 같다.

| 초안 이름 | 출처 분류 | 해상도 / 비율 / FPS | 길이(초) | 비디오 세그먼트 수 | 샘플 컷 길이(초) | 총 에셋 수 | `pyCapCut` 매칭 수 (비율) | `is_vip` 수 |
|---|---|---|---|---|---|---|---|---|
| `전사스 템플릿 1` | 팀 스페이스(평문) | 1920x1080 (`original`) @ 30fps | 84.70s | 12 | 18.767, 3.133, 3.033, 12.533 | 67 | 25 (**37.3%**) | 5 |
| `전사스 템플릿2` | 팀 스페이스(평문) | 1920x1080 (`original`) @ 30fps | 74.43s | 15 | 2.233, 2.200, 1.367, 2.933 | 79 | 34 (**43.0%**) | 2 |
| `전사스 템플릿3` | 팀 스페이스(평문) | 1920x1080 (`original`) @ 30fps | 99.73s | 12 | 16.500, 15.833, 3.433, 5.033 | 94 | 19 (**20.2%**) | 2 |
| `오사미 템플릿` | 팀 스페이스(평문) | 1920x1080 (`original`) @ 30fps | 65.13s | 0 (복합/하위) | - | 53 | 17 (**32.1%**) | 7 |
| `블랙사운드 스피커 템플릿` | 팀 스페이스(평문) | 1920x1080 (`original`) @ 30fps | 71.93s | 23 | 2.500, 3.667, 2.500, 3.233 | 34 | 8 (**23.5%**) | 7 |
| `옵틱글래스 광각미러 템플릿 1` | 팀 스페이스(**Timelines 16개 암호화**) | 1920x1080 (`original`) @ 30fps | 57.73s | 16 (루트 기준) | 4.667, 3.167, 2.233, 2.500 | 57 | 8 (**14.0%**) | 0 |
| `숏폼 영상 프로젝트 (1)/(2)` | 팀 스페이스(평문, 5 Timelines) | 1080x1920 (`9:16`) @ 30fps | 12.60~30.50s | 3 | 12.600 (트랙 중첩) | 1 | 1 (**100.0%**) | 0 |
| `폴스타 4 릴스` | **로컬 생성(평문)** | 1080x1920 (`9:16`) @ 30fps | 23.97s | 8 | 2.367, 3.400, 3.200, 4.300 | 38 | 4 (**10.5%**) | 2 |
| `미러비교(9대16)` | **로컬 생성(평문)** | 1080x1920 (`9:16`) @ 30fps | 13.50s | 16 | 1.867, 0.533, 4.300, 0.367 | 30 | 6 (**20.0%**) | 2 |
| `직관성(9대16)` | **로컬 생성(평문)** | 1080x1920 (`9:16`) @ 30fps | 21.57s | 12 | 2.200, 2.133, 3.767, 2.100 | 74 | 15 (**20.3%**) | 7 |
| `가족1(9대16)` | **로컬 생성(평문)** | 1080x1920 (`9:16`) @ 30fps | 20.03s | 7 | 4.067, 2.200, 2.000, 3.733 | 11 | 3 (**27.3%**) | 0 |
| `0729` | **로컬 생성(평문)** | 1080x1920 (`9:16`) @ 30fps | 17.40s | 8 | 5.500, 2.667, 2.333, 2.467 | 22 | 3 (**13.6%**) | 0 |

### 3-2. 미매칭 원인 분석
- `pyCapCut`의 메타데이터는 2025년 8월(`25-08`) 중국판 剪映 기준이므로, 2025년 하반기~2026년에 추가된 국제판 CapCut 에셋(`resource_id`가 `75...`, `76...`으로 시작하는 전환·비디오 이펙트·텍스트 애니메이션)과 텍스트 스타일 프리셋(`materials.effects`의 花字 `733...`~`757...`)은 `pyCapCut` 정적 Enum에 없다.
- 단, 로컬 평문 초안의 JSON 구조(`materials.effects`, `materials.transitions`, `materials.texts[].fonts`)를 그대로 보존하거나 `{resource_id, path}` 딕셔너리로 직접 주입하면 CapCut 로컬 캐시(`User Data\Cache\effect\<resource_id>`)와 연결된다.

### 3-3. CapCut 내 `Noto Sans KR` 캐시 확인
- 경로: `C:\Users\bssho\AppData\Local\CapCut\User Data\Cache\effect\7189852363404874242\4867c0fc2fd7265ca0c71e2f16e01ef2\NotoSansKR-Regular.otf` (4,744,692 bytes, 정적 OpenType 폰트)
- 매핑 구조: `materials.texts[].fonts` 배열 및 `content.styles[].font`에 `"id": "7189852363404874242"`, `"path": "C:/Users/bssho/AppData/Local/CapCut/User Data/Cache/effect/7189852363404874242/4867c0fc2fd7265ca0c71e2f16e01ef2/NotoSansKR-Regular.otf"` 형태로 주입 가능(GUI 열림 확인은 Phase 1 종료 후 확정).

### 3-4. Phase 1 최종 실측 결과 (CapCut 9.6.0.4097 열림·저장·평문 유지 완전 통과)
- **홈 화면 자동 인덱싱**: CapCut 9.6.0.4097 실행 시 `pycapcut_smoke_A`와 `pycapcut_smoke_B` 폴더를 즉시 감지해 `root_meta_info.json`(`all_draft_store`)에 등록하고 `draft_meta_info.json`을 평문 JSON(`{`)으로 보정함.
- **타임라인 편집기 열림 확인 (사용자 스크린샷 2장 실측)**:
  - **`pycapcut_smoke_A` (`6.7.0` / `140.0.0` 기본 마커)** 및 **`pycapcut_smoke_B` (`9.1.0` / `179.0.0` 로컬 마커)** 모두 `"unusual/unconventional path"` 또는 파일 손상 경고 **0건**, 미디어 다시 연결(relink) 요구 **0건**.
  - 두 초안 모두 4초(`00:00:04:00`) 타임라인에 트랙 3개(`text`, `video.mp4`, `audio.mp3`)가 정상 표시되고, 프리뷰 화면 하단에 노란색 한글 자막(`"9.6 테스트 A 기본"`, `"9.6 테스트 B 9.1 마커"`)이 정상 출력됨.
  - 단, 좌측 상단 미디어 빈(`모두`)에는 `audio.mp3`만 표시되었는데, 이는 `draft_meta_info.json`의 `draft_materials` 배열이 비어 있기 때문이며(`pyCapCut #13`), 타임라인 재생 및 편집에는 영향을 주지 않음.
- **열고 저장한 뒤 암호화 여부 점검 (`first_byte` 실측)**:
  - CapCut 9.6.0.4097이 두 초안과 신규 초안(`1016`)을 저장하면서 `last_modified_platform.app_version: "9.6.0"`, `new_version: "189.0.0"`, `os_version: "10.0.26300"`으로 갱신하고 `Timelines/<UUID>/draft_content.json`을 생성함.
  - **`pycapcut_smoke_A`, `pycapcut_smoke_B`, `1016` 모두 루트 `draft_content.json`과 `Timelines/<UUID>/draft_content.json`의 첫 바이트가 `b'{'`(평문 JSON)임을 확인함.** `draft_virtual_store.json` 내 `is_encrypted: true` 항목도 **0건**임.
  - **최종 판정**: **A 정상 (기본 출력 및 9.1 마커 모두 CapCut 9.6.0.4097에서 완벽 호환 및 평문 유지)**.

### 3-5. 글꼴 및 자막 스타일 규칙 보정 (`NotoSans_Condensed-Bold` + 외곽선 대신 배경 박스)
- 사용자 지정 폰트 `NotoSans_Condensed-Bold.ttf`(`C:\Users\bssho\AppData\Local\Microsoft\Windows\Fonts\NotoSans_Condensed-Bold.ttf`, 630KB, 글리프 4,503개)는 라틴/숫자 전용 정적 폰트(`nameID 1: Noto Sans Condensed`, `nameID 2: Bold`)이며, 한글은 `Noto Sans KR`(시스템 `NotoSansKR-VF.ttf` 또는 CapCut 캐시 `7189852363404874242` `NotoSansKR-Regular.otf`)이 담당한다.
- 텍스트 스타일은 **외곽선(`stroke: null` / `False`)을 쓰지 않고 반투명 배경 박스(`background: true` / `cc.TextBackground`)를 사용**한다. 이로써 FilmCraft에서 가변 글꼴(`NotoSansKR-VF.ttf`) 위에 두꺼운 외곽선이 겹쳐 획이 잠기던 현상까지 완전히 해결되었다.

## 4. 산출물 경로
- `C:\Users\bssho\Downloads\paperclip-master\video-automation\strategy\spec.schema.json`
- `C:\Users\bssho\Downloads\paperclip-master\video-automation\strategy\specs\polestar4_reels.spec.json`
- `C:\Users\bssho\Downloads\paperclip-master\video-automation\strategy\specs\jeonsas_template2.spec.json`
