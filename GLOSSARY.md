# GLOSSARY

옵틱글래스 영상 자동화에서 정해진 말. 코드와 문서는 이 이름을 쓴다.

**장면 역할 (role)**: 시나리오 씬 하나가 보여 주는 것. `longform_common.ROLES`의 하나: exterior, detail, card(「광각미러가 꼭 필요한 이유」 카드), before(순정 쪽 보조 장면), install(시공 과정), after(옵틱 미러 시야), compare_before / compare_after(비교 구간의 단독 전/후 컷), split(50:50 분할), close(마무리), outro. 규칙은 역할에서 나온다: after·compare_after·split은 화살표 4개, compare_*·split은 전후 전환 금지, 미러 시야 역할에는 시공 장면 금지. _쓰지 않는 말_: "compare 씬", "s13/s14 분할 씬" (번호는 시나리오마다 다름).

**미러 시야 (mirror view)**: 운전석에서 본 사이드미러 화면. 순정(mirror_before)과 옵틱글래스(mirror_after). 비교·시공 후·썸네일 전/후 칸은 미러 시야만 쓴다.

**시공 장면 (install shot)**: 유리를 빼고 붙이는 손·하우징 장면 (install_stock / install_optic). before·install 역할에만 쓴다.

**결과물 검사 (output check)**: `check_text_outputs.check_draft`. 빌드한 CapCut 초안이 규칙과 시나리오를 지키는지 배포 전에 본다. 실패하면 capcut_stage에만 남는다.

**리포트**: 실행이 촬영 자료 부족이나 규칙 위반으로 멈출 때 `output/<차>/report.txt`에 쓰는 100자 안팎의 이유. GUI가 작업이 끝날 때 메시지박스로 띄운다.
