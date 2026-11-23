import argparse
import json
import pathlib
import sys
from typing import Dict, Any

TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent
CATALOG_PATH = TEMPLATE_DIR / "catalog_0002_0043.json"

BG_THEME_DESCRIPTIONS = {
    "rainy_city_night_bokeh": "비 내린 직후 젖은 아스팔트 위에 네온사인과 빌딩 불빛이 반사되는 세련된 도심 야경 (Rainy modern city night street with bokeh neon reflections on wet asphalt)",
    "cable_bridge_highway_overcast": "사장교(대교)와 도시 스카이라인이 배경으로 펼쳐진 고속도로 주행 샷 (Modern cable-stayed bridge and city skyline highway driving shot)",
    "city_night_skyscrapers_blue": "푸른빛과 보랏빛 마천루 야경이 빛나는 미래지향적 도심 도로 (Futuristic blue and violet metropolitan skyscraper night road)",
    "autumn_maple_forest_road": "붉은 단풍잎이 떨어져 있는 가을 숲길 아스팔트 도로와 옅은 안개 (Autumn maple forest road with fallen red leaves and soft morning mist)",
    "rocky_mountain_offroad_dust": "바위와 흙먼지가 튀는 웅장한 설산·침엽수림 오프로드 트레일 (Dramatic rocky mountain off-road trail with dirt dust and pine forest)",
    "cyberpunk_neon_city_rain": "사이버펑크 감성의 핑크·블루 네온사인이 빛나는 비 내리는 밤거리 (Cyberpunk neon-lit rainy night street with pink and cyan reflections)",
    "coastal_modern_ architecture_daylight": "푸른 바다와 현대적인 노출 콘크리트 건축물이 어우러진 해안 도로 (Bright coastal road with modern minimalist concrete architecture and ocean view)",
    "modern_concrete_villa_night": "고급스러운 간접조명이 켜진 모던 콘크리트 건축물 앞 야간 주차 공간 (Luxury modern concrete villa courtyard at night with warm architectural lighting and wet pavement)",
    "snowy_mountain_alps_daylight": "만년설이 덮인 알프스 산맥과 침엽수림이 펼쳐진 맑은 날의 비포장 산악 도로 (Clear daylight alpine gravel road with snow-capped mountain peaks and pine trees)",
    "italian_coast_sunset": "황금빛 석양이 지는 지중해 아말피 해안 절벽 전망대 (Golden hour sunset overlooking Mediterranean coastal cliffs)",
    "genesis_showroom_daylight": "따스한 햇살과 가로수가 어우러진 프리미엄 브랜드 라운지 건축물 전면 (Warm daylight in front of a luxury automotive brand showroom with trees)",
    "european_palace_night": "따뜻한 가로등 조명이 켜진 유럽풍 클래식 석조 호텔/저택 야경 (Classic European stone mansion hotel entrance at night with warm golden lights)",
    "city_night_skyscrapers": "화려한 고층 빌딩 야경과 젖은 노면 반사가 돋보이는 대도시 밤거리 (High-contrast metropolitan night skyline with wet road reflections)",
}


def load_catalog() -> Dict[str, Any]:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_reference_by_id(ref_id: str) -> Dict[str, Any]:
    cat = load_catalog()
    norm_id = ref_id.zfill(4)
    for item in cat["references"]:
        if item["id"] == norm_id:
            return item
    raise KeyError(f"Reference ID '{ref_id}' not found in catalog_0002_0043.json (valid: 0002..0043)")


def build_hero_bg_prompt(entry: Dict[str, Any]) -> str:
    """
    코드 합성기(generate_thumbnail.py / template_studio.html)의 배경으로 사용할
    좌측 70% 히어로 차량 배경 이미지(텍스트 없는 클린 배경) 생성 프롬프트.
    그 차의 외관 사진(번호판·얼굴을 가린 사본)을 참조 이미지로 붙여서 씁니다: 차를 바꾸지 않고, 가린 번호판 커버를 그대로 두고,
    사람은 넣지 않으며, 썸네일 규칙대로 블러 없이 선명하게.
    """
    vehicle_ko = entry.get("vehicle_ko", "차량")
    vehicle_en = entry.get("vehicle_en", vehicle_ko)
    bg_key = entry.get("bg_theme", "rainy_city_night_bokeh")
    bg_desc = BG_THEME_DESCRIPTIONS.get(bg_key, bg_key).replace("bokeh ", "")  # bokeh is defocus blur: not allowed
    names = vehicle_ko if vehicle_en == vehicle_ko else f"{vehicle_en} / {vehicle_ko}"

    return f"""Commercial automotive photography, 16:9 widescreen (1280x720), ultra-detailed 8k resolution, tack-sharp.
Subject: the exact car in the attached reference photo ({names}), positioned prominently in the LEFT 70% of the frame. Keep its body shape, paint colour, wheels, lights, mirrors and trim identical to the photo; do not turn it into another model or restyle it. A dynamic 3/4 front view facing toward the center-right is preferred.
License plate: keep the plate cover exactly as it appears in the reference photo (white "Optic-Glass" cover with a small red emblem). Never render a readable registration number.
People: no people, faces, hands or reflections of people anywhere in the image.
Environment: {bg_desc}.
Composition & 70:30 Visual Balance (CRITICAL):
- Frame the hero vehicle prominently across the left 65%~70% of the canvas (x: 2% to 68%, y: 28% to 94%) so the entire car body is clearly visible and unobstructed.
- Leave the top-left sky/background (y: 0% to 28%) and the right 30% of the frame (x: 70% to 100%) as clean, darker atmospheric negative space so Korean headline typography and compact before/after mirror comparison cards can be overlaid without covering the vehicle.
- Keep the car and the scene in sharp focus: no depth-of-field blur, no motion blur, no haze over the car.
- Do NOT render any text, logos, watermarks, badges or UI boxes in the image, and no legible letters on shop or neon signs either (only the plate cover may show "Optic-Glass"). Pure automotive hero background only."""


def generate_image(prompt: str, out_path: pathlib.Path, images: list) -> pathlib.Path:
    """video-automation/work/llm.py의 thumbnail_image 작업으로 이미지 생성 (Antigravity 구독, agy). images는 참조 사진
    최대 3장이며 PC 밖으로 나가므로 번호판·얼굴을 가린 사본만 넘깁니다."""
    work = str(TEMPLATE_DIR.parents[1] / "video-automation" / "work")
    if work not in sys.path:
        sys.path.insert(0, work)
    import llm

    return llm.generate_image("thumbnail_image", prompt, images, out_path)


def make_ai_background(exterior: pathlib.Path, car_name: str, out_path: pathlib.Path, ref_id: str = "0031") -> pathlib.Path:
    """그 차의 가린 외관 사진 1장으로 ref_id 레퍼런스 장면의 히어로 배경을 만듭니다. 제목·시공 전/후 카드·로고는
    generate_thumbnail.py가 실제 사진과 Paperlogy 폰트로 그 위에 합성합니다 (AI가 미러 비교 사진을 그리지 않도록)."""
    entry = dict(get_reference_by_id(ref_id), vehicle_ko=car_name, vehicle_en=car_name)
    return generate_image(build_hero_bg_prompt(entry), out_path, [exterior])


def main():
    parser = argparse.ArgumentParser(description="옵틱글래스 썸네일 AI 히어로 배경 프롬프트 (0002~0043 레퍼런스 장면)")
    parser.add_argument("--id", type=str, default="0031", help="레퍼런스 번호 (0002 ~ 0043, 기본값: 0031)")
    parser.add_argument("--vehicle", type=str, help="차 이름 (예: '2026 포르쉐 마칸 EV')")
    parser.add_argument("--call-gemini", action="store_true",
                        help="Antigravity 구독(agy, API 키 없음)으로 즉시 이미지 생성 실행")
    parser.add_argument("--exterior-img", type=str, help="첨부할 외관 사진 (번호판·얼굴을 가린 사본: media/<slug>/thumb/car_exterior.jpg)")
    parser.add_argument("--out", type=str, default="out_gemini_thumbnail.png", help="생성 이미지 저장 경로")

    args = parser.parse_args()
    if args.call_gemini and not (args.exterior_img and args.vehicle):
        parser.error("--call-gemini에는 --exterior-img(가린 사본)와 --vehicle(그 사진의 차 이름)이 필요합니다")

    entry = dict(get_reference_by_id(args.id))
    if args.vehicle:
        entry["vehicle_ko"] = entry["vehicle_en"] = args.vehicle  # not the reference car's English name
    prompt = build_hero_bg_prompt(entry)
    print(f"=== [레퍼런스 #{entry['id']}] {entry['vehicle_ko']} 히어로 배경 프롬프트 ===\n{prompt}")
    if args.call_gemini:
        saved = generate_image(prompt, pathlib.Path(args.out), [pathlib.Path(args.exterior_img)])
        print(f"\n[이미지 생성 완료] {saved}")


if __name__ == "__main__":
    main()
