# 영상 편집 자동화 전략 수립 — Hermes 작업 지시서

이 폴더(`C:\Users\bssho\Downloads\paperclip-master\video-automation`)에서 실행된 Hermes는 이 문서를 따른다. 보고와 산출물은 **한국어**로 작성한다.

> **2026-11-06 결정**: FilmCraft 폐기 — 결과물은 CapCut 초안(롱폼·숏폼 모두 CapCut GUI에서 Export), 미리보기 MP4/9프레임 시트/숏폼 MP4 제거. 시각 검수는 배포된 CapCut 초안을 열어서 한다. FilmCraft → FCP7 XML → Premiere 비상 경로도 폐기했다. 아래 FilmCraft 관련 내용은 2026-10-16 전략 수립 당시 기록이다.

## 1. 목표

사용자는 **다운로드한 CapCut 템플릿 설명(.md)과 레퍼런스 영상·이미지**를 입력으로 받아, AI 에이전트가 편집된 영상을 만드는 자동화 파이프라인을 원한다.

이번 작업의 목표는 **대량 제작이 아니라 전략 수립**이다. 실험으로 근거를 모으고, 어떤 경로로 자동화할지 결정해서 문서로 남긴다.

### 산출물

| 파일 | 내용 |
|---|---|
| `strategy/STRATEGY.md` | 최종 전략 문서. 형식은 9장 |
| `strategy/spec.schema.json` | 중립 편집 명세(spec) JSON Schema v0.1. 초안은 8장 |
| `strategy/specs/<템플릿명>.spec.json` | 실제 .md 1~2개를 변환한 spec |
| `strategy/experiments/<날짜>-<이름>.md` | 실험 로그. 실행한 명령, 출력, 결과 파일 경로, 판정 |

## 2. 이미 확인된 사실 (2026-10-16 기준)

자세한 근거와 출처는 `research/facts.md`(약 10만 자)에 있다. 한 번에 다 읽지 말고 1장과 3장만 읽고 나머지는 `search_files`로 필요한 부분만 찾는다. 그 파일 1장의 **검증 정정 사항이 다른 내용보다 우선**하고, 이 문서(HERMES.md)는 facts.md 전체보다 우선한다(더 최신). 아래 사실은 다시 조사하지 말고, 바뀌었을 가능성이 있을 때만 확인한다.

### 환경
- Windows 11 Pro, Python 3.14.7(`py`), Node 24.21 / npm 11.19
- **ffmpeg는 PATH에 없다.** CapCut 폴더에 동봉된 `ffmpeg.exe`(커스텀 빌드, ffprobe 없음, 업데이트 때 교체됨)는 쓰지 않는다. PySceneDetect, OpenCV, librosa, beat_this, PaddleOCR도 설치되어 있지 않다(분석 관련은 numpy만 있음).
- Adobe Premiere Pro 2021이 설치되어 있다. 마감 도구로 쓸 수 있는지는 검증하지 않았다.

### CapCut
- 버전 **9.6.0.4097**. 2026-10-15에 9.1.0에서 자동 업데이트됐다.
- 초안 폴더: `C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft`
- **암호화는 버전 탓이 아니다.** 클라우드 팀 스페이스에서 내려받은 일부 초안에만, 초안별로 붙는다. `root_meta_info.json` 항목에 `draft_cloud_last_action_download=true`가 있는 초안이 대상이다. 같은 스페이스에서 받았어도 평문인 초안이 있다.
- 암호화 판별: 루트 `draft_content.json`과 `Timelines/*/draft_content.json` 중 하나라도 첫 바이트가 `{`가 아니면 암호화다. `draft_virtual_store.json`의 `"is_encrypted":true,…,"path":"draft_content.json"` 항목은 보조 신호다. 암호화된 `57.08 벤츠`에는 이 항목이 없고, 평문 `전사스 템플릿3`에는 wav 경로로 `is_encrypted:true`가 있다. `crypto_key_store.dat` 유무는 판별 기준이 **아니다**.
- 루트 파일은 평문이어도 `Timelines/*/draft_content.json`이 암호화된 초안이 있다(`옵틱글래스 광각미러 템플릿 1`). CapCut 9.2.8 이상은 Timelines 쪽을 먼저 읽는다는 보고가 있다(capcut-cli 문서, 9.6 미검증). 루트만 보고 템플릿으로 쓰면 오래된 사본을 오류 없이 쓰게 될 위험이 있다.
- 국제판 CapCut의 **MP4 export 자동화 경로는 없다.** pyCapCut 컨트롤러는 중국판 剪映 창 전용이고, 9.5.0 export 대화상자는 UIA·MSAA에 자식 컨트롤을 노출하지 않는다(메인테이너 답변, 9.6은 미확인). 최종 export는 사람이 GUI에서 한다.
- 도구가 만든 평문 초안이 열린다는 공개 검증은 9.3.0까지다. **9.6에서 열리는지는 미검증**이다. 테스트 초안은 준비해 두었다(4장 Phase 1).
- 10.x는 외부에서 작성한 초안을 손상으로 거부한다는 보고가 있다.

### 도구
- **pyCapCut**: `C:\Users\bssho\Downloads\paperclip-master\pyCapCut`
  - 브랜치 `fix/template-mode-data-loss` @00e08e6. origin/main 위에 데이터 손실·템플릿 모드 버그 수정을 올렸다(푸시하지 않음).
  - `py`에 editable로 설치되어 있다. Hermes `execute_code`는 Hermes 내장 Python이라 `import pycapcut`가 실패한다. pyCapCut 코드는 `work/`에 .py로 저장해 터미널에서 `py work/<파일>.py`로 실행한다.
  - 테스트: `(cd C:/Users/bssho/Downloads/paperclip-master/pyCapCut && py -m unittest discover -s tests)` (31 통과, 1 건너뜀). Hermes 터미널은 `cd`가 다음 호출까지 남으므로 다른 폴더 명령은 이렇게 괄호로 감싼다.
  - 템플릿 모드는 평문 초안만 읽는다. 남은 이슈는 `research/facts.md` 3장에 있다(✅ 표시가 없는 항목).
- **cli-anything-capcut v0.5.7**: `C:\Users\bssho\Downloads\cli-anything-capcut-main\cli-anything-capcut-main`
  - **설치되어 있지 않다.** 쓰려면 사용자 승인 후 그 폴더에서 `py -m pip install -e .`
  - 그대로 쓰면 다음과 같이 오류 없이 결과가 틀어진다:
    - 레시피에 적은 `id`가 무시되고 `op_N`으로 다시 매겨진다. 트랙이 자동 추가되면 번호가 더 밀린다.
    - `"duration": "auto"`가 0µs로 처리된다.
    - 레시피의 width/height/fps가 무시된다.
    - 동봉 레시피 템플릿 5종은 깨져 있다.
    - `plan` 명령에는 fade 인자 버그가 있다.
  - `render`는 剪映 전용이라 국제판에서 동작하지 않는다. `render-headless`는 효과가 빠지는 ffmpeg 근사다.
- **FilmCraft 0.8.0** (storytold/filmcraft, MIT OR Apache-2.0): `C:\Program Files\FilmCraft\filmcraft-cli.exe` — **2026-11-06 폐기, 쓰지 않는다.** 아래는 당시 기록이다.
  - 이 PC에서 headless로 JSONL 실행, 한글 텍스트, PNG 프레임 렌더, MP4 export까지 성공했다. 한글은 글꼴을 지정해야 보인다(10장).
  - 생성된 지 약 16일 된 **alpha**이고 자체 실사용 준비도는 약 56%다. CapCut 템플릿은 가져올 수 없어 **재구현**해야 한다.
  - GUI와 `--bridge` 모드는 위험하다(Win11 크래시 이슈 #380, bridge 버그 #1538). **headless만** 쓴다.
  - 폴더 접근 제한이 없다(PR #985 open).
- **Remotion 4.0.535**: 실행 가능한 설치는 **없다**(node_modules·전역 설치 없음). `C:/Users/bssho/Downloads/paperclip-master/my-video`에 사용자가 2026-10-16에 `create-video`로 만든 Next.js+Lambda 골격과 `.agents/skills/remotion-best-practices`가 있다. 이 스킬은 Hermes에 로드되지 않으니 필요하면 read_file로 읽는다. 새 프로젝트를 만들지 말고, 쓰게 되면 사용자 승인 후 my-video에서 `npm install` → `npx remotion render`로 로컬 렌더한다. Lambda(`deploy.mjs`, AWS)는 쓰지 않는다. `Downloads/remotion-main.zip`(소스 597MB)은 빌드하지 않는다. 직원 4명 이상 영리조직이면 유료 라이선스가 필요하다.
- **HyperFrames**(heygen-com, Apache-2.0): 설치되어 있지 않다. 0.x이고 거의 매일 릴리스된다. Node 22 이상, FFmpeg, Chromium이 필요하다.
- **CapCut MCP 계열**(VectCutAPI와 그 래퍼): 새 초안 생성만 하고 템플릿 불러오기·교체·렌더가 없다. **도입하지 않는다.** 셸이 있는 Hermes에는 로컬 pyCapCut/CLI가 더 단순하다.

## 3. 절대 규칙

1. **복호화 금지.** 암호화된 초안을 복호화하는 도구를 설치·실행하지 않고, 외부 사이트에 올리지 않는다. CapCut 약관 6조와 저작권법 104조의2에 저촉될 위험이 있다.
2. **기존 초안은 읽기 전용이다.** drafts 폴더에 쓰는 것은 이름이 `hermes_` 또는 `pycapcut_smoke_`로 시작하는 **새 폴더**만 허용한다. 삭제나 덮어쓰기는 사용자에게 매번 확인받는다.
3. **CapCut이 실행 중이면 drafts 폴더에 쓰지 않는다.** 확인: `tasklist /FI "IMAGENAME eq CapCut.exe" /NH /FO CSV | grep -ic capcut.exe`(0이면 종료. 한글 안내문은 Hermes 터미널에서 깨지니 개수로 판정). 쓰기 전에 `C:/Users/bssho/AppData/Local/CapCut/Apps`의 가장 높은 버전 폴더도 확인한다. 9.6.0.4097이 아니면 Phase 1을 다시 하고, 10.x면 쓰지 말고 보고한다.
4. 클라우드 팀 스페이스에서 받은 초안은 템플릿 원본으로 쓰지 않는다. 템플릿 원본은 사용자가 이 PC에서 직접 만든 평문 초안의 **사본**만 쓴다.
5. 레퍼런스의 소재·음원·폰트 자체를 복제하지 않는다. 구성, 타이밍, 스타일 같은 **편집 문법만** 재현한다. CapCut 내장 폰트·음원·스티커는 CapCut 안에서만 쓰고 다른 렌더러로 옮기지 않는다(약관 10조). 다른 렌더러의 폰트·BGM은 상업 이용 라이선스를 확인한 것만 쓰고, `is_vip`(Pro 전용) 에셋은 spec의 `needs_review`에 넣는다.
6. 다음은 사용자 승인 후에만 한다:
   - 새 패키지 설치(pip/npm/winget, ffmpeg 포함)
   - 외부 클라우드 렌더(VectCut, Shotstack, Creatomate)에 미디어 업로드
   - CapCut 자동 업데이트 설정 변경
   - Hermes cron 작업·kanban 카드·스킬·프로필 생성. 이번 작업의 절차는 `strategy/`에 문서로만 남긴다.
7. FilmCraft는 실행하지 않는다(2026-11-06 폐기). 원본 미디어는 저장소 루트 `구글드라이브다운파일/media`에 복사한 사본만 쓴다.
8. 사람이 해야 하는 일(CapCut GUI에서 열기·확인·export, 설치 승인)은 번호를 매긴 단계로 적고 **그 응답으로 턴을 끝낸다.** 사용자의 다음 메시지 전에는 다음 Phase로 가지 않는다. `clarify`는 짧은 선택 질문에만 쓰고, 결과가 `timed_out`·`cancelled`·`undelivered`이면 답이 없는 것으로 보고 턴을 끝낸다(기본 1시간 뒤 시간 초과되면 Hermes가 혼자 진행한다). 추측으로 진행하지 않는다.
9. 사실과 추정을 구분해서 쓴다. 실행해서 확인하지 않은 것은 "미검증"으로 표시한다.
10. 하위 에이전트(`delegate_task`)도 이 문서를 받지만 사용자에게 물을 수 없다. 하위 에이전트에는 읽기 전용 조사·분석만 맡긴다. 네가 하위 에이전트라면 Phase를 진행하지 말고 위임받은 일만 한 뒤 결과를 돌려준다. drafts 폴더 쓰기와 설치는 하지 않는다.
11. `HERMES.md`와 `research/`는 고치지 않는다(Hermes 쓰기 승인 게이트는 HERMES.md를 보호하지 않는다). 새 사실은 `strategy/experiments/`에 적고, memory에는 미검증 실험 결과를 저장하지 않는다.

## 4. 작업 순서

### Phase 0 — 입력 확인 (사용자에게 질문)
아래 질문, Phase 1의 CapCut 확인 요청, Phase 3 설치 승인 요청은 서로 의존하지 않으므로 한 메시지로 보낸다.
1. 다운로드한 템플릿 .md 파일과 레퍼런스 미디어의 경로. 이전 조사에서는 찾지 못했다.
2. 템플릿 출처: CapCut 템플릿 스토어인지, 팀 스페이스 공유 초안인지, 직접 만든 것인지. 스토어 템플릿이면 원본 초안과 원작자 소재는 쓸 수 없다고 보고(수익화가 꺼진 템플릿은 초안 편집 불가) .md의 구조만 재구성한다. 팀 스페이스 초안은 3장 4번을 따른다.
3. 최종 MP4를 사람 손 없이 뽑아야 하는지, CapCut에서 사람이 마감해도 되는지, 목표 제작량(주당 편수).
4. 용도와 조직 규모: 상업용인지, 직원 3명 이하 영리조직 또는 개인인지(Remotion·폰트·음원 라이선스 판단용).

답을 받으면 .md 1~2개를 읽고 다음을 기록한다:
- CapCut 고유 이름(텍스트 애니메이션, 전환, 필터, 스티커, 花字, 폰트)이나 resource_id가 얼마나 있는지. 그중 pyCapCut enum(`cc.TransitionType`, `cc.TextIntro`, `cc.FilterType`, `cc.FontType`, `cc.VideoSceneEffectType` 등)에서 값의 `resource_id`나 영문 이름(`name`/`title`)으로 찾히는 비율과 `is_vip`(Pro 전용) 항목. 한국어 표시 이름은 enum 이름과 다르니 resource_id를 우선한다. 못 찾은 항목은 CapCut 경로에서도 '미검증'이다.
- 장면 타이밍이 얼마나 정밀한지
- 레퍼런스 영상의 길이, 화면비, fps

### Phase 1 — CapCut 9.6 호환성 확인
테스트 초안 두 개가 이미 drafts 폴더에 있다. 둘 다 9:16, 길이 4초이고 영상·오디오·노란 한글 텍스트 트랙이 하나씩 들어 있다. 미디어는 이 폴더의 `smoke_media/`에 있으니 옮기거나 지우지 않는다.

| 초안 | 차이 |
|---|---|
| `pycapcut_smoke_A` | pyCapCut 기본 출력. 버전 표시가 6.7.0 / new_version 140.0.0 |
| `pycapcut_smoke_B` | 이 PC에서 직접 만든 최신 초안 0729(9.1.0 / new_version 179.0.0, os 10.0.26200)의 platform 값을 복사. 새 id를 쓰고 meta에 이름·경로를 채움 |

사용자에게 다음을 요청한다:
1. CapCut을 실행해서 두 초안이 목록에 보이는지 확인한다.
2. 각각 열어서 다음을 확인한다:
   - "unusual/unconventional path"나 손상 경고가 뜨는지
   - 미디어 다시 연결(relink)을 요구하는지
   - 타임라인 4초에 트랙 3개가 보이는지
   - 한글 텍스트가 노란색으로 아래쪽에 보이는지
3. 10장의 글꼴 확인용 초안 `hermes_font_probe`를 만든다(10장 1~2단계).
4. 모든 초안을 저장하고 CapCut을 완전히 종료한다.

종료 후 Hermes가 각 초안의 `draft_content.json`과 `Timelines/*/draft_content.json` 첫 바이트, 그리고 `draft_virtual_store.json`에서 `path`가 `draft_content.json`인 `is_encrypted` 항목을 확인한다. 리소스 파일의 `is_encrypted`는 판정에 쓰지 않는다. 이걸로 9.6이 도구 초안을 저장할 때 암호화하는지 판정하고 `strategy/experiments/`에 기록한다.

판정 규칙(정상 = 2번 확인 항목이 모두 기대대로):
- **A 정상**: 기본 출력으로 충분하다.
- **열리지만 relink만 요구**: 실패로 보지 않는다. 생성기가 `draft_meta_info.json`의 `draft_materials`를 채워야 한다는 과제로 기록한다(pyCapCut #13).
- **B만 정상**: 생성기가 최신 로컬 초안의 버전 표시를 복사해야 한다.
- **둘 다 실패**: 증상(경고 문구, 빈 타임라인 등)을 기록한다. 'unconventional/unusual path' 경고였다면 앱이 만든 빈 초안에 주입하는 방식(zxypro1/capcut-shell-inject, 9.3.0에서만 보고됨)을 1회 시험한다. 빈 초안 `hermes_shell`은 사용자가 CapCut에서 만들어 저장·종료하고, 덮어쓰기는 확인받는다. 그래도 실패하면 CapCut 초안 쓰기를 멈추고 사용자에게 보고한다(FilmCraft 경로와 FilmCraft xml → Premiere 2021 비상 경로는 2026-11-06 폐기).
- **저장 후 암호화됨**: CapCut 초안은 "만들고 끝"인 산출물이다. 다시 읽어 고치는 단계는 설계에서 뺀다.

### Phase 2 — .md를 spec으로 변환
1. 8장 초안을 다듬어 `strategy/spec.schema.json`을 만든다.
2. Phase 0의 .md 1~2개를 `strategy/specs/`의 spec으로 변환한다. 문구와 구성은 .md를 기준으로 한다. 모르는 CapCut 이름은 null로 두고 `needs_review`에 넣는다.
3. 변환 규칙을 적용 순서대로 `strategy/STRATEGY.md` 초안에 적는다.

### Phase 3 — 레퍼런스 분석 (설치 승인이 필요하다)
컷·비트 분석에는 ffmpeg, PySceneDetect(+OpenCV), librosa나 beat_this가 필요하다. 설치 목록과 용량을 제시하고 승인받는다. 설치 후에는 `py -m scenedetect`처럼 모듈로 실행한다(Python Scripts 폴더가 PATH에 없다). 승인이 없으면 컷·비트는 .md 타이밍만 쓰고 한계를 문서에 적는다. 프레임 추출과 길이 확인은 ffmpeg로 한다(2026-10-16 당시의 FilmCraft headless 방식은 2026-11-06 폐기).

- **컷 경계**: PySceneDetect `detect-adaptive`
- **비트·다운비트**: beat_this 또는 librosa
- **텍스트 위치·색·전환 후보**: 장면마다 처음·중간·끝 프레임을 뽑아 비전 모델로 분석하고, JSON으로 받는다.
- **병합 원칙**: 타이밍은 분석값을 우선해 다운비트에 맞추고, 문구는 .md를 우선한다.
- **금지**: Hermes `video_analyze`(영상을 Gemini 같은 영상 모델로 보냄)와 Gemini 영상 이해는 기본 1fps 샘플링에 MM:SS 타임스탬프라서 타이밍 근거로 쓰지 않는다. 장면 설명 보조로만 쓴다.
- **사람 확인 대상**: 정확한 CapCut 에셋 ID, 한글 폰트, 전환 종류

### Phase 4 — 비교 실험
같은 spec 하나를 두 경로로 만들어 비교한다.
- **(a) CapCut 경로**: spec → pyCapCut 스크립트 → `hermes_<템플릿>` 초안. 사람이 열어 확인하고 export한다. cli-anything-capcut은 설치가 필요하고 조용히 틀리는 버그가 많아 이 실험에 쓰지 않는다(전략 문서에서 후보로만 평가).
- **(b) FilmCraft 경로**: spec → JSONL → headless 실행 → MP4. 2026-10-16에 실험을 마쳤고 2026-11-06에 폐기했다(기록: `strategy/experiments/2026-10-16-phase3-4-reference-and-filmcraft.md`).

비교 지표(표로 기록, 도구가 없어 못 재면 '측정 불가'로 적는다):
- 컷 타이밍 오차: 결과물에 PySceneDetect를 다시 돌려 레퍼런스와 비교(ms). 합격 기준 초안: 모든 컷이 2프레임(30fps 기준 67ms) 이내
- 장면별 시각 비교: 레퍼런스와 결과의 같은 시각 프레임을 뽑아 나란히 놓고, 비전 모델과 사용자가 1~5점으로 평가(합격 기준 초안: 평균 4점 이상)
- 장면 수 일치 여부
- 텍스트 내용·위치 일치
- CapCut 고유 효과 재현율: 재현 / 근사 / 불가로 분류해 비율 계산
- 사람이 손본 시간(분)
- 실패·경고 횟수
- 전체 소요 시간

### Phase 5 — 전략 문서 작성
9장 형식으로 `strategy/STRATEGY.md`를 완성하고, 사용자에게 요약을 보고한다.

## 5. 검증된 명령

**pyCapCut** (`py`로 실행할 때만 수정 브랜치가 import된다. `execute_code`에서는 안 된다):
```python
import pycapcut as cc
folder = cc.DraftFolder(r"C:\Users\bssho\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
s = folder.create_draft("hermes_example", 1080, 1920)   # 이름은 hermes_ 로 시작
s.add_track(cc.TrackType.video).add_track(cc.TrackType.text)
s.add_segment(cc.VideoSegment(r"...\구글드라이브다운파일\media\clip.mp4", cc.trange("0s", "3s")))
s.add_segment(cc.TextSegment("문구", cc.trange("0s", "3s")))
s.save()
```
- 시간에는 단위를 붙인다(`"1.5s"`). 단위가 없는 문자열은 조용히 0이 된다.
- `AudioSegment.add_keyframe`에는 문자열 시간 대신 `cc.tim("0s")`를 넘긴다(미수정 버그).

**FilmCraft**: 2026-11-06 폐기로 명령을 삭제했다. 2026-10-16 실행 기록은 `strategy/experiments/2026-10-16-phase3-4-reference-and-filmcraft.md`에 있다.

**초안 암호화 점검** (CapCut 종료 후):
```bash
py -c "import sys,pathlib; d=pathlib.Path(sys.argv[1]); [print(p, open(p,'rb').read(1)) for p in [d/'draft_content.json', *d.glob('Timelines/*/draft_content.json')] if p.exists()]" "<초안 폴더>"
```

## 6. 결정 원칙
- **MCP 서버는 만들지 않는다.** 셸이 있는 에이전트에는 CLI가 낫다. Claude Desktop처럼 셸이 없는 클라이언트가 필요해질 때만 CLI를 감싸는 얇은 래퍼를 검토한다.
- **Phase 4의 두 경로는 spec 1개를 옮기는 일회성 스크립트로 만든다.** 범용 컴파일러는 Phase 4 결과로 고른 하나만 설계하고, 두 번째는 라우팅 규칙이 요구할 때만 추가한다. spec, CapCut, FilmCraft, HyperFrames 컴파일러를 동시에 만들지 않는다.
- CapCut 고유 효과 비중(Phase 0에서 센 효과·전환·텍스트 애니메이션 중 pyCapCut enum으로 찾힌 비율, 초기값 절반 이상)이 높고, 사람 마감이 허용되고, Phase 1을 통과했으면 CapCut 경로를 기본으로 한다.
- 고유 효과 비중이 높은데 무인 MP4도 필수이면 두 조건이 충돌한다. 추측으로 고르지 말고 '사람 export 허용'과 '근사 재현 허용' 중 하나를 사용자에게 묻는다.
- 그 밖에도 CapCut 초안을 결과물로 한다(FilmCraft headless와 FilmCraft xml → Premiere 2021 경로는 2026-11-06 폐기). Phase 4 합격 기준에 못 미치면 HyperFrames나 Remotion을 검토한다.
- 추천에는 반드시 Phase 1과 4의 실측 근거를 붙인다. 근거가 없으면 "가설"로 표시한다.

## 7. 운영 가드레일 (전략 문서에 포함할 것)
- CapCut 업데이트 직후 스모크 테스트 절차: 최소 초안 생성 → 사람이 열어 경고 확인 → 저장 → 암호화 점검. 버전 감지는 Hermes cron의 `no_agent` 스크립트 작업으로 설계한다: `C:\Users\bssho\AppData\Local\hermes\scripts\`의 스크립트가 `C:\Users\bssho\AppData\Local\CapCut\Apps`의 버전 폴더 목록을 지난번과 비교해 바뀌었을 때만 출력한다(빈 출력은 알림 없음). cron은 게이트웨이가 떠 있을 때만 돌고 GUI 확인을 못 하므로 알림까지만 맡긴다. 생성은 사용자 승인 후.
- HyperFrames를 쓰게 되면 버전을 고정하고, 업그레이드 전에 같은 spec으로 다시 렌더해 비교한다.
- 10.x로 업데이트되면 CapCut 쓰기를 멈추고 재검증한다.

## 8. spec 초안 (v0.1 출발점)
```json
{"spec_version":"0.1","canvas":{"w":1080,"h":1920,"fps":30},
 "audio":{"bgm_slot":"bgm","bpm":128,"downbeats_s":[0.0,1.875],"sections":[{"label":"chorus","start":12.4,"end":28.0}]},
 "styles":{"title_a":{"font":"Noto Sans KR","weight":700,"capcut_font":null,"size_pct":7.5,"color":"#FFFFFF","stroke":{"color":"#000000","w":0.08},"anchor":[0.5,0.18]}},
 "scenes":[{"id":"s01","start":0.0,"dur":1.875,"snap":"downbeat#1",
   "slot":{"id":"clip_1","kind":"video","aspect":"9:16","min_src_dur":2.0,"subject_hint":"제품 클로즈업","fit":"cover"},
   "motion":{"type":"zoom_in","from":1.0,"to":1.12,"ease":"ease_out"},
   "texts":[{"text":"{{HOOK}}","style":"title_a","t":[0.1,1.7],"in":{"class":"pop","dur":0.3},"out":{"class":"fade","dur":0.2}}],
   "transition_out":{"class":"whip_left","dur":0.25,"capcut":null,"fallback":"cut"},
   "effects":[{"class":"flash","at":0.0,"dur":0.1,"capcut":null}],
   "audio_cue":{"sfx":"whoosh","at":1.65,"duck_db":-6},
   "confidence":{"timing":0.97,"transition":0.55,"text_style":0.7},
   "needs_review":["transition_out","effects"]}]}
```
- 시간은 초 단위로 저장하고, 렌더러별로 변환한다. pyCapCut은 µs다.
- `capcut` 필드가 null이면 사람이 고르거나 `fallback`을 쓴다.

## 9. STRATEGY.md 형식
1. **결론**: 한 문단. 기본 경로와 그 이유
2. **파이프라인**: 입력 → spec → 렌더러 → 검수 → 출력. 각 단계의 도구와 담당(자동/사람)
3. **렌더러 결정 근거**: Phase 1·4의 실측 표
4. **템플릿 유형별 라우팅 규칙**: 예) 유형마다 CapCut 초안 구성을 어떻게 다르게 할지(FilmCraft 경로는 2026-11-06 폐기)
5. **자동화 경계 표**: 자동 / 반자동(LLM 후보 + 사람 확인) / 사람 필수
6. **운영 가드레일**: 7장 내용을 구체화
7. **리스크와 완화책**: 암호화, 업데이트, alpha 도구, 라이선스(Remotion·폰트·음원, LICENSE가 없는 pyCapCut)
8. **미해결 질문**
9. **다음 2주 실행 계획**: 할 일, 완료 기준, 필요한 사용자 승인

## 10. 글꼴 규칙 (사용자 결정: Noto Sans)
- **모든 텍스트의 기본 글꼴은 `Noto Sans KR`이다.** `Noto Sans`(라틴 전용)는 한글이 □로 나오니 한글이 들어가면 쓰지 않는다. 둘 다 설치되어 있다(`NotoSansKR-VF.ttf`는 시스템, `NotoSans-VariableFont`는 사용자 글꼴).
- **FilmCraft 0.8.0 한계(2026-10-16 실측, 2026-11-06 FilmCraft 폐기로 해당 없음, 기록용)**: `Noto Sans KR`은 가변 글꼴이라 `fontStyle:"Regular"`도 가장 가는 굵기로 나온다. `"Bold"`는 글자 끝에 가시 모양 깨짐이 생긴다(B·o·l·d, 한). 해결책은 정적 굵기 파일(Google Fonts의 NotoSansKR-Regular/Bold 등)을 설치하는 것인데, 설치는 사용자 승인 후에 한다. 그 전까지 FilmCraft 실험에서 굵기 차이는 판정에서 제외하고, 렌더 PNG에서 깨짐 여부를 기록한다.
- **CapCut 경로**: pyCapCut `FontType`에는 Noto Sans KR이 없다. CapCut 캐시에 정적 `NotoSansKR-Regular.otf`가 있다(`User Data\Cache\effect\7189852363404874242\`). 매핑은 미검증이므로 Phase 1 때 사람에게 다음을 요청한다:
  1. CapCut에서 새 초안 `hermes_font_probe`를 만든다.
  2. 텍스트 하나에 Noto Sans KR(가능하면 Regular와 Bold 두 개)을 적용해 저장하고 종료한다.

  초안이 평문이면 text 소재와 `content.styles[].font`의 글꼴 필드(id, path)를 읽어 생성기 매핑으로 기록한다. 암호화됐으면 그렇게 기록하고, CapCut 경로에서는 CapCut 기본 글꼴을 쓰는 것을 대안으로 적는다.
