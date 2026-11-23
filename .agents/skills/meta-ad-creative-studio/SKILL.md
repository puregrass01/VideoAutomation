---
name: "meta-ad-creative-studio"
description: "퓨어그래스·스타포쉬·옵틱글래스 메타 광고 소재 제작: 스토리보드, 릴스·숏츠 레퍼런스 변환, 2주 소재팩, 힉스필드 장면 생성(크레딧 절약), FilmCraft 편집 파일, 저작권 안전 음악, 카피."
---

# 메타 광고 소재 스튜디오

퓨어그래스·스타포쉬·옵틱글래스의 메타 광고 소재를 **기획 → 스토리보드 → 힉스필드 장면 생성 → FilmCraft 편집 패키지 → 카피**까지 만들어, 사람은 검수·자막 스타일·최종 내보내기만 하면 되게 하는 스킬이다. 장면 영상은 힉스필드 MCP 커넥터로 직접 생성하고(§13), 커넥터가 없으면 프롬프트 목록을 넘긴다. 편집은 FilmCraft에서 한다(§14). 산출물의 품질 기준은 "편집자·AI툴이 질문 없이 바로 작업할 수 있을 만큼 구체적인가"이다.

**기본 파이프라인**: 스토리보드(§11) → 스토리보드 JSON 저장 → 힉스필드 비용 확인·승인 → 장면 생성·다운로드(§13) → 생성물 검수 → 음악 선정(§15) → FilmCraft 패키지 생성(§14) → 사용자는 FilmCraft에서 열어 자막 스타일만 다듬고 내보내기.

## 작업 모드

| 요청 | 모드 | 섹션 |
|---|---|---|
| "예전 광고 영상 이걸로 다른 버전 만들어줘" | A. 리폼 | §4 |
| "이 릴스/숏츠처럼 우리 제품으로" | B. 레퍼런스 벤치마킹 | §5 |
| "이번 2주 소재 뽑아줘", "소재 교체" | C. 스프린트 소재팩 | §6 |
| "이 콘티로 프롬프트만", "카피만" | D. 프롬프트·카피 단독 | §7, §8 |
| "이 스토리보드로 영상 뽑아줘", "FilmCraft 파일 만들어줘" | E. 영상 제작 | §13, §14, §15 |

요청이 모드를 섞으면(예: 레퍼런스 2개 + 2주 팩) C를 골격으로 하고 A·B 결과를 팩 안의 소재로 넣는다.

## 1. 시작 전에 불러올 것

이 작업은 "광고 영상 제작" 프로젝트에 이력이 쌓인다. 매번 처음부터 시작하지 않도록 먼저 읽는다.

- `project_search`/`project_read`로 `claude/brand-profiles.md`(브랜드 프로필), `claude/creative-log.md`(지난 스프린트 소재·성과)를 확인한다.
- 지난 소재와 같은 훅·포맷·장면을 반복하면 메타가 같은 소재로 묶어 버리므로(§3), 새 기획은 항상 creative-log와 겹치지 않는지 대조한다.
- 브랜드 프로필이 없거나 오래됐으면 §2로 먼저 만든다.

## 2. 브랜드 프로필

세 브랜드 모두 "내 차종에 딱 맞는 자동차 용품"이 공통 축이다. 차종 매칭은 가장 강력한 개인화 훅이므로 기획마다 활용한다("카니발 타시는 분", "테슬라 Y 오너라면").

| 코드 | 브랜드 | 몰·커넥터 | 주력 | 확인된 사실 |
|---|---|---|---|---|
| PG | 퓨어그래스 | 카페24 `PG`(puregrass.co.kr) | 차종별 맞춤 하드타입 코일 매트 | 국산·수입 전 차종 카테고리, 대표상품 #177 220,000원 |
| SP | 스타포쉬 | 카페24 `SP` | 전동 사이드스텝 Pro(기본형/LED), 고정 사이드스텝, 그릴, 바디킷, 핸들커버 | SUV·미니밴 중심(카니발, 팰리세이드, 스타리아, 레인지로버, BMW X시리즈, 카이엔 등) |
| OG | 옵틱글래스 | 아임웹 `KR/US/JP` (optic-glass.co.kr) | 차종별 광각 사이드미러 | 1,600개 이상 차종 모델, 한·미·일 판매 |

USP·수치·인증·보증·가격 같은 사실은 **추측해서 쓰지 않는다**. 광고에 들어간 틀린 수치는 표시광고법 문제가 되고 신뢰를 잃는다. 확인 방법:
1. `get_product`로 상품 정보와 상세 이미지 주소를 받는다(상세페이지는 대부분 이미지라 텍스트가 거의 없다).
2. 상세 이미지를 직접 본다: 내장 브라우저로 상품 페이지를 열어 `get_page_text`·스크린샷으로 읽거나, 사용자가 이미지를 첨부·폴더 연결하면 Read로 본다. (클라우드 셸의 직접 다운로드는 프록시에 막힐 수 있다.)
3. 확인 못 한 항목은 프로필에 `[확인 필요]`로 남기고 카피에서 빼거나 사용자에게 묻는다.

프로필 항목: 핵심 USP 3개(근거 포함), 타깃 페르소나 2~3개(차종·상황·고민), 자주 받는 질문/반론, 금지·주의 표현, 톤, 브랜드 컬러·로고 사용 규칙, 보유 소스(실사 촬영본·리뷰·설치 영상). 만든 뒤 `project_write`로 `claude/brand-profiles.md`에 저장한다.

## 3. 메타 광고 최적화 원칙

스펙은 메타가 수시로 바꾸므로 납품 전 광고관리자 미리보기에서 최종 확인하라고 산출물에 적는다. 아래는 2026년 10월 기준 업계 가이드 여러 곳이 일치한 값이다(메타 공식 가이드 페이지는 자동 조회가 막혀 있어 직접 확인하지 못했다). 웹 검색이 되면 작업 시작 때 한 번 "Meta ad specs safe zone"을 검색해 바뀐 점이 있는지 본다.

**규격**
- 릴스·스토리: 9:16, 1080×1920. 피드: 4:5, 1080×1350(1:1도 되지만 화면 점유가 커서 4:5가 기본). 캐러셀: 1:1 1080×1080(4:5 가능, 모든 카드 비율 통일). 영상 하나를 만들면 9:16 원본 + 4:5 크롭 버전 지시를 함께 쓴다.
- 9:16 세이프존(1080×1920 기준): 위 14%(약 270px), 아래 35%(약 670px), 좌우 6%(약 65px)에는 자막·로고·제품 핵심부를 두지 않는다. 릴스는 오른쪽 아래(세로 1150px 아래, 오른쪽 약 230px 폭)에 좋아요·댓글 버튼이 더 덮으므로 그 영역도 비운다. 스토리와 릴스는 2026년부터 같은 세이프존을 쓴다는 안내가 있으니 하나의 기준으로 맞춘다.
- 4:5 피드는 위아래·좌우 약 10%(135px/108px) 여백을 권장(필수는 아님).
- 영상 길이: 릴스 광고는 최대 90초, 스토리는 카드당 120초까지 가능하지만 전환 목적은 9~15초 기본, 설치·데모형은 20~30초까지. 6초 범퍼는 리타게팅용 보조.
- 파일: 영상 MP4/MOV, H.264, AAC 128kbps 이상, 30fps, 최대 4GB(1GB 이하 권장). 이미지 JPG/PNG, 최대 30MB.

**크리에이티브**
- 첫 1~3초가 전부다. 0초 프레임부터 제품 또는 고민 장면이 보여야 하고, 로고 인트로·느린 페이드인은 쓰지 않는다.
- 음소거 시청이 많으므로 모든 대사·내레이션은 자막으로 넣는다(번인 자막).
- 화면 텍스트는 한 장면에 한 메시지, 7~12자 내외 큰 글씨.
- 컷 길이 평균 1~2초. 3초 넘게 정지된 장면은 이탈 구간이다.
- 마지막 2초에 CTA(제품+행동: "내 차종 검색하기") 장면.

**소재 다양성 (Andromeda 이후 메타 알고리즘)**
메타는 2025년 10월 Andromeda 이후 소재 자체를 타기팅 신호로 쓰며, 공식적으로 "충분히 다르지 않은 변형은 의미 있는 효과가 없다"고 안내한다. 비슷해 보이는 소재는 사실상 같은 소재로 취급돼 노출이 몇 개에 몰린다. 유연한 형식(Flexible format) 광고에는 소재를 최대 10개까지 넣을 수 있다. 그래서 2주 소재팩의 영상 5개는 "자막만 바꾼 변형"이 아니라 서로 다른 컨셉이어야 한다. 소재마다 아래 4축 중 최소 2개가 달라야 한다:
- 페르소나(누구) / 고민·욕구(왜) / 포맷(어떻게: §9 포맷 라이브러리) / 비주얼 세팅(어디서·누가 출연·실사 vs AI vs 그래픽)

**정책·법규**
- '최고·최초·1위·유일·완벽·100%' 같은 최상급·절대 표현은 근거 자료가 있을 때만. 옵틱글래스는 "사각지대 제거" 대신 "사각지대를 줄여주는" 식으로 쓴다.
- 차량 브랜드명은 "○○ 차종 전용"처럼 호환 정보로만 쓰고, 제휴·공식 인증처럼 보이게 하지 않는다. AI 생성 차량은 엠블럼 없는(unbadged) 차로 지시한다.
- 레퍼런스 영상의 촬영본·음악·문구·인물을 그대로 쓰지 않는다. 가져오는 것은 구조·리듬·훅 메커니즘뿐이다.
- 실제 고객 후기를 지어내지 않는다. 후기형 포맷은 실제 리뷰(사용자 제공) 인용이거나, "연출" 표시한 상황극으로 기획한다.

## 4. 모드 A — 이전 영상을 다른 폼으로

목적: 이미 가진 촬영본을 최대한 재활용해 새 컨셉 소재를 만든다. 재촬영 비용을 줄이는 게 핵심 가치다.

1. 영상을 분석한다(§10). 결과로 **샷 리스트**를 만든다: 번호, 타임코드, 화면 내용, 자막/대사, 사운드, 역할(훅/문제/데모/증거/CTA), 재활용 가치(상·중·하).
2. 원본 진단: 훅 강도, 페이싱(평균 컷 길이), 세이프존 위반, 자막 유무, CTA 유무를 짧게 평가한다. 성과 데이터가 있으면 함께 본다.
3. §9 포맷 라이브러리에서 원본과 **다른** 포맷 2~3개를 골라 각각 스토리보드를 만든다. 각 씬에 소스를 표기한다:
   - `[재활용 00:04.2–00:06.0]` 원본 구간 그대로/크롭/속도 조절
   - `[실사 촬영]` 새로 찍어야 하는 컷(촬영 지시 포함)
   - `[AI 영상]` / `[AI 이미지]` 생성 프롬프트로 만들 컷
   - `[그래픽]` 자막·모션그래픽만으로 된 컷
4. 재활용 비율을 산출물 상단에 적는다(예: "8씬 중 5씬 재활용, 신규 촬영 1, AI 2").
5. 길이·비율 변형 지시: 15초 기본 → 6초 범퍼 컷 편집점, 9:16 → 4:5 크롭 시 잘리는 요소.

## 5. 모드 B — 레퍼런스(릴스·숏츠) → 우리 제품

1. 레퍼런스를 분석한다(§10). 파일이면 스크립트, 링크면 브라우저.
2. **구조 해부**를 먼저 적는다. 이게 이 모드의 핵심 산출물이다:
   - 훅 메커니즘(무엇이 스크롤을 멈추게 하나: 의외의 장면, 질문, 소리, 숫자, 대비, POV…)
   - 비트 구성(초 단위: 0–2 훅 / 2–6 문제 / … ), 평균 컷 길이, 자막 스타일·위치, 사운드 역할
   - 왜 잘 됐을지 가설(조회수·댓글·좋아요가 보이면 근거로)
3. 우리 브랜드 중 구조가 맞는 제품·차종·페르소나를 고른다. 사용자가 지정하지 않았으면 가장 맞는 1안 + 다른 브랜드 대안 1안.
4. 비트 단위로 1:1 매핑한 스토리보드를 만든다("레퍼런스 비트 → 우리 씬" 대응표). 구조는 빌리고 내용은 우리 제품의 실제 USP로 채운다.
5. 레퍼런스에서 그대로 가져오면 안 되는 요소(음원, 인물, 특정 문구)를 대체안과 함께 명시한다.

## 6. 모드 C — 2주 스프린트 소재팩 (기본: 브랜드당 영상 5 + 이미지 10)

메타는 정해진 교체 주기를 공식으로 두지 않는다. 피로도는 "같은 사람이 너무 자주 본 것"이므로 빈도 상승·CTR 하락·CPA 상승으로 판단한다. 2주 교체는 이 팀의 운영 기준이며, 매번 "이긴 것 발전 + 새 컨셉 탐색"을 반복하는 것이 목적이다. 성과가 아직 좋은 소재는 끄지 않고 새 소재를 옆에 추가한다.

1. **입력 확인** (모르면 묻되, 사용자가 없으면 기본값으로 진행하고 가정을 적는다)
   - 대상 브랜드(기본: 요청에 나온 브랜드, 없으면 3개 모두 각각), 집중 제품·차종, 프로모션 유무, 스프린트 시작일
   - 지난 스프린트 성과: 메타 광고관리자 내보내기(CSV/XLSX) 또는 스크린샷. 있으면 소재별로 계산한다:
     - 훅률 = 3초 재생 ÷ 노출, 유지율 = ThruPlay ÷ 3초 재생, CTR(링크), CPA/ROAS
     - 위너: CPA 하위 25% 또는 ROAS 상위 25% / 루저: 지출은 있는데 전환 없음
2. **구성 비율**: 데이터가 있으면 영상 5 = 위너 발전 2 + 신규 컨셉 3. 위너 발전도 §3의 4축 중 2축 이상 바꾼다(같은 메시지를 다른 포맷·세팅으로). 데이터가 없으면 5개 모두 신규.
3. **컨셉 매트릭스**를 먼저 표로 만든다(소재 ID, 페르소나, 고민/욕구, 포맷, 비주얼 세팅, 훅 한 줄, 브랜드·제품·차종). creative-log와 겹치는 행이 없는지 확인하고 다양성 체크 결과를 표 아래에 적는다.
4. 영상 5개 각각: 스토리보드(§11 형식) + 씬별 프롬프트(§7) + 카피(§8).
5. 이미지 10개: 메시지가 서로 다른 10개. 아래 유형에서 고르게 섞는다:
   제품 히어로 / 전후 분할 / 문제 클로즈업 / 수치·스펙 콜아웃 / 차종 매칭("○○도 있어요") / 실제 리뷰 인용 / 비교표(일반 제품 vs 우리) / 라이프스타일 / 오퍼·프로모션 / 텍스트 중심 밈형.
   각 이미지: 레이아웃 스케치(텍스트로 위치 지정), 헤드라인·서브 문구, 이미지 프롬프트, 4:5 기본 + 9:16 리사이즈 지시.
6. **제작 체크리스트**: 담당별(촬영/AI 생성/편집/카피 검수) 할 일, 필요한 실제 제품 사진 목록.
7. 파일명 규칙을 소재마다 붙인다: `{브랜드코드}_{YYMMDD}_{V|I}{두자리번호}_{포맷}_{훅키워드}_{비율}`
   예: `SP_261109_V03_POV-승하차_9x16`, `OG_261109_I07_차종매칭-테슬라Y_4x5`
8. 끝나면 creative-log에 이번 스프린트 행을 추가한다(§12).

## 7. AI 생성 프롬프트 작성 규칙

**실사 vs AI 판단이 먼저다.** AI는 제품 디테일(코일 매트 질감·재단선, 미러 곡률, 사이드스텝 구조, 그릴 패턴)을 지어내 바꿔 버린다. 그래서:
- 제품이 화면 주인공인 컷 → 실제 제품 사진을 첫 프레임으로 넣는 **이미지→영상(image-to-video)** 으로 지시하거나 `[실사 촬영]`으로 둔다. 프롬프트에 "keep the product exactly as in the reference image"를 넣는다.
- 분위기·상황·배경(세차장, 비 오는 주차장, 가족 캠핑, 야간 주행, 진흙 신발) → 텍스트→영상/이미지로 생성 가능.
- 한글 텍스트는 AI가 깨뜨리므로 생성물에는 "no text, no letters, no logos"를 넣고, 자막·헤드라인은 편집(CapCut/Canva)에서 얹는다.

**영상 프롬프트 형식** (영어로 쓰고, 아래에 한 줄 한국어 설명):
```
[Shot] vertical 9:16, {샷 크기: close-up / medium / wide}, {카메라: slow push-in / handheld POV / top-down / orbit}
[Subject] {누가/무엇이, 외형 구체적으로 — 차량은 "unbadged modern mid-size SUV, dark gray"}
[Action] {5초 안에 일어나는 한 가지 동작}
[Setting] {장소, 시간대, 날씨}
[Light & mood] {조명, 색감}
[Style] photorealistic, {smartphone UGC look | premium commercial look}
[Duration] 5s
[Avoid] text, logos, emblems, distorted hands, warped car body, extra wheels
[Start frame] (image-to-video일 때) {사용할 실제 제품 사진 설명}
```
- 컷 하나 = 프롬프트 하나 = 동작 하나. 여러 동작을 한 프롬프트에 넣으면 생성이 무너진다.
- 같은 영상 안 씬들은 인물·차량·색감 설명을 동일 문구로 반복해 일관성을 유지한다.
- 툴별 버전·기능은 자주 바뀌므로 특정 버전에 의존하는 문법은 쓰지 않는다. 사운드를 같이 만드는 툴(Veo, Sora 등)에는 "no dialogue, ambient sound only"를 넣고 내레이션은 따로 녹음/TTS로 지시한다.

**이미지 프롬프트 형식**: 구도, 피사체, 배경, 조명, 렌즈감, 스타일, 비율(4:5), 여백 위치("leave empty space at top 25% for headline"), Avoid 항목. 제품 히어로 이미지는 실제 제품 누끼 사진 + AI 배경 합성으로 지시한다.

## 8. 광고 카피

소재마다 메타 광고 문구 세트를 붙인다:
- 기본 문구(Primary text) 3안: '더 보기' 전에 약 125자까지 보이고 모바일은 2~3줄에서 잘리므로 첫 줄에 훅. 각 안은 서로 확실히 다른 각도(고민형 / 혜택형 / 차종 호명형). 메타는 문구 변형도 미세하면 효과가 없다고 안내한다.
- 헤드라인 2안: 40자 이내, 모바일 고려해 20자 안팎이 안전.
- 설명: 1안, 30자 이내.
- CTA 버튼 제안: 지금 구매하기 / 더 알아보기 등.
- 랜딩 URL: 해당 차종 상품 페이지(커넥터에서 확인한 실제 주소).
§3의 금지 표현을 피하고, 확인 안 된 수치는 넣지 않는다.

## 9. 포맷 라이브러리

| 포맷 | 구조(15초 기준) | 잘 맞는 제품 |
|---|---|---|
| 문제→해결 | 0–2 고민 장면 / 2–5 불편 강조 / 5–12 제품 해결 / 12–15 CTA | 전 브랜드 |
| 전후 비교(Before/After) | 분할화면 또는 와이프 전환 | 코일매트(오염), 그릴·바디킷(외관), 광각미러(시야) |
| POV(1인칭) | "○○ 오너의 아침" 시점 촬영 | 사이드스텝 승하차, 미러 차선변경 |
| ASMR·디테일 | 소리 중심 클로즈업(매트 털기, 스텝 전개음) | 코일매트, 전동 사이드스텝 |
| 설치 과정 타임랩스 | "5분 만에 장착" 가속 편집 | 미러, 매트, 그릴 |
| 3가지 이유 리스트 | 숫자 자막 1·2·3 + 컷 | 전 브랜드 |
| 비교 실험 | 일반 제품 vs 우리 제품 같은 조건 테스트 | 코일매트(물·모래), 광각미러(시야각) |
| 차종 호명 | "카니발 타시는 분 멈춰보세요" | 전 브랜드(차종별 변형 쉬움) |
| 오너 리뷰(실제 후기) | 실제 리뷰 텍스트/고객 영상 + 제품 컷 | 전 브랜드 |
| 상황극(가족·동승자) | 아이·어르신 승하차, 반려견 탑승 | 사이드스텝, 코일매트 |
| 질문형 퀴즈 | "이 차에 뭐가 달라졌을까?" → 공개 | 그릴, 바디킷 |
| 언박싱·제품 해부 | 박스 개봉 → 소재·구조 클로즈업 | 전 브랜드 |

## 10. 영상 분석 (모드 A·B 공통)

**파일로 받은 경우** (채팅 첨부 → uploads 폴더 / 연결 폴더 → `device_stage_files`로 가져옴)
아래 스크립트를 작업 폴더에 `analyze_video.py`로 저장해 실행한다. ffmpeg·Pillow가 필요하다.
```bash
python3 analyze_video.py <영상> <출력폴더>    # 컷 전환이 너무 많거나 적으면 --threshold 0.2~0.45 조정
```
그다음 `contact_sheet.jpg`와 주요 `frames/cut_*.jpg`를 Read로 직접 보고 장면·자막을 읽는다. `transcript.txt`가 없으면(받아쓰기 라이브러리 없음) 화면 자막과 맥락으로 대사를 추정하고 "추정"이라고 표시한다. 필요하면 `pip install faster-whisper --break-system-packages` 후 재실행한다.

```python
#!/usr/bin/env python3
# 광고 영상 분석: 컷 전환 키프레임, 1초 샘플, 콘택트시트, 오디오, (가능하면) 받아쓰기
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw
def run(cmd): return subprocess.run(cmd, capture_output=True, text=True)
src, out = sys.argv[1], sys.argv[2]
th = float(sys.argv[sys.argv.index("--threshold") + 1]) if "--threshold" in sys.argv else 0.3
fd = os.path.join(out, "frames"); os.makedirs(fd, exist_ok=True)
probe = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", src]).stdout)
dur = float(probe["format"]["duration"])
v = next(s for s in probe["streams"] if s["codec_type"] == "video"); w, h = int(v["width"]), int(v["height"])
has_audio = any(s["codec_type"] == "audio" for s in probe["streams"])
r = run(["ffmpeg", "-hide_banner", "-i", src, "-vf", f"select='gt(scene,{th})',showinfo", "-vsync", "vfr", "-q:v", "3", os.path.join(fd, "cut_%03d.jpg")])
cuts = [0.0] + [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]
run(["ffmpeg", "-hide_banner", "-y", "-ss", "0", "-i", src, "-frames:v", "1", "-q:v", "3", os.path.join(fd, "cut_000.jpg")])
step = 1 if dur <= 60 else 2
run(["ffmpeg", "-hide_banner", "-i", src, "-vf", f"fps=1/{step}", "-q:v", "4", os.path.join(fd, "t_%03d.jpg")])
shots = []
for i, start in enumerate(cuts):
    end = cuts[i + 1] if i + 1 < len(cuts) else dur
    shots.append({"shot": i + 1, "start": round(start, 2), "end": round(end, 2), "len": round(end - start, 2), "frame": f"frames/cut_{i:03d}.jpg"})
thumbs = [s for s in shots if os.path.exists(os.path.join(out, s["frame"]))]
tw = 240; tph = int(tw * h / w); cols = max(1, min(6, len(thumbs))); rows = (len(thumbs) + cols - 1) // cols or 1
sheet = Image.new("RGB", (cols * tw, rows * (tph + 22)), "white"); d = ImageDraw.Draw(sheet)
for k, s in enumerate(thumbs):
    im = Image.open(os.path.join(out, s["frame"])).convert("RGB").resize((tw, tph))
    x, y = (k % cols) * tw, (k // cols) * (tph + 22)
    sheet.paste(im, (x, y)); d.text((x + 4, y + tph + 4), f"#{s['shot']} {s['start']:.1f}-{s['end']:.1f}s", fill="black")
sheet.save(os.path.join(out, "contact_sheet.jpg"), quality=85)
transcript = None
if has_audio:
    wav = os.path.join(out, "audio.wav"); run(["ffmpeg", "-hide_banner", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav])
    try:
        from faster_whisper import WhisperModel
        segs, _ = WhisperModel("small", compute_type="int8").transcribe(wav, language="ko")
        transcript = [{"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()} for s in segs]
        with open(os.path.join(out, "transcript.txt"), "w") as f:
            f.writelines(f"[{t['start']}-{t['end']}] {t['text']}\n" for t in transcript)
    except Exception as e:
        transcript = f"받아쓰기 생략({type(e).__name__}) — 화면 자막을 프레임에서 읽을 것"
summary = {"file": os.path.basename(src), "duration": round(dur, 2), "size": f"{w}x{h}", "has_audio": has_audio,
           "shot_count": len(shots), "avg_shot_len": round(dur / len(shots), 2), "shots": shots, "transcript": transcript}
json.dump(summary, open(os.path.join(out, "shots.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: summary[k] for k in ["duration", "size", "has_audio", "shot_count", "avg_shot_len"]}, ensure_ascii=False))
```

**링크로 받은 경우** (인스타 릴스·유튜브 숏츠)
- 영상을 셸로 내려받지 않는다(yt-dlp 등). 플랫폼 약관과 이 환경의 웹 접근 규칙 때문이다.
- 내장 브라우저로 링크를 연다 → `get_page_text`로 캡션·해시태그·조회수/좋아요/댓글 수를 읽는다 → `javascript_tool`로 `<video>`를 일시정지하고 `currentTime`을 0.5~1초씩 옮기며 스크린샷을 찍어 프레임을 확보한다(15초 영상이면 15~30장). 음성은 들을 수 없으니 자막·화면 텍스트로 파악하고 사운드는 "확인 불가"로 둔다.
- 로그인 벽·차단·재생 실패가 나면 2번 이상 재시도하지 말고, 사용자에게 영상 파일을 받아 첨부하거나 연결 폴더에 넣어 달라고 요청한다.

## 11. 산출물 형식

**스토리보드(소재 1개 단위)** — 상단 요약 + 씬 표 + 프롬프트 + 카피 + 체크리스트.

상단 요약: 소재 ID·파일명, 브랜드/제품/차종, 페르소나, 포맷, 컨셉 한 줄, 훅(0–3초 무엇을 보여주고 무슨 자막), 길이, 비율, 소스 구성(재활용/촬영/AI/그래픽 씬 수).

씬 표 열:
| # | 시간 | 화면(무엇이 보이나, 샷·카메라) | 화면 자막(세이프존 위치) | 내레이션/사운드 | 소스 태그 | 비고(편집 효과·전환) |

그 아래 씬별 프롬프트(§7), 카피(§8), 제작 체크리스트(필요한 실제 사진·촬영 컷 목록).

**스토리보드 JSON** — 영상 소재마다 아래 구조로 `storyboard.json`을 함께 만든다. 힉스필드 생성(§13)과 FilmCraft 패키지(§14)가 모두 이 파일을 읽으므로, 씬 표와 내용이 같아야 한다.
```json
{"id": "OG_261109_V01_차종호명-테슬라Y_9x16", "ratio": "9:16", "width": 1080, "height": 1920, "fps": 30,
 "music": {"file": "music/OG_V01_music.mp3", "start": 0, "volume_db": -14, "fade_out": 1.0},
 "scenes": [
  {"no": 1, "duration": 2.0, "source": "AI 영상", "clip": "clips/OG_V01_S01.mp4", "clip_in": 0.0,
   "caption": "테슬라 Y 오너라면 멈춰보세요",
   "higgsfield": {"model": "<models_explore로 확인한 id>", "aspect_ratio": "9:16", "duration": 5,
                  "prompt": "...", "start_image": "<실제 제품 사진 경로/URL, 없으면 생략>"}},
  {"no": 3, "duration": 4.0, "source": "실사 촬영", "clip": "clips/OG_V01_S03.mp4",
   "captions": [{"text": "광각미러로 교체하면", "offset": 0, "duration": 2}, {"text": "옆 차선이 더 넓게", "offset": 2, "duration": 2}]}
 ]}
```
- `duration`은 타임라인에 쓰는 길이, `clip_in`은 생성 클립에서 잘라 쓸 시작점. 힉스필드는 5초 단위로 뽑고 편집에서 가장 좋은 구간을 잘라 쓴다.
- 한 장면에 자막이 둘 이상이면 `captions` 배열(장면 시작 기준 offset)을 쓴다.
- `higgsfield`가 없는 장면은 실사 촬영·재활용·그래픽 컷이다.

**어디에 담나**
- 팀이 같이 보고 다시 열 결과물이므로 Artifact 페이지로 게시한다(artifact-design 스킬을 먼저 로드). 씬은 카드형으로, 레퍼런스/원본 프레임이 있으면 data URI로 넣어 나란히 보여 주고, 프롬프트마다 복사 버튼을 단다. 모바일 폭에서도 읽히게 한다.
- 스프린트 팩은 한 페이지에 [컨셉 매트릭스 / 영상 V01~V05 / 이미지 I01~I10 / 카피 / 체크리스트] 탭 구성.
- 사용자가 엑셀·구글시트를 원하면 같은 씬 표를 그 형식으로 낸다.

## 12. 기록 남기기

작업이 끝나면 프로젝트 문서 `claude/creative-log.md`에 행을 추가한다(`project_read` → 내용 추가 → 같은 경로로 `project_write`). 다음 스프린트의 중복 방지와 위너 추적에 쓴다.

```
| 날짜 | 소재 ID | 브랜드·제품·차종 | 페르소나 | 포맷 | 훅 한 줄 | 비주얼 세팅 | 출처(신규/리폼/레퍼런스 URL) | 성과(나중에 채움) |
```
브랜드 프로필에 새로 확인한 사실이 생기면 `claude/brand-profiles.md`도 갱신한다.

## 13. 힉스필드 장면 생성 (MCP)

**연결 확인**: 힉스필드 공식 MCP(`https://mcp.higgsfield.ai/mcp`, 힉스필드 계정 OAuth 로그인)가 이 세션 도구에 있는지 본다. 없으면 생성은 건너뛰고 `higgsfield_jobs.json`과 장면별 복사용 프롬프트를 산출물에 넣은 뒤, "claude.ai 설정 → 커넥터 → 커스텀 커넥터 추가에서 위 주소를 넣으면 다음부터 자동 생성된다"고 한 줄 안내한다.

**크레딧 절약 원칙 (기본값)**

아래는 2026-11-09에 `get_cost: true`로 실측한 9:16 기준 단가다. 가격은 바뀔 수 있으니 스프린트 첫 생성 전에 같은 방법으로 한 번 다시 잰다(실제 생성 없이 견적만 나온다).

| 용도 | 모델·설정 | 크레딧 |
|---|---|---|
| 키프레임(정지 이미지) 시안 | GPT Image 2.6, quality low, 1k | 0.25 |
| 광고 이미지 소재(4:5 지원) | Marketing Studio Image, 1k | 2 |
| **장면 영상 기본** | Kling 3.0, std, sound off, 3초 / 5초 | 4.5 / 7.5 |
| 시작·끝 프레임 고정 저가형 | Veo 3.1 Lite, 무음, 4초 | 6 |
| 히어로샷(제품 클로즈업) | Kling 3.0, pro, sound off, 5초 | 8.75 |
| 정밀 모션·다중 레퍼런스 | Seedance 2.5, 무음, 4초 480p / 720p / 1080p | 12 / 28 / 64 |
| 고화질 시네마틱 | Veo 3.1 fast, basic, 4초 | 16 |
| 광고 통째 템플릿 | Marketing Studio Video, 15초 720p(소리 포함) | 75 |

1. **소리는 항상 끈다**(`sound: off` / `generate_audio: false`). 음악·내레이션은 FilmCraft에서 넣는다. Kling pro 5초는 소리를 켜면 8.75→12.5로 오른다.
2. **키프레임 먼저, 영상은 나중에.** 모든 AI 장면은 0.25크레딧짜리 정지 이미지로 구도·제품 모양을 먼저 확인받고, 통과한 이미지만 `start_image`로 영상화한다. 영상 재생성(4.5~64)보다 이미지 재생성이 수십 배 싸다. 제품 장면 키프레임에는 실제 제품 사진을 `image_references`로 넣는다.
3. **기본 모델은 Kling 3.0 std.** 검수에서 품질 문제가 실제로 보일 때만 pro → Seedance 720p 순으로 올린다. 시작·끝 장면을 둘 다 고정해야 하면 Veo 3.1 Lite. 1080p·Marketing Studio Video는 성과가 확인된 위너 소재를 다시 만들 때만 쓴다.
4. **길이는 모델 최소값으로.** 2초 장면도 Kling 3초로 만든다. 5초는 동작이 길거나 `clip_in`으로 골라 쓸 여유가 꼭 필요한 장면에만 쓴다.
5. **변형은 1개씩.** `count`는 1. 훅 장면(0~3초)만 2안.
6. **재사용.** 생성 클립은 클립 라이브러리로 남겨 다른 소재·차종 변형에서 다시 쓴다(배경·상황 컷은 브랜드 간에도 공유 가능). 비율만 바꾸려면 재생성 대신 `reframe`을 먼저 견적 내 비교한다.
7. **재시도는 한 번, 원인을 고친 뒤에만.** 같은 프롬프트로 다시 돌리지 않는다. 타임아웃으로 결과가 불확실하면 같은 job id를 보고 판단한다(중복 결제 방지).
8. **예산**: 15초 영상 1편(AI 장면 4개) ≈ 키프레임 2 + 영상 30 + 재시도 여유 8 = 약 40크레딧. 2주 팩(영상 5 + 이미지 10) ≈ 브랜드당 약 220~250크레딧. 견적이 이보다 크게 나오면 이유를 적고 먼저 묻는다.
9. **사후 기록**: 스프린트가 끝나면 `transactions`로 실제 사용 크레딧을 합계해 creative-log에 소재당 비용을 적는다. 성과(CPA)와 함께 보면 어떤 설정이 돈값을 하는지 보인다.

**구글 Flow**: Flow는 2026-11 기준 공식 API·커넥터가 없다. 비공식 MCP·리버스 엔지니어링 API는 계정 제재 위험이 있어 쓰지 않는다. Flow의 핵심 모델인 Veo 3.1은 힉스필드 안에서 쓴다. 사용자가 Flow에서 직접 만들고 싶다면 장면별 8초 이하 프롬프트와 시작 이미지 목록을 복사용으로 만들어 주고, 내려받은 파일을 `clip` 경로 이름으로 저장하면 §14 패키지가 그대로 연결된다고 안내한다.

**절차**
1. **모델·파라미터 확인**: 도구 이름과 파라미터는 자주 바뀌므로 외워 쓰지 말고 매번 `models_explore`(필요하면 `presets_show`)로 현재 모델·길이·비율·시작 프레임 지원 여부를 확인한다. 고르는 기준:
   - 제품이 주인공인 장면 → 실제 제품 사진을 `media_upload`/`media_import_url`로 올려 시작 프레임·레퍼런스로 쓰는 image-to-video. 시작·끝 프레임 제어가 되는 모델(예: Kling 계열)이 유리하다.
   - 여러 제품 레퍼런스를 넣고 프롬프트로 세밀하게 움직임을 지시할 때 → Seedance 계열.
   - 상품 URL만으로 UGC·언박싱·리뷰형 광고 템플릿을 빠르게 뽑을 때 → Marketing Studio. 위너 소재의 변형 탐색용으로 좋다.
2. **비용 확인 후 승인**: 장면마다 `get_cost: true`로 크레딧을 미리 계산하고 `balance`와 함께 표(장면 / 모델 / 길이 / 크레딧 / 합계)로 보여 준 뒤 사용자가 승인하면 생성한다. 크레딧은 실제 돈이므로 승인 없이 생성하지 않는다. 사용자가 미리 "N크레딧까지 자동"이라고 정해 두면 그 안에서는 묻지 않는다.
3. **생성(2단계)**: ① `generate_image_batch`로 AI 장면 키프레임을 한 번에 만들어 콘택트시트처럼 보여 주고 고를 것을 확인받는다. ② 통과한 키프레임을 `start_image`로 넣어 `generate_video_batch`(한 번에 최대 12개)로 9:16 영상화한다. 설정은 위 절약 원칙을 따른다.
4. **대기**: `jobs_wait`/`job_status`로 완료를 기다린다(영상은 보통 1~3분). `failed`·`nsfw`는 프롬프트를 한 번 고쳐 재시도하고, 그래도 실패하면 해당 장면을 `[실사 촬영]` 또는 `[그래픽]`으로 바꾸자고 제안한다.
5. **다운로드**: 결과 URL을 스토리보드 JSON의 `clip` 경로(예: `clips/OG_V01_S01.mp4`)로 저장한다. FilmCraft 프로젝트는 사용자 컴퓨터에 있으므로 연결된 폴더에 `device_bash`로 `curl -L -o`해서 바로 넣는다. 연결 폴더가 없으면 폴더 접근을 요청한다. 클라우드에서 받아야 하면 받은 뒤 `device_commit_files`로 옮긴다. job id는 `higgsfield_jobs.json`에 기록한다.
6. **검수**: 받은 클립을 §10 스크립트로 콘택트시트를 만들어 직접 본다. 제품 형태 왜곡(매트 재단선, 미러 모양, 스텝 구조), 엠블럼·글자 생성, 손·차체 뭉개짐이 있으면 해당 장면만 재생성 후보로 표시하고 사용자에게 보여 준다.

**힉스필드용 프롬프트**: §7 형식에 더해 힉스필드 공식 예시처럼 다음을 넣는다.
- `Reference key`: 올린 이미지마다 역할 지정("Image 1 = product, keep exact shape and texture; Image 2 = location mood only").
- 5초 안의 타임 비트: "0.0–1.5s ..., 1.5–3.5s ..., 3.5–5.0s ...".
- 마지막에 `AVOID:` 목록(text, letters, logos, emblems, warped product, extra limbs).
- 한글은 생성물에 넣지 않는다. 자막은 FilmCraft에서 SRT로 얹는다.

## 14. FilmCraft 편집 패키지

FilmCraft(Rust로 만든 오픈소스 비선형 편집기)의 자체 프로젝트 파일(`.fcproj`)은 클립·자막 구조가 문서화돼 있지 않다. 그래서 FilmCraft가 공식으로 읽는 표준 교환 형식으로 만든다: **OTIO**(타임라인), **FCPXML 1.10**(세로 포맷을 명시하는 예비용), **SRT**(자막).

```bash
pip install opentimelineio --break-system-packages   # 처음 한 번
python3 build_edit_package.py storyboard.json <프로젝트폴더> --placeholders [--media-root <사용자 컴퓨터의 프로젝트폴더 절대경로>]
```
- 출력: `timeline.otio`(V1 장면 + A1 음악), `timeline.fcpxml`, `captions.srt`, `higgsfield_jobs.json`, `가져오기_안내.txt`.
- `--placeholders`: 아직 없는 클립 자리에 "SCENE 01"이 적힌 검은 임시 영상을 만든다. 힉스필드 생성 전에도 타이밍·자막을 미리 볼 수 있고, 나중에 같은 파일명으로 덮어쓰면 그대로 연결된다.
- `--media-root`: FCPXML은 절대 경로가 필요하다. 사용자 컴퓨터에서 실행하면 생략해도 된다(출력 폴더 기준).
- 가능하면 사용자 컴퓨터의 연결 폴더에서 `device_bash`로 실행해 패키지가 프로젝트 폴더에 바로 생기게 한다. opentimelineio를 설치할 수 없으면 클라우드에서 만든 뒤 `--media-root`를 지정하고 결과를 커밋한다.
- 확인된 한계(2026-11 기준, FilmCraft는 알파 단계): OTIO·FCPXML 가져오기 완성도는 약 80%이고 SRT는 약 95%다. 9:16 시퀀스 지원은 문서로 확인되지 않았다. 그래서 안내문에 "시퀀스를 1080×1920으로 먼저 만들고 가져오기, OTIO가 안 되면 FCPXML"을 적는다. 사용자가 한 번 열어 본 결과(성공/실패, 어떤 파일)를 알려 주면 `claude/brand-profiles.md` 아래 '제작 환경 메모'에 기록해 다음부터 그 형식을 기본으로 쓴다.
- 자막 스타일·위치, 음악 페이드는 교환 형식으로 정확히 옮겨지지 않으므로 안내문에 값(볼륨 dB, 페이드 초, 세이프존)을 적어 사람이 적용하게 한다.

```python
#!/usr/bin/env python3
# 스토리보드 JSON -> FilmCraft 가져오기용 편집 패키지 (OTIO + FCPXML 1.10 + SRT)
import json, os, subprocess, sys
from pathlib import Path
from xml.sax.saxutils import escape

sb = json.load(open(sys.argv[1], encoding="utf-8"))
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
root = Path(sys.argv[sys.argv.index("--media-root") + 1]) if "--media-root" in sys.argv else out
make_ph = "--placeholders" in sys.argv
W, H, FPS = sb.get("width", 1080), sb.get("height", 1920), sb.get("fps", 30)
scenes, music = sb["scenes"], sb.get("music")

def fr(sec): return int(round(sec * FPS))
def rt(sec): return f"{fr(sec) * 100}/{FPS * 100}s"
def srt_t(sec):
    ms = int(round(sec * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"
def probe(p):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
        return float(r.stdout.strip())
    except Exception: return None

missing = [s["clip"] for s in scenes if not (out / s["clip"]).exists()]
t = 0.0
for s in scenes:
    s["_start"] = t; t += s["duration"]
    p = out / s["clip"]
    if make_ph and not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        label = f"SCENE {s['no']:02d}  {s['duration']}s"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        f"color=c=black:s={W}x{H}:r={FPS}:d={max(s['duration'], s.get('clip_in', 0) + s['duration'])}",
                        "-vf", f"drawtext=text='{label}':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)])
    s["_media_dur"] = probe(p) or max(s.get("higgsfield", {}).get("duration", s["duration"]), s.get("clip_in", 0) + s["duration"])
TOTAL = t

with open(out / "captions.srt", "w", encoding="utf-8") as f:
    n = 0
    for s in scenes:
        for c in (s.get("captions") or ([{"text": s["caption"]}] if s.get("caption") else [])):
            n += 1
            a = s["_start"] + c.get("offset", 0); b = a + c.get("duration", s["duration"] - c.get("offset", 0))
            f.write(f"{n}\n{srt_t(a)} --> {srt_t(b)}\n{c['text']}\n\n")

import opentimelineio as otio
tl = otio.schema.Timeline(name=sb["id"])
tl.metadata["meta_ad"] = {"width": W, "height": H, "fps": FPS, "ratio": sb.get("ratio", "9:16")}
v = otio.schema.Track(name="V1 장면", kind=otio.schema.TrackKind.Video)
for s in scenes:
    ref = otio.schema.ExternalReference(target_url=s["clip"], available_range=otio.opentime.TimeRange(
        otio.opentime.RationalTime(0, FPS), otio.opentime.RationalTime(fr(s["_media_dur"]), FPS)))
    v.append(otio.schema.Clip(name=f"S{s['no']:02d}", media_reference=ref, source_range=otio.opentime.TimeRange(
        otio.opentime.RationalTime(fr(s.get("clip_in", 0)), FPS), otio.opentime.RationalTime(fr(s["duration"]), FPS)),
        metadata={"caption": s.get("caption", ""), "source": s.get("source", "")}))
tl.tracks.append(v)
if music:
    a = otio.schema.Track(name="A1 음악", kind=otio.schema.TrackKind.Audio)
    mdur = probe(out / music["file"]) or TOTAL
    a.append(otio.schema.Clip(name="music", media_reference=otio.schema.ExternalReference(target_url=music["file"]),
        source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(fr(music.get("start", 0)), FPS),
        otio.opentime.RationalTime(fr(min(TOTAL, mdur - music.get("start", 0))), FPS)),
        metadata={"volume_db": music.get("volume_db", -12), "fade_out": music.get("fade_out", 1.0)}))
    tl.tracks.append(a)
otio.adapters.write_to_file(tl, str(out / "timeline.otio"))

def url(rel): return (root / rel).resolve().as_uri()
res, spine = [f'<format id="r1" name="FFVideoFormatRateUndefined" frameDuration="100/{FPS*100}s" width="{W}" height="{H}"/>'], []
for i, s in enumerate(scenes):
    aid = f"a{i+1}"
    res.append(f'<asset id="{aid}" name="S{s["no"]:02d}" start="0s" duration="{rt(s["_media_dur"])}" hasVideo="1" format="r1">'
               f'<media-rep kind="original-media" src="{escape(url(s["clip"]))}"/></asset>')
    inner = ""
    if i == 0 and music:
        res.append(f'<asset id="m1" name="music" start="0s" duration="{rt(probe(out / music["file"]) or TOTAL)}" hasAudio="1">'
                   f'<media-rep kind="original-media" src="{escape(url(music["file"]))}"/></asset>')
        inner = (f'<asset-clip ref="m1" lane="-1" offset="{rt(s.get("clip_in", 0))}" start="{rt(music.get("start", 0))}" '
                 f'duration="{rt(TOTAL)}" name="music"><adjust-volume amount="{music.get("volume_db", -12)}dB"/></asset-clip>')
    spine.append(f'<asset-clip ref="{aid}" offset="{rt(s["_start"])}" start="{rt(s.get("clip_in", 0))}" '
                 f'duration="{rt(s["duration"])}" name="S{s["no"]:02d}">{inner}</asset-clip>')
xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10">\n<resources>\n' + "\n".join(res) +
       f'\n</resources>\n<library><event name="{escape(sb["id"])}"><project name="{escape(sb["id"])}">'
       f'<sequence format="r1" duration="{rt(TOTAL)}" tcStart="0s" tcFormat="NDF"><spine>\n' + "\n".join(spine) +
       '\n</spine></sequence></project></event></library>\n</fcpxml>\n')
(out / "timeline.fcpxml").write_text(xml, encoding="utf-8")

jobs = [{"scene": s["no"], "save_as": s["clip"], **s["higgsfield"]} for s in scenes if s.get("higgsfield")]
json.dump(jobs, open(out / "higgsfield_jobs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

(out / "가져오기_안내.txt").write_text(f"""{sb['id']} 편집 패키지 ({W}x{H}, {FPS}fps, 총 {TOTAL:.1f}초, 장면 {len(scenes)}개)

1. FilmCraft에서 새 프로젝트 → 시퀀스 설정을 {W}x{H}, {FPS}fps로 만든다.
2. 파일 > 가져오기에서 timeline.otio 를 연다. (영상이 가로로 잡히거나 실패하면 timeline.fcpxml 로 다시 시도)
3. captions.srt 를 가져와 자막 트랙에 올린 뒤, 스타일(굵은 고딕, 흰 글씨+검은 외곽선)을 정하고
   세이프존(위 14%, 아래 35%, 좌우 6%) 안쪽으로 위치를 맞춘다. 광고는 자막을 영상에 입혀서(번인) 내보낸다.
4. 음악(A1) 볼륨 {music.get('volume_db', -12) if music else '-'}dB, 끝 {music.get('fade_out', 1.0) if music else '-'}초 페이드아웃을 적용한다.
5. 내보내기: H.264 MP4, AAC, {W}x{H}, {FPS}fps.

아직 없는 클립(임시 화면으로 대체됨): {', '.join(missing) if missing else '없음'}
클립 파일을 같은 이름으로 넣으면 타임라인이 그대로 연결된다.
""", encoding="utf-8")
print(json.dumps({"total_sec": round(TOTAL, 2), "scenes": len(scenes), "missing_clips": missing,
                  "files": sorted(p.name for p in out.iterdir())}, ensure_ascii=False))
```

## 15. 광고 음악 (저작권 안전)

유료 광고에 쓰는 음악은 일반 게시물보다 기준이 엄격하다. 음원을 정하면 출처·라이선스·다운로드 날짜를 creative-log의 해당 소재 행에 함께 적는다(분쟁 시 증빙).

**쓰지 않는다**
- 인스타·릴스 앱 안의 인기 음악·트렌드 음원: 개인용 라이선스라 광고(부스트 포함)에는 별도 라이선스가 필요하다.
- Uppbeat 무료 플랜, Bensound 무료 트랙: 유료 광고가 라이선스에서 제외된다.
- 유튜브 오디오 라이브러리: 유튜브 밖 광고 사용 조건이 불명확하다.
- 레퍼런스 영상에 쓰인 음악.

**추천 순서**
1. **Pixabay Music** (무료): 상업적 사용 가능, 출처 표기 불필요, 수정 가능. 음원만 따로 재배포하는 것은 금지다. 광고 사용이 약관에 명시돼 있지는 않으므로 처음 한 번은 pixabay.com/service/terms 를 확인하라고 안내한다.
2. **Meta Sound Collection** (무료): 메타 광고 안에서만 쓸 수 있다고 알려져 있다. 계정 유형·지역에 따라 목록이 다르니 광고관리자에서 고를 수 있는지 확인한다.
3. **유료로 가장 안전**: Uppbeat Business(조직용, 유료 광고 허용, 연간 결제 기준 월 약 $35), Epidemic Sound Pro/Enterprise(광고 포함), Soundstripe. 소재를 2주마다 계속 만들 거라면 구독이 관리 부담이 적다.

**브랜드별 음악 방향** (Pixabay 검색어 포함). 장면 컷 전환을 비트에 맞추기 쉽도록 BPM을 정해 두고, 편집 안내문에 "컷 전환은 비트에"를 적는다.
| 브랜드 | 분위기 | BPM | 검색어 예시 |
|---|---|---|---|
| 퓨어그래스(코일매트) | 깔끔·경쾌, 생활 밀착 | 100–115 | upbeat acoustic, clean pop, happy corporate |
| 스타포쉬(사이드스텝·그릴) | 프리미엄·파워풀 | 90–100 또는 120+ | luxury trap, cinematic hits, powerful electronic, car commercial |
| 옵틱글래스(광각미러) | 긴장→해소, 신뢰감 | 100–110 | minimal tech, suspense build, modern synth corporate |
가사 있는 곡은 자막·내레이션과 겹치므로 연주곡을 기본으로 한다. 15초 광고는 곡의 하이라이트 구간을 `music.start`로 지정해 첫 3초에 에너지가 있게 한다.

## 마무리 응답

산출물 링크와 함께 2~3문장만: 무엇을 몇 개 만들었는지, 사람이 해야 할 다음 작업(촬영 컷 n개, AI 생성 n개, 확인 필요 항목). 스프린트 모드였다면 다음 교체일(시작일+14일)을 알려 준다.