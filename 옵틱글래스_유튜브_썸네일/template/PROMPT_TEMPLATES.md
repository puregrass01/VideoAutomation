# 옵틱글래스 유튜브 썸네일 생성 템플릿 가이드 (`0002_img` ~ `0043_img` 레퍼런스)

이 디렉토리(`옵틱글래스_유튜브_썸네일/template`)는 `0002_img` ~ `0043_img` 레퍼런스의 레이아웃·타이포그래피를 재현하는 코드 기반 썸네일 합성기와, 그 배경으로 쓸 AI 히어로 배경 프롬프트를 담고 있습니다. 파이프라인(`gdrive_pipeline.py` Stage 3)은 항상 그 차의 가린 사진 3장으로 합성합니다.

---

## 1. 구성 파일

| 파일명 | 역할 |
|---|---|
| `옵틱글래스 로고.png` | **공식 옵틱글래스 브랜드 로고 원본 에셋** (투명 배경 RGBA 693×153, 주황·레드 그라데이션 초승달+점 심볼 및 화이트 `Optic-Glass` 워드마크) |
| `generate_thumbnail.py` | **Python Pillow 기반 1280×720 썸네일 합성기** (`generate_thumbnail()`, `render_split_horizontal`·`render_split_vertical`): 그 차 외관 사진 배경 + `Paperlogy-9Black` 2줄 헤드라인 + 시공 전/후 카드 2장 + 공식 로고, 블러 없음. 외관·시공 전·시공 후 사진이 모두 있어야 하며 다른 차 사진으로 대체하지 않습니다 |
| `template_studio.html` | **브라우저 기반 인터랙티브 썸네일 스튜디오** (이미지 드래그 앤 드롭, 대표 프리셋 전환, 실시간 텍스트/컬러 수정, 1280×720 PNG/JPG 다운로드) |
| `prompt_generator.py` | **AI 히어로 배경 프롬프트 빌더** (`build_hero_bg_prompt`, `make_ai_background`): 가린 외관 사진 1장으로 텍스트 없는 배경을 agy로 생성 |
| `catalog_0002_0043.json` | `0002` ~ `0043` 레퍼런스의 레이아웃 프리셋(`split_horizontal`, `split_vertical`), 세부 스타일, 2줄 타이틀·강조색·배경 테마 명세 DB |
| `samples/` | `template_studio.html`이 보여 주는 샘플 이미지 |

---

## 2. 빠른 실행 방법 (CLI)

### ① 코드 기반 1280×720 썸네일 합성 (`generate_thumbnail.py`)

```powershell
# 특정 레퍼런스 스타일(예: 0031 좌우 비교형)로 그 차의 가린 사진 3장 합성
py "옵틱글래스_유튜브_썸네일\template\generate_thumbnail.py" `
  --id 0031 `
  --bg "차량배경.jpg" `
  --before "시공전_순정미러.jpg" `
  --after "시공후_광각미러.jpg" `
  --line1 "2026 포르쉐 마칸 EV" `
  --line2 "광각미러 차이!" `
  --out "output_macan.jpg"
```

### ② AI 히어로 배경 (`prompt_generator.py`)

이미지 생성은 Antigravity 구독(agy, 데스크톱 앱과 같은 계정, API 키 없음)으로 에이전트의 `generate_image` 도구를 씁니다. 첨부 사진은 PC 밖으로 나가므로 번호판·얼굴을 가린 사본(`media/<차 폴더>/thumb/*.jpg`, `drive_index.media_dir`)만 넘깁니다.

파이프라인에서는 GUI의 **AI 배경** 버튼(= `gdrive_pipeline.py --vehicle <slug> --skip-video-rebuild --ai-bg`)이 가린 외관 사진 1장으로 히어로 배경을 만들고, 제목·시공 전/후 카드·로고는 `generate_thumbnail.py`가 실제 사진과 Paperlogy 폰트로 합성해 `thumbnail_ai_1280x720_split_*.jpg`를 만듭니다. AI는 미러 비교 사진이나 글자를 그리지 않습니다.

```powershell
# 레퍼런스 번호(0002~0043) 장면으로 배경 프롬프트만 출력
py "옵틱글래스_유튜브_썸네일\template\prompt_generator.py" --id 0034 --vehicle "2026 기아 카니발 하이리무진"

# 가린 외관 사진으로 배경 즉시 생성
py "옵틱글래스_유튜브_썸네일\template\prompt_generator.py" `
  --id 0031 `
  --vehicle "2026 테슬라 사이버트럭" `
  --exterior-img "구글드라이브다운파일\media\cybertruck\thumb\car_exterior.jpg" `
  --call-gemini `
  --out "ai_bg_0031.png"
```
