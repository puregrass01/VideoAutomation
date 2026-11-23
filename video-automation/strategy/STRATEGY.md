# AI 영상 편집 자동화 최종 전략서 (`STRATEGY.md`)

> **작성일**: 2026-10-16  
> **대상 환경**: Windows 11 Pro (`10.0.26300`), CapCut `9.6.0.4097`, Python `3.14.7` (`pyCapCut` `@00e08e6`, `PySceneDetect 0.7.2`, `librosa 1.0.0`), FFmpeg `9.0.2`  
> **조직 및 운영 조건**: 4인 이상 영리조직, 주당 1회 제작, **사람 확인 후 수동 Export 허용**  
> **2026-11-06 결정**: FilmCraft 폐기 — 결과물은 CapCut 초안(롱폼·숏폼 모두 CapCut GUI에서 Export), 미리보기 MP4/9프레임 시트/숏폼 MP4 제거. 시각 검수는 배포된 CapCut 초안을 열어서 한다. 아래 FilmCraft 실측 수치는 기록으로만 남긴다.

---

## 1. 결론

**기본 경로는 「중립 편집 명세(`spec.json`) → `pyCapCut` 기반 CapCut 초안(`hermes_*`) 생성 → CapCut 데스크톱 GUI에서 사람이 최종 효과 검수 및 수동 MP4 Export」로 확정하며, 「PySceneDetect + librosa」는 레퍼런스 정밀 분석에 결합한다. (FilmCraft 0.8.0 Headless 프리뷰 검증 엔진은 2026-11-06 폐기.)**  
사용자의 제작 목표가 **주당 1회, 사람 확인 후 수동 Export**이므로 국제판 CapCut에 무인 Export API가 없다는 제약이 병목이 되지 않는다. 또한 4인 이상 영리조직이므로 유료 상업 라이선스가 필요한 Remotion(월 최소 $75~$100)을 도입할 필요가 없고, 알파 단계(실사용 준비도 56%)이며 CapCut 고유 효과(花字·스티커·특수 전환)를 재현하지 못하는 FilmCraft를 단독 마감 렌더러로 쓰는 리스크도 피할 수 있다. 대신 레퍼런스 영상의 컷·비트 추출(PySceneDetect·librosa)로 타임라인 수치를 먼저 확정한 뒤, `pyCapCut`으로 CapCut 초안을 생성해 사람이 3~5분 내로 마감·Export하는 구조가 품질·비용·안정성 면에서 가장 우수하다.

---

## 2. 파이프라인

### 2-1. 전체 단계 및 역할 분담

| 단계 | 입력 → 출력 | 사용 도구 | 담당 | 상세 동작 |
|---|---|---|---|---|
| **Step 1. 레퍼런스 & 소재 수집** | 참조 영상/초안 설명 + **실제 촬영 MP4/MOV/이미지** → `구글드라이브다운파일/media/` 사본 | 파일 시스템 복사 및 `vision_analyze` 장면-자막 매칭 검증 | **자동 (에이전트)** | **AI 생성 영상(`사이드미러가_좀더...`, `puregrass_*`, `kling_*`) 및 자막 내용과 무관한 스톡 영상(`smoke_video.mp4` 등) 사용 절대 금지.** 실제 촬영된 카메라 원본(`IMG_*.MOV`, `미러.MOV`, `교체2.MOV`, `테슬라 미러비교.MOV`, `미러2.mp4` 등)만 `구글드라이브다운파일/media/`로 복사하고 자막 의미와 장면 피사체 일치 여부를 검증 |
| **Step 2. 레퍼런스 정밀 분석** | 레퍼런스 MP4/오디오 → 컷 경계 CSV + BPM/다운비트 + 대표 프레임 PNG | `PySceneDetect 0.7.2` (`detect-adaptive`), `librosa 1.0.0`, `ffmpeg` 프레임 추출, `vision_analyze` | **자동 (에이전트)** | 컷 시작·종료 프레임(ms), BGM BPM 및 다운비트 그리드, 장면별 상·중·하단 텍스트 배치와 색상을 추출 |
| **Step 3. 중립 명세(`spec.json`) 생성 — 2026-11-16 폐기** | - | - | - | `extract_specs.py`를 지웠다. 지금은 차종별 시나리오(`work/scenarios/<slug>_longform.json`, 없으면 `make_scenario.py`)를 `build_longform.py`·`build_shorts.py`가 바로 CapCut 초안으로 만든다. |
| **Step 4. 프리비즈(Pre-viz) 검증 — 2026-11-06 폐기** | - | - | - | FilmCraft 프리뷰 MP4·9프레임 시트를 만들지 않는다. 시각 검수는 Step 6에서 배포된 CapCut 초안을 열어 한다. |
| **Step 5. CapCut 초안 컴파일** | 시나리오 JSON → `com.lveditor.draft/hermes_<이름>` | `pyCapCut` (`fix/template-mode-data-loss` `@00e08e6`) | **자동 (에이전트)** | **CapCut 종료 상태(`CapCut.exe` 프로세스 0개) 및 버전(`9.6.0.4097`) 확인 후** 로컬 최신 플랫폼 마커(`9.1.0` / `new_version: 179.0.0`), `ratio: "9:16"`, 로컬 캐시 `NotoSansKR-Regular.otf`(`id: 7189852363404874242`)를 주입해 초안 생성 |
| **Step 6. 검수 및 최종 Export** | `hermes_<이름>` 초안 → 최종 납품용 `.mp4` | CapCut Desktop GUI (`9.6.0.4097`) | **사람 (수동 마감)** | `needs_review`에 표시된 최신 CapCut 고유 이펙트·전환·Pro 에셋을 GUI에서 확인·보정하고 수동 Export 수행 (주당 1회, 편당 약 3~5분) |

### 2-2. `.md` / 참조 초안 → `spec.json` 변환 규칙 (적용 순서)
1. **캔버스 정규화**: 해상도(`w`, `h`)와 `fps`(기본 30.0)를 읽고 `aspect`(`"9:16"`, `"16:9"`, `"4:5"`)를 명시한다(`pyCapCut` `dumps()`가 `ratio`를 `"original"`로 덮어쓰는 버그를 후처리에서 복원).
2. **타이밍 병합 및 스냅**: 장면 시작(`start`)과 길이(`dur`)는 초(float, 소수점 3자리 ms 단위)로 기록한다. 레퍼런스 영상이 있으면 `PySceneDetect` `detect-adaptive`의 컷 경계를 우선 적용하고, 음악 중심 구간은 `librosa` 다운비트(`downbeats_s`)와 150ms 이내일 때 스냅(`snap: "downbeat#N"`)한다.
3. **글꼴 및 자막 배경 규칙 (10장 및 사용자 보정 반영)**:
   - 한글 기본 `font`는 정적 Bold로 인스턴스화한 **`"Noto Sans KR Bold"`**(`C:\Users\bssho\AppData\Local\Microsoft\Windows\Fonts\NotoSansKR-Bold-Static.ttf`, `wght=700`, 6.22MB), 영문·숫자 보조 글꼴(`latin_font`)은 **`"NotoSans_Condensed-Bold"`**(`C:\Users\bssho\AppData\Local\Microsoft\Windows\Fonts\NotoSans_Condensed-Bold.ttf`, 4,503 글리프)로 지정한다.
   - **텍스트 외곽선(`stroke`)은 사용하지 않고(`stroke: null` / `False`), 불투명 검정 배경 박스(`background: {"enabled": true, "color": "#000000", "alpha": 1.0, "radius": 0.14}` / CapCut `cc.TextBackground(color="#000000", alpha=1.0)`)를 기본 스타일로 적용한다.** 이로써 가변 글꼴(`NotoSansKR-VF.ttf`)의 가는 획 문제와 가시 모양 깨짐 현상이 모두 완전히 해결되었다.
4. **AI Slop 차단 · CapCut 클라우드 템플릿 임포트 · 사이드미러 전체 노출(`Full sidemirror had to be shown`) 규칙**:
   - 생성형 AI 클립(예: 대시캠 합성 영상, `puregrass_*`, `kling_*`)이나 자막 문맥과 무관한 스톡 클립(`smoke_video.mp4` 등)은 슬롯 매핑에서 즉시 차단한다.
   - 로컬 경로가 유실된 경우 CapCut 클라우드 캐시 폴더(`.cloud_cache_7327546324319568897/광각미러 템플릿1-복사/materials/video/` 등) 및 실제 촬영 원본(`IMG_3294.MOV`, `IMG_3270.MOV`, `IMG_3285.MOV`, `테슬라 미러비교.MOV`)에서 템플릿의 실제 사용 구간(`source_timerange`)을 가져온다.
   - **사이드미러 전체 노출 필수 (`Full sidemirror had to be shown` / `full side mirror img had to be shown`)**: 사이드미러가 주제인 모든 장면(단독 시야 비교 컷 `s08, s13, s14`, 50:50 좌우/상하 분할 비교 컷 `s15, s16`, 숏폼 `s01~s04`)에서 사이드미러의 좌·우·상·하 끝단(거울면 및 베젤/하우징 외곽)이 프레임 경계에 잘리는 프레이밍을 엄격히 금지한다. 원본 4K(`3840×2160` 또는 `2160×3840`) 영상을 단독 `16:9`(`1920×1080`), 50:50 좌우 분할 `8:9`(`960×1080`), 또는 숏폼 `9:16`(`1080×1920`)으로 크롭할 때는 반드시 미러 전체 폭과 높이에 여유 마진을 둔 크롭 영역(예: `crop=2560:1440:640:700`, `crop=1520:1710:...`, `crop=1840:2070:...` 등)을 지정하여 **시공 전·후 모든 패널에서 사이드미러 하우징과 거울면 전체(100%)가 화면 안에 온전히 들어오도록** 검증한다. 크롭 영역 확대로 인해 상단 배경에 작업자/촬영자의 얼굴이 함께 잡힐 경우에는 미러를 잘라내지 않고 **솔리드 블랙 원형 마스크(`구글드라이브다운파일/media/face_mask_circle.png`)**로 얼굴만 정밀 마스킹한다.
5. **CapCut 에셋 매칭 및 `needs_review` 분류**:
   - 전환·비디오 효과·텍스트 애니메이션은 한국어 표시 이름이 아닌 `resource_id`(또는 `effect_id`)를 우선 키로 삼아 `pyCapCut`의 13개 메타데이터 Enum(4,936개 항목)에서 검색한다.
   - Enum에 매칭되면 `capcut: {"enum": "...", "resource_id": "...", "is_vip": ...}`를 기록한다.
   - Enum에 없거나(`25-08` 이후 추가된 `75...`/`76...` ID 및 花字 `materials.effects`) `is_vip == true`인 항목은 `capcut.unmatched = true` 또는 `null`로 두고 장면의 `needs_review` 배열에 `"<종류>:<이름>(<resource_id>)"` 형태로 반드시 등록한다.
6. **영상 편집 검수 시 전체 영상 탐색 금지 — `cli-anything-capcut` 기반 `O(1)`/`O(log N)` 타겟 검수 (`Check Video Edits Using /cli-anything-capcut, Not Searching Whole Video`)**:
   - 영상 편집 결과물(CapCut 초안 `draft_content.json`, 클립 배치, 타임스탬프, 자막 오버레이, 전환, BGM 커버리지 등)을 검수할 때 전체 비디오를 처음부터 끝까지 디코딩·탐색하지 않는다.
   - 반드시 `cli-anything-capcut` (`capcut/agent-harness/cli_anything/capcut/capcut_cli.py`)의 인덱싱된 CLI 명령어를 사용하여 **`O(1)` ID/씬 이름 조회**(`media list --id s16`) 및 **`O(log N)` 타임스탬프 이진 탐색(`bisect`) 조회**(`media list --at 34.9s`, `text list --at 35.0s`)로 필요한 구간만 즉시 검증한다:
     - `cli-anything-capcut --json --project <draft_content.json> project validate` (전체 타임라인 무결성·해상도·세그먼트 수 검증)
     - `cli-anything-capcut --json --project <draft_content.json> media list --at <timestamp>` (`O(log N)` `bisect`로 특정 시점의 활성 비디오/오디오/텍스트 세그먼트만 즉시 조회)
     - `cli-anything-capcut --json --project <draft_content.json> media list --id <scene_id>` (`O(1)`로 특정 씬 클립의 경로·소스 구간·트랜스폼·전환 즉시 조회)
     - `cli-anything-capcut --json --project <draft_content.json> text list --at <timestamp>` (`O(log N)`으로 특정 시점의 자막 문구·좌표·폰트 크기 즉시 조회)

---

## 3. 렌더러 결정 근거 (Phase 0 · Phase 1 · Phase 3 · Phase 4 실측 표)

### 3-1. 후보 렌더러 종합 평가 및 라이선스 판정
| 후보 | 로컬 실행 실측 | 템플릿 효과 재현 | 무인 MP4 Export | 4인 이상 영리조직 라이선스 비용 | 최종 판정 |
|---|---|---|---|---|---|
| **CapCut 9.6 + `pyCapCut` (`@00e08e6`)** | 초안 생성 0.8s, **CapCut 9.6.0.4097에서 `pycapcut_smoke_A`(6.7 마커)와 `pycapcut_smoke_B`(9.1 마커) 모두 경고 없이 정상 열림 및 저장 후 루트·`Timelines/` 모두 평문 JSON(`{`) 유지 실측 완료** | **최상** (Enum 4,936개 + 로컬 캐시 `resource_id` 직접 주입 가능) | 불가 (사람이 GUI에서 수동 Export) | `pyCapCut` 무료(단, 저장소 LICENSE 미기재로 내부 도구로만 사용) / CapCut 상업용 에셋 약관 준수 필요 | **1차 메인 경로 채택** (주 1회 수동 Export 조건에 부합) |
| **FilmCraft `0.8.0` Headless CLI** | 9:16 12초(4장면+한글자막+오디오) 빌드·MP4 Export **25.7초** 성공, 컷 타이밍 오차 **0.0ms** | **낮음** (컷·리프레이밍·기본 자막·디졸브만 가능, CapCut 花字·특수 효과 불가) | **가능** (`filmcraft-cli export`) | **무료** (`MIT OR Apache-2.0`) | **2026-11-06 폐기** (이전: 레퍼런스 프레임 추출·프리비즈 검증 보조 경로) |
| **FilmCraft XML → Premiere Pro 2021** | `file.exportInterchange`로 FCP7 XML(`71,983B`) 생성 성공 (Premiere 2021 열림은 미검증) | **주의**: 실측 결과 `graphics.newText` 자막 클립이 FCP7 XML에서 미디어 없는 빈 클립으로 빠져 자막 재작업 발생 | 불가 (Premiere 수동 Export) | 이미 설치됨 | **2026-11-06 공식 폐기** (구현이 `work/_retired/`에만 있어 동작하지 않음) |
| **Remotion `4.0.535`** | `my-video/`에 골격만 있고 `node_modules` 미설치 (실행 가능 설치 없음) | 코드로 재구현 필요 | 가능 (`npx remotion render`) | **유료 필수** (4인 이상 영리조직은 Creators 좌석당 $25/월[최소 3석 $75/월] 또는 Automators 월 최소 $100) | **제외** (주 1회 제작에 유료 라이선스 및 React 재구현 비용 과다) |
| **cli-anything-capcut `v0.5.7`** | 미설치 (코드 리뷰 완료) | `pyCapCut` 래퍼이나 레시피 ID 무시, `duration: "auto"`→`0µs`, 해상도/fps 무시, fade 인자 버그 존재 | 국제판 불가 (`render-headless`는 효과 유실) | MIT | **제외** (`pyCapCut` 직접 스크립트가 더 정확하고 안전함) |
| **CapCut MCP (VectCutAPI 등)** | 미설치 | 템플릿 로드·교체 없음, 구버전 마커(`6.5.0/mac`) 하드코딩 | 유료 비공개 클라우드 | Apache-2.0 (코어만) | **도입 금지** (6장 결정 원칙) |

### 3-2. Phase 4 동일 Spec(`polestar4_reels.spec.json` 4장면, 12.0초) 비교 실측 표
- 2026-10-16 실측 기록이다. (b) FilmCraft 경로는 2026-11-06에 폐기했다.
- 실험 상세 로그: `strategy/experiments/2026-10-16-phase3-4-reference-and-filmcraft.md`
- 시각 비교 이미지: `구글드라이브다운파일/frames/compare_all_4scenes.png`

| 비교 항목 | 합격 기준 | (a) CapCut 경로 (`work/capcut_stage/hermes_polestar4_spec`) | (b) FilmCraft 0.8.0 Headless (`work/filmcraft_polestar4_out.mp4`) |
|---|---|---|---|
| **컷 타이밍 오차 (`PySceneDetect`)** | ≤ 67ms (2프레임) | 타임라인 데이터 기준 **0.0 ms** (최종 MP4는 수동 Export 후 확정) | **0.0 ms (0프레임)** — `2.367s`(71f), `5.767s`(173f), `8.967s`(269f), `12.000s`(360f) 완전 일치 |
| **장면별 시각 점수 (1~5점)** | 평균 ≥ 4.0점 | **`pycapcut_smoke_A/B` GUI 검증 통과 (4.5 / 5.0점)** | **평균 4.9 / 5.0점** — 4장면 모두 **100% 실제 촬영 카메라 영상(`미러.MOV`·`교체2.MOV`·`테슬라 미러비교.MOV`·`미러2.mp4`)**을 자막 의미에 맞게 배치하고, 정적 **`Noto Sans KR Bold` (`wght=700`) + 100% 검정 배경 박스(`#000000`, `opacity: 100%`)**를 적용해 시인성과 진정성 확보 |
| **장면 수 일치** | 4 / 4 | **4 / 4 일치** | **4 / 4 일치** |
| **텍스트 내용·위치 일치** | 문구 일치·상단 배치(2026-10-16 사용자 요청) | **일치** (4개 문구, 상단 `y=0.58`, `bold=True`, `TextBackground(color="#000000", alpha=1.0)`, `NotoSansKR-Bold-Static.ttf` 연결) | **일치** (4개 문구, 상단 중앙 `[540, 360]`, `Noto Sans KR Bold`, `stroke: false, background_color: "#000000", background_opacity: 100.0` 적용) |
| **CapCut 고유 효과 재현율** | 재현 / 근사 / 불가 | 로컬 초안 12종 평균 Enum 매칭 **24.6%** (`전사스 템플릿2` **43.0%**, `폴스타 4 릴스` **10.5%**). 단, 로컬 캐시 `resource_id` 직접 주입 시 **100% 호환 가능(미검증)** | **재현 0% / 근사 50% / 불가 50%** |
| **사람 수작업 시간** | - | 편당 **약 3~5분** (`needs_review` 효과 확인 + 수동 Export) | **0분** (무인 Export 완료, 단 CapCut 고유 룩앤필은 미적용) |
| **실패·경고 횟수** | 0회 | **0회** | MP4 렌더 **0회** (FCP7 XML 내보내기 시 자막 미지원 경고 4건) |
| **전체 실행 시간** | - | 초안 생성 **0.8초** (+ 수동 Export 별도) | 총 **29.7초** (JSONL 빌드 + 4프레임 PNG + 12초 MP4 Export 25.7초) |

---

## 4. 템플릿 유형별 라우팅 규칙

| 템플릿 유형 | 판별 기준 (`spec.json` 기준) | 기본 렌더러 경로 | 마감 방식 |
|---|---|---|---|
| **유형 A: CapCut 효과·花字 집중형 (기본)** | 전환·비디오 이펙트·텍스트 애니메이션·스티커가 장면당 1개 이상이거나, 팀 스페이스/로컬 쇼츠 템플릿(`폴스타 4 릴스`, `미러비교`, `직관성`, `전사스 템플릿 1~3`)을 따르는 경우 | `spec.json` → `pyCapCut` 생성기 → `hermes_<이름>` 초안 | **CapCut GUI에서 사람이 `needs_review` 점검 후 수동 Export** |
| **유형 B: 컷·단순 자막 중심형** | CapCut 고유 효과가 없거나 단순 컷+하단 자막+BGM 구성인 경우 | `spec.json` → `pyCapCut` 생성기 → `hermes_<이름>` 초안 (FilmCraft 경로는 2026-11-06 폐기) | **CapCut GUI에서 수동 Export** |
| **유형 C: CapCut 호환성 차단 시** | CapCut이 10.x로 자동 업데이트되어 외부 초안을 손상으로 거부하거나, Phase 1에서 스모크 초안 A·B·Shell 주입이 모두 실패한 경우 | CapCut 초안 쓰기를 중단하고 사용자에게 보고 (FilmCraft → FCP7 XML → Premiere 비상 경로는 구현이 `work/_retired/`에만 있어 2026-11-06 공식 폐기) | 사용자 결정 |

---

## 5. 자동화 경계 표

| 작업 영역 | 자동 (에이전트 단독 수행) | 반자동 (에이전트 후보 생성 + 사람 확인) | 사람 필수 (수동 수행) |
|---|---|---|---|
| **레퍼런스 분석** | `PySceneDetect` 컷 경계(ms) 검출, `librosa` BPM·다운비트 추출, `ffmpeg` 프레임 추출 | 비전 모델(`vision_analyze`)을 통한 텍스트 위치·색상·전환 종류 추정 (`confidence` 점수 부여) | 암호화된 팀 스페이스 초안의 실제 타임라인 구성 확인 (복호화 금지) |
| **명세(`spec.json`) 작성** | 장면 분할, 시간 단위 변환(초 ↔ `µs` / `tick`), `Noto Sans KR` 기본 스타일 지정 | `pyCapCut` Enum에 없는 신규 `resource_id`(`75...`/`76...`) 및 `is_vip` 에셋의 대체 후보 지정 (`needs_review`) | 브랜드 카피 최종 감수, Pro(`is_vip`) 유료 에셋 사용 여부 결정 |
| **타임라인 생성** | `구글드라이브다운파일/media/` 소재 복사, `pyCapCut`으로 트랙·세그먼트·키프레임·캐시 폰트 주입 | 9:16 크롭 시 피사체 중심축(`anchor` / `transform`) 미세 보정 | **CapCut 종료 상태에서 생성된 `hermes_*` 초안을 CapCut GUI에서 열기** |
| **마감 및 Export** | 초안 생성 전 `CapCut.exe` 실행 여부 및 앱 버전(`9.6.0.4097`) 자동 점검 | - | **CapCut GUI에서 미매칭 효과(`needs_review`) 적용 및 최종 MP4 Export** |

---

## 6. 운영 가드레일

1. **CapCut 실행 중 초안 쓰기 절대 금지**:
   - 생성 스크립트는 실행 직전 반드시 `tasklist /FI "IMAGENAME eq CapCut.exe" /NH /FO CSV`에서 `CapCut.exe` 개수가 `0`인지 확인한다(현재 10개 프로세스 실행 중이므로 `work/capcut_stage/`에만 스테이징하고 `com.lveditor.draft`에는 쓰지 않음).
   - `com.lveditor.draft`에는 오직 `hermes_` 또는 `pycapcut_smoke_` 접두사로 시작하는 새 폴더만 생성하며, 기존 35개 초안은 읽기 전용으로 보호한다.
2. **CapCut 버전 감지 및 업데이트 직후 스모크 테스트 절차**:
   - 초안 생성 전 `C:\Users\bssho\AppData\Local\CapCut\Apps` 하위 폴더 중 최고 버전을 확인한다.
   - `9.6.0.4097`보다 높은 버전이 감지되면 작업을 중단하고 스모크 테스트(`hermes_smoke` 최소 초안 생성 → 사람 GUI 열림·경고 확인 → 저장 → `draft_content.json` 및 `Timelines/*/draft_content.json` 첫 바이트 `{` 여부 점검)를 다시 수행한다.
   - 특히 **`10.x` 버전 폴더가 감지되면 즉시 CapCut 초안 쓰기를 중단**하고 사용자에게 보고한다(외부 초안 손상 거부 위험).
   - 버전 감시 자동화 설계(생성 시 별도 승인 필요): `C:\Users\bssho\AppData\Local\hermes\scripts\check_capcut_version.py`를 Hermes cron `no_agent` 스크립트로 두어 `Apps` 폴더 목록이 직전 스냅샷과 달라졌을 때만 알림을 출력하도록 설계한다.
3. **부분 암호화(`Timelines/`) 및 클라우드 초안 오용 방지**:
   - `옵틱글래스 광각미러 템플릿 1`처럼 루트 `draft_content.json`은 평문(`{`)이나 `Timelines/*/draft_content.json` 16개가 암호화된 초안은 루트만 읽으면 구버전 스냅샷을 쓰게 되므로, 모든 `Timelines/*/draft_content.json`의 첫 바이트가 `{`인지 함께 검사한다.
   - 클라우드 팀 스페이스(`tm_draft_cloud_space_id: 7327545136085664770`)에서 내려받은 초안은 `duplicate_as_template` 원본으로 직접 복제하지 않고, 중립 `spec.json`으로 편집 문법만 추출해 새 초안을 생성한다.
4. **FilmCraft 폐기 (2026-11-06)**:
   - FilmCraft는 설치·실행하지 않는다. 시각 검수는 배포된 CapCut 초안을 GUI에서 열어 한다.

---

## 7. 리스크와 완화책

| 리스크 요인 | 상세 내용 (실측 근거) | 완화책 |
|---|---|---|
| **1. CapCut 9.6 저장 후 암호화 가능성** | 9.6.0 홈 화면 스캔 시 `draft_meta_info.json`은 평문(`{`)으로 저장됨을 확인했으나, 타임라인 편집 후 저장 시 `draft_content.json`을 암호화하는지는 미검증 | 암호화되더라도 `spec.json`이 원본(Source of Truth)이므로 CapCut 초안은 **"일회성 출력물(Write-once)"**로 취급하고, 수정이 필요하면 `spec.json`에서 재생성한다. |
| **2. `pyCapCut` 메타데이터 노후화 (`25-08`)** | 로컬 초안 12종 실측 결과, `75...`/`76...` 신규 효과 및 花字(`materials.effects`) 때문에 정적 Enum 매칭률이 10.5%~43.0%에 그침 | ① 자주 쓰는 한국어/신규 효과의 `{resource_id, effect_id, path}` 사전을 로컬 평문 초안(`0729`, `직관성`, `미러비교`, `폴스타 4 릴스`)에서 추출해 스니펫 테이블로 관리하거나, ② `needs_review`로 분리해 사람이 GUI 마감 시 클릭 1~2회로 적용한다. |
| **3. 기존 초안의 원본 미디어 경로 유실** | `0729`, `미러비교`, `직관성` 등이 참조하던 `OneDrive/바탕 화면/영상컨텐/*` 파일들이 현재 디스크에 없음 (`exists=False`) | 모든 신규 자동화 작업은 입력 소재를 `구글드라이브다운파일/media/` 아래로 먼저 복사·검증한 뒤 절대 경로로 주입한다. |
| **4. FilmCraft 가변 글꼴(`NotoSansKR-VF.ttf`) 렌더링 한계** (2026-11-06 FilmCraft 폐기로 해당 없음, 기록용) | Windows 기본 `NotoSansKR-VF.ttf` 사용 시 `Regular`는 가장 가는 굵기로 나오고 `Bold`는 자소 끝에 가시 모양 깨짐 발생 | 프리비즈에서는 `Regular` + 외곽선(`stroke_width: 6`) 조합으로 깨짐 없이 가독성을 확보(실측 확인 완료)하고, 필요 시 Google Fonts 정적 `NotoSansKR-Bold.ttf`를 시스템에 추가 설치한다. |
| **5. 소프트웨어 및 에셋 라이선스 리스크** | ① **Remotion**: 4인 이상 영리조직 유료 → **미사용으로 리스크 제거**.<br>② **pyCapCut**: GitHub 저장소에 LICENSE 파일이 없음.<br>③ **CapCut 내장 에셋**: 약관 10조에 따라 외부 렌더러 반출 금지. | ① `pyCapCut`은 외부 배포·SaaS화하지 않고 사내 로컬 스크립트로만 사용한다.<br>② CapCut 내장 폰트(`7189852363404874242`)·음원·효과는 CapCut 초안 내부에서만 참조하고, CapCut 밖 처리(ffmpeg 클립 인코딩 등)에는 시스템 폰트(`Noto Sans KR`)와 자체 오디오만 사용한다. |

---

## 8. 미해결 질문 및 추후 확인 항목 (해결 완료)

Phase 1 스모크 테스트(`pycapcut_smoke_A`, `pycapcut_smoke_B`)와 구현 계획 실행을 통해 기존 미해결 항목이 모두 해결되었습니다:
1. **CapCut 9.6.0.4097 평문 호환성 실측 완료**: 도구 생성 초안을 경고 없이 열고, 저장 후에도 루트 `draft_content.json`과 `Timelines/<UUID>/draft_content.json`을 모두 평문(`{`, `new_version: "189.0.0"`)으로 유지함을 확인했습니다.
2. **`draft_meta_info.json`의 `draft_materials` 채우기 (`pyCapCut #13`) 해결 완료**: `work/compile_spec_to_capcut.py`의 `populate_draft_materials()`에서 비디오 소재(`metetype: "video"`, 4개)와 오디오 소재(`metetype: "music"`, 1개)의 `local_material_id` 및 `draft_materials[0].value`를 양방향 연결하여 CapCut 좌측 상단 미디어 빈(`모두`)에 모든 비디오·오디오 클립이 정상 노출되도록 보강했습니다.
3. **신규 초안(`hermes_polestar4_fullmirror`) 배포 완료**: `CapCut.exe` 종료(`0`개 프로세스) 및 버전(`9.6.0.4097`) 확인 후, 기존 폴더 덮어쓰기 없이 `com.lveditor.draft/hermes_polestar4_fullmirror`로 안전하게 배포 완료했습니다.

---

## 9. 2주 실행 계획 및 구현 완료 현황

| 주차 / 단계 | 실행 과제 | 구현 산출물 및 완료 현황 | 필요한 사용자 승인 / 개입 |
|---|---|---|---|
| **1주차 전반 (Day 1~2)** | **Phase 1 & 4(a) CapCut 9.6 GUI 실측 및 `draft_materials` 보강** | **완료** — `work/compile_spec_to_capcut.py`에 `populate_draft_materials()` 적용(`videos_in_media_bin: 4`, `audios_in_media_bin: 1`), `com.lveditor.draft/hermes_polestar4_fullmirror` 배포 완료 | CapCut GUI에서 `hermes_polestar4_fullmirror` 열기 및 수동 Export 확인 |
| **1주차 후반 (Day 3~5)** | **자주 쓰는 로컬 효과·花字 스니펫 사전 구축** | **완료** — `work/build_asset_catalog.py` 작성 및 실행, 로컬 평문 초안 45종에서 전환 44개·비디오 이펙트 46개·텍스트 효과(花字) 127개·애니메이션 141개를 추출해 `work/capcut_asset_catalog.json` 구축 완료 | 불필요 (읽기 전용 추출 완료) |
| **2주차 전반 (Day 6~8)** | **주 1회 제작용 원클릭 CLI 파이프라인 완성** | **완료 후 폐기** — `work/build_weekly.py`(Polestar4 파일럿: 프리플라이트 → `spec.json` 검증 → FilmCraft 프리뷰 → CapCut 초안)는 2026-11-06 FilmCraft와 함께 삭제. 지금 실행 진입점은 `work/gdrive_pipeline.py`(GUI) / `work/build_longform.py <slug>` | 결과 초안 CapCut GUI 검수 및 수동 Export (주 1회, 3~5분) |
| **2주차 후반 (Day 9~10)** | **CapCut 버전 감시 및 안전 프리플라이트 스크립트** | **완료** — `work/preflight_check.py` 및 버전 스냅샷(`work/capcut_version_snapshot.json`) 구현 완료. `CapCut.exe` 실행 여부, `Apps/` 최고 버전(`9.6.0.4097`), `10.x` 차단, 루트·`Timelines/` 평문(`{`) 검사, AI Slop 미디어 차단 목록 검사를 자동 수행 | 선택 사항: Hermes cron 자동 알림 등록 시 사용자 승인 |

---

## 10. 롱폼(`16:9`) vs 숏폼(`9:16`) 템플릿 엄격 분리 아키텍처

> **배경 (2026-10-19 사용자 피드백 반영)**: 롱폼 영상을 제작할 때 숏폼(`폴스타 4 릴스` 등 `9:16` 릴스/쇼츠) 템플릿의 자막 규칙(불투명 검정 배경 박스 `bg_style=1`)이나 세로형 클립(`1080×1920`)을 혼용하면 롱폼 고유의 영상미가 깨지고 숏폼처럼 보이는 문제가 발생한다. 이에 따라 **명세 디렉토리(`strategy/specs/shortform/` vs `strategy/specs/longform/`)와 시각 문법·빌더를 완전히 분리**한다.

| 구분 항목 | 숏폼 템플릿 (`shortform` — 릴스 / 쇼츠) | 롱폼 템플릿 (`longform` — 옵틱글래스 공식 유튜브/블로그 롱폼) |
|---|---|---|
| **대표 레퍼런스 초안** | `폴스타 4 릴스`, `미러비교`, `직관성`, `전사스 템플릿 1~3` | `광각미러 템플릿1-복사`, `옵틱글래스 광각미러 템플릿 1`, `26 폴스타4 옵틱 [26.03.13]` |
| **명세 경로 (`spec.json`)** | `strategy/specs/shortform/<이름>.spec.json` | `strategy/specs/longform/<이름>.spec.json` |
| **캔버스 및 길이** | `1080×1920` (`9:16` 세로형), `12.0s ~ 25.0s` (4~8컷 빠른 호흡) | `1920×1080` (`16:9` 가로형), `52.0s ~ 58.0s` (6파트 스토리텔링 구조) |
| **자막 배경 박스 (`background`)** | **불투명 검정 배경 박스 필수** (`bg_style: 1`, `#000000`, `alpha: 1.0`, `stroke: false`) | **검정 배경 박스 절대 사용 금지 (`bg_style: 0`, `background: false`)** — **인트로 및 섹션 타이틀은 외곽선 없는 순백색 `Paperlogy 7 Bold`(`stroke: false`, `shadow: false`)**를 사용하며, 본문 내레이션만 외곽선(`stroke: #000000`) 사용 |
| **자막 배치 위치** | 상단 중앙 고정 (`transform_y: 0.58` / 픽셀 좌표 `[540, 360]`) | **모든 자막 엄격한 가로 중앙 정렬(`font Center align`)**: 하단 2줄 내레이션 모두 `x=960` (CapCut `transform.x: 0.0`, `alignment: 1`, 앞뒤 공백 제거), 50:50 좌·우 상단 분할 라벨은 각 패널 중앙(`시공 전` `x=480` / `transform.x: -0.5`, `시공 후` `x=1440` / `transform.x: +0.5`)에 정확히 정렬 |
| **롱폼 전용 6파트 구조** | 해당 없음 (즉각적인 Hook → 시공 → 결과 4컷) | **Part 1 (`0~12.1s`)**: 차량 외관·미러 16:9 B-Roll + **브랜드 공식 로고(`Tesla Logo.png`) + 제조사 명시 단일 심플 인트로 타이틀 (`2026 테슬라 사이버트럭`, `Paperlogy 7 Bold` 화이트, 무외곽선 — `TESLA CYBERTRUCK` 등 영문 중복 표기 제거)**<br>**Part 2 (`12.1~14.7s`)**: 실사 미러 영상 위 섹션 타이틀 (`BY OPTICGLASS` + `광각미러가 꼭 필요한 이유` + 사선 `╱`, `Paperlogy 7 Bold` 화이트, 무외곽선)<br>**Part 3 (`14.7~26.2s`)**: 문제 제기 (`순정미러의 좁은 시야` + 2줄 중앙 정렬 외곽선 자막 `운행 시 차선 확인 어려움!`, `초보운전자에게는 특히나 치명적인 좁은 시야! / 혼잡한 도로에서 사고 발생 확률 UP!!`, `운전고수도 무시할 수 없는 사각지대!`)<br>**Part 4 (`26.2~31.6s`)**: 광각 솔루션 (`옵틱글래스 광각미러로 한방에 해결!`, `사각지대 해소 가능한 넓은 시야, / 편리해진 차선/주차라인 확인`)<br>**Part 5 (`31.6~37.8s`)**: 16:9 **단독 및 50:50 좌우 분할 비교** (`시공 전` 순정 미러 **밝은 원본 컬러** 100% 노출 vs `시공 후` 옵틱글래스 광각미러 **밝은 원본 컬러** 100% 노출 — **인위적 흑백 처리 금지**)<br>**Part 6 (`37.8~41.5s`)**: **옵틱글래스 광각미러 공식 아웃트로(`C:\Users\bssho\OneDrive\문서\카카오톡 받은 파일\아웃트로\아웃트로\옵틱글래스 광각미러 아웃트로.mp4`) 고정 적용** 및 CapCut 미디어 보관함 전체 등록 |
| **클립 선정 및 프레이밍 원칙** | ① **사이드미러 전체 노출 필수 (`Full sidemirror had to be shown`)**: 16:9 원본을 9:16(`1080×1920`) 또는 상하 50:50 분할(`1080×960`)로 크롭할 때 사이드미러의 좌·우·상·하 하우징과 거울면이 단 1%도 잘리지 않고 **100% 전체 노출**되도록 크롭 폭·위치를 설정한다.<br>② **시공 전·후 비교 컷 화살표 이펙트 4개 고정 (`arrow effects had to be 4` & `arrow effect example`)**: `시공 후` 사이드미러 베젤/테두리(상·하·좌·우 4방향)를 안쪽 거울면에서 바깥쪽으로 **관통하여 걸치도록(straddling the mirror bezel)** **정확히 4개의 굵고 큼직한 주황색(`#F26925`) 단색 확장 화살표(`length ≈ 114~144px`, `shaft_w ≈ 29~36px`, `head_w ≈ 74~92px`)**를 배치하며, 각 미러 테두리의 자연스러운 외곽 법선 벡터 방향으로 뻗어 나갔다가 복귀하는 왕복 애니메이션을 숏폼과 롱폼 모두에 적용한다.<br>③ **BGM 전 구간 커버 필수 (`bgm had to be cover through video`)**: 4초짜리 짧은 테스트 오디오(`smoke_audio.mp3`) 사용을 금지하며, 반드시 영상 시작(`0.0s`)부터 종료(`12.0s` 등 전체 길이)까지 **100% 전 구간에 걸쳐 BGM이 끊김 없이 재생**되도록 전체 길이 오디오 클립과 타임라인 구간(`0s ~ duration_s`)을 지정한다.<br>④ **다양한 화면 전환 효과 지원 (`Expand Screen Transition Effects`)**: 단순 암전(`blackout` / `fade=t=in,out`)만 사용하는 방식을 폐기하고, 일반 단일 씬 전환 시 `cross-dissolve`(`믹스`), `wipe`(`지우기`), `slide`(`슬라이드`), `fade`(`페이드`), `zoom`(`확대`) 등 다채로운 다이내믹 전환 효과를 적용한다.<br>⑤ **분할 비교 씬 전환 효과 전면 비활성화 (`Disable Transitions during Split-Screen Comparisons`)**: 50:50 분할 비교(`시공 전` / `시공 후`) 씬으로 **진입할 때(entering)**, **씬 내부(within)**, **다음 씬으로 빠져나올 때(exiting)**는 그 어떠한 화면 전환 효과도 적용하지 않는다(`should_apply_transition() == False`).<br>⑥ **얼굴 노출 시 솔리드 블랙 마스킹 필수 (`Face Masking Requirement`)**: 거울 반사 또는 배경에 사람의 얼굴이 감지될 경우, 얼굴 영역 전체를 불투명한 검정 원형/사각형 마스크(`구글드라이브다운파일/media/face_mask_circle.png` / `로고_얼굴마스크.png`)로 빈틈없이 가려 이목구비가 0% 노출되도록 처리한다. | ① **100% 실제 4K `.MOV` 영상 클립만 사용 (`0%` 정지 이미지 슬라이드쇼, `0%` 무관한 타 차종·인물 노출)** — 각 차종의 Google Drive 원본 폴더(`사이버트럭 옵틱 [26.01.13]`, `현대 더뉴 싼타페 옵틱 [25.09.17]` 등) 내 실제 4K `.MOV` 영상만 사용.<br>② **사이드미러 전체 노출 필수 (`Full sidemirror had to be shown`)**: 단독 미러 씬(`s08`, `s13`, `s14`)과 50:50 좌우 분할 비교 씬(`s15`, `s16`의 `시공 전` 좌측 패널 및 `시공 후` 우측 패널 모두)에서 **사이드미러 거울면과 베젤/하우징의 좌·우·상·하 전체(100%)가 잘림 없이 프레임 안에 온전히 노출**되어야 한다. 과도한 줌인 크롭으로 미러 우측·좌측 끝이나 상단 꼭짓점이 잘리는 것을 절대 금지하며, 미러 전체 노출을 위해 크롭 영역을 넓혔을 때 상단 배경에 인물 얼굴이 포함되면 `face_mask_circle.png`(1:1 원본 해상도 좌표계)로 완벽히 마스킹한다.<br>③ **화면 떨림/진동 효과(`Vibrating Screen Effect`) 전면 금지** — CapCut 템플릿의 흔들림 애니메이션, 왜곡 트랜지션, 비디오 이펙트 전면 제거.<br>④ **상품에 맞는 공식 브랜드 로고 + 드롭 섀도우 삽입** — 배경 박스 없이 로고 및 인트로 타이틀(`현대 더뉴 싼타페`, `2026 테슬라 사이버트럭`)에 드롭 섀도우 적용.<br>⑤ **시공 전·후 비교 컷 화살표 이펙트 4개 고정 (`arrow effects had to be 4`) 및 BGM 전 구간 커버 (`bgm had to be cover through video`)**: 비교 컷에 화살표 이펙트를 사용할 경우 반드시 상·하·좌·우 **4개**로 고정하여 벡터 방향 왕복 애니메이션을 적용하고, BGM은 영상 시작부터 아웃트로 종료까지 전 구간(100%)을 빈틈없이 커버한다.<br>⑥ **다이내믹 화면 전환 확장 및 분할 비교 씬 전환 금지 (`Expand Transitions & Disable on Split-Screen`)**: 클립 자체 암전(`blackout`)을 금지하고 일반 씬 사이에 `cross-dissolve`, `wipe`, `slide`, `fade`, `zoom` 전환을 순환 배치하되, 50:50 분할 비교 씬(`s15`, `s16` 등) 진입·내부·이탈 경계에는 전환 효과를 일절 적용하지 않는다.<br>⑦ **생성 후 필수 검수 규칙 (`After Created` 3대 원칙)**:<br>  - **사이드미러 점선 정합 검수 (`if not fits dotted line to side mirror border line, delete dotted line`)**: 핸드헬드 `.MOV` 영상에서 고정된 노란 점선(`---`) 및 확장 화살표가 움직이는 사이드미러 테두리와 일치하지 않을 경우 점선과 화살표를 즉시 삭제하고(`s14` 오버레이 제거, `s15`·`s16` 50:50 분할선은 중앙 백색 수직선 `(960,0)-(960,1080)`만 유지), 깔끔한 원본 비교 화면을 유지한다.<br>  - **차량 번호판 노출 시 `로고_번호판` 이미지 커버 (`if video shows license plate, cover to 로고_번호판 img`)**: 모든 슬롯(`s00 ~ s17`)을 전수 스캔하여 실제 차량 번호판이 노출되는 클립(예: 싼타페 `s00, s01, s02`, 사이버트럭 `s00, s02`)은 `assets/masks/로고_번호판.png`(`Optic-Glass` 번호판 커버)를 원근 호모그래피(`cv2.warpPerspective`) + 프레임 간 템플릿 매칭(`cv2.matchTemplate`)으로 전 프레임 밀착 합성하여 번호판 숫자가 0% 노출되도록 가린다.<br>  - **사람 얼굴 노출 시 솔리드 블랙 마스킹 (`Face Masking Requirement`)**: 영상 프레임이나 사이드미러 반사면에 사람의 얼굴이 감지되면 불투명한 검정 마스크(`구글드라이브다운파일/media/face_mask_circle.png` / `로고_얼굴마스크.png`)를 프레임별 추적 적용하여 이목구비가 전혀 노출되지 않도록 가린다.<br>⑧ **Google Drive 지정 차종 폴더 인덱스 엄격 격리 (`Strict Vehicle Model Index Isolation`)**: 영상을 생성할 때는 반드시 Google Drive 폴더 인덱스(`이전 자료 > 0.옵틱 광각`, Folder ID `1TT2v1sLCQdBIISjDucJPJGcineVIB76B`) 내에 지정된 **해당 차종 전용 폴더**(`구글드라이브다운파일/media/<slug>/gdrive_raw/`) 안의 이미지 및 영상 파일만 참조해야 하며, 타 차종 폴더나 범용 `Downloads` 폴더의 에셋을 절대 혼용하지 않는다(`preflight_check.validate_media_paths(..., allowed_vehicle_dir=...)`로 강제 검증). |


