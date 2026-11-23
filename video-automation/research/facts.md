# 조사 근거 자료 (2026-10-16)

HERMES.md의 '확인된 사실'에 대한 근거입니다. 두 개의 다중 에이전트 조사 결과를 그대로 옮겼습니다.
**'검증 정정 사항'이 각 조사 각도의 내용보다 우선합니다.** 날짜가 지난 사실(별 수, 버전)은 다시 확인한 뒤 쓰세요.

## 1. 검증 정정 사항 (우선 적용)

- **[capcut-encryption]** 원래 주장: 'Filmcraft'라는 이름의 MCP·영상 편집 프로젝트는 웹 검색 2회로도 찾지 못했다.
  - 정정: storytold/filmcraft가 존재합니다(2026-09-30 생성, Apache-2.0 감지·README는 MIT OR Apache-2.0, 2026-10-16 기준 13,929★, v0.8.0 2026-10-14). 이 PC에는 C:/Program Files/FilmCraft에 filmcraft.exe와 filmcraft-cli.exe가 2026-10-15 14:57에 설치돼 있고, `filmcraft-cli --version`은 0.8.0을 출력합니다. Downloads에는 artcraft-launcher-0.3.2-windows-x64.msi도 있습니다.
  - 근거: https://api.github.com/repos/storytold/filmcraft (2026-10-16 조회); 로컬 C:/Program Files/FilmCraft (ls, --version)
- **[task LOCAL FACTS / portable-stack / filmcraft]** 원래 주장: CapCut 9.6(오늘 저장분)이 draft_content.json을 암호화한다. 즉 9.6에서 암호화가 시작됐다.
  - 정정: 암호화된 2건('57.08 벤츠', '롱폼')은 모두 root_meta_info.json에 draft_cloud_last_action_download=true, tm_draft_cloud_space_id=7327545136085664770이 찍혀 있습니다. 벤츠는 2026-05-26 17:01(8.5.0 시절)에 이미 암호화됐습니다. 반대로 같은 팀 스페이스에서 받은 '숏폼 영상 프로젝트 (1)/(2)'는 평문입니다. 이 PC에서 9.6.0으로 저장된 draft(last_modified_platform.app_version=9.6.0)는 하나도 없습니다. 따라서 '9.6이 로컬 신규 draft나 도구가 만든 draft를 암호화하는지'는 아직 미검증입니다. 이 점에서는 capcut-encryption 각도의 해석이 맞습니다.
  - 근거: 로컬 읽기 전용 스캔: .../com.lveditor.draft/root_meta_info.json, */draft_content.json 첫 바이트·last_modified_platform (2026-10-16)
- **[task LOCAL FACTS / portable-stack]** 원래 주장: 암호화된 draft에는 crypto_key_store.dat가 있다(암호화의 지표).
  - 정정: '롱폼 영상 프로젝트'(암호화)에는 crypto_key_store.dat가 없습니다. 반면 평문인 '0729'에는 2,092B짜리 파일이 있고, '57.08 벤츠'(암호화)에는 183B짜리가 있습니다. 실제로 쓸 수 있는 판별 기준은 draft_content.json 첫 바이트가 '{'인지 여부와 draft_virtual_store.json의 {"is_encrypted":true,"path":"draft_content.json"} 항목입니다.
  - 근거: 로컬 ls: 롱폼 영상 프로젝트/, 0729/, 57.08 벤츠 지바겐 광각 [26.04.13]/
- **[capcut-mcp / capcut-encryption]** 원래 주장: 9.4.0·9.5.0에서 마지막으로 저장한 draft는 평문이다(capcut-mcp). 9.6.0도 평문 초안을 직접 만든다(숏폼 (2), capcut-encryption).
  - 정정: '숏폼 영상 프로젝트 (2)'의 last_modified_platform은 app_version 9.4.0, device_id 01bb6bac…, os_version 10.0.26200입니다. 이 PC는 device_id 0ceb7058…, os_version 10.0.26300이므로 다른 기기입니다. '옵틱글래스 광각미러 템플릿 1'도 같은 기기의 9.5.0 저장본입니다. 이 PC의 Apps 폴더에는 9.1.0.3879 다음 버전이 9.6.0.4097뿐이라 9.4와 9.5는 설치된 적이 없습니다. 따라서 9.6.0이 평문으로 저장하는지, 도구가 만든 draft를 여는지에 대한 증거가 되지 못합니다.
  - 근거: 로컬 grep last_modified_platform/platform; ls C:/Users/bssho/AppData/Local/CapCut/Apps
- **[capcut-mcp]** 원래 주장: '옵틱글래스 광각미러 템플릿 1'의 draft_content.json은 평문이라 쓸 수 있다(메타만 비JSON).
  - 정정: 루트 draft_content.json은 평문('{')입니다. 그러나 Timelines/*/draft_content.json 16개와 draft_meta_info.json은 모두 비JSON입니다. capcut-cli 문서에 따르면 9.2.8+는 Timelines/<id>를 우선 읽습니다. 그러니 루트 평문만으로 pyCapCut load_template를 돌리면 오래된 사본이나 부분 사본을 템플릿으로 쓰게 될 위험이 있습니다.
  - 근거: 로컬 head -c1 옵틱글래스 광각미러 템플릿 1/Timelines/*/draft_content.json; https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/version-support.md
- **[capcut-mcp]** 원래 주장: '57.08 벤츠 지바겐 광각 [26.04.13]' 폴더는 루트에 파일이 없어 암호화 여부를 확인하지 못했다.
  - 정정: 루트에 draft_content.json(552,888B, 첫 바이트 'fh7hykbG…' 비JSON), crypto_key_store.dat(183B), template.json.bak(3,933B) 등이 있습니다. 암호화돼 있으며 Timelines 3개도 비JSON입니다.
  - 근거: 로컬 ls/head: .../57.08 벤츠 지바겐 광각 [26.04.13]/
- **[reference-analysis]** 원래 주장: FilmCraft의 타이틀/텍스트(graphics.*, titles.*)와 전환 적용 명령은 문서화되지 않았다.
  - 정정: docs/graphics.md와 `filmcraft-cli commands`에 graphics.newText(text, position, box, size, font, seconds, track, time), graphics.set(font, fill_color, stroke, shadow…), graphics.setText, graphics.template.apply(.fcgt), sequence.applyVideoTransition, effects.addKeyframe/setKeyframe, file.exportInterchange(edl|xml|fcpxml|otio|aaf|omf)가 있습니다. 명령은 총 701개입니다. 이 PC에서 헤드리스로 run(JSONL) → graphics.newText('한글 자막 테스트', Malgun Gothic) → render PNG → 2초 MP4 export까지 모두 exit 0으로 성공했습니다(export 0.4s). 한글 셰이핑도 정상이었습니다.
  - 근거: https://raw.githubusercontent.com/storytold/filmcraft/main/docs/graphics.md; 로컬 C:/Program Files/FilmCraft/filmcraft-cli.exe (--data-dir를 scratchpad로 지정해 실행, 2026-10-16)
- **[reference-analysis]** 원래 주장: FilmCraft GitHub Releases 항목이 비어 있다.
  - 정정: Releases API에 v0.8.0(2026-10-14), v0.7.2(2026-10-12) 등이 있습니다. v0.8.0에는 windows-x64.msi, portable.zip, arm64, x86, macOS dmg, Linux, FreeBSD, web 자산이 있습니다.
  - 근거: https://api.github.com/repos/storytold/filmcraft/releases
- **[portable-stack]** 원래 주장: FilmCraft는 사본으로만 쓰고 납품용으로 쓰지 말라고 안내한다.
  - 정정: README에는 'alpha', 'Ready for real work: ~56%'(2026-10-10 Premiere Pro 26.5.2 대비 재측정), '카메라·폰 파일은 덜 테스트됨' 정도만 있습니다. 사본 사용이나 납품 금지에 대한 문구는 없습니다. alpha라서 위험하다는 평가 자체는 타당합니다.
  - 근거: https://raw.githubusercontent.com/storytold/filmcraft/main/README.md
- **[portable-stack]** 원래 주장: Remotion은 MCP 경로가 폐기돼 스킬·CLI 방식만 남았다(단점으로 제시).
  - 정정: Remotion 문서는 'The Remotion MCP is deprecated'라고 하고, hosted 서버는 2026-08-31 이후 종료되며 대체는 Agent Skills(/remotion-docs)라고 안내합니다. 렌더 능력은 원래 CLI와 Lambda에 있었으므로 잃은 기능은 없습니다. 라이선스는 1차 출처로 확인했습니다. 무료 대상은 개인, 직원 3명 이하 영리조직, 비영리, 평가 목적입니다. 4명 이상이면 Company License가 필요하고, Creators는 좌석당 $25/월(3석 $75), Automators는 렌더당 $0.01·월 최소 $100, Enterprise는 월 $500부터입니다. 5.0에서 라이선스가 '약간' 바뀔 예정입니다.
  - 근거: https://www.remotion.dev/docs/ai/mcp ; https://www.remotion.pro/license ; https://raw.githubusercontent.com/remotion-dev/remotion/main/LICENSE.md
- **[reference-analysis]** 원래 주장: pyCapCut 원본 레포의 마지막 push는 2025-09경이다(제3자 인덱스).
  - 정정: pushed_at은 2026-10-15T07:04:59Z이고 705★, license는 null입니다. 마지막 커밋은 'Fix: Restore masks in newer CapCut versions'(fc86c9e)입니다.
  - 근거: https://api.github.com/repos/GuanYixuan/pyCapCut
- **[capcut-mcp / filmcraft]** 원래 주장: 로컬 pyCapCut은 @00c223a이고 main보다 13커밋 뒤처져 있다.
  - 정정: 로컬 pyCapCut은 fix/template-mode-data-loss 브랜치입니다. HEAD 00e08e6('Prevent draft data loss and template mode bugs')이 origin/main fc86c9e 위에 올라가 있습니다. 이전 로컬 수정은 stash@{0}에 보존돼 있습니다. 푸시나 PR은 하지 않았습니다.
  - 근거: 로컬 git -C C:/Users/bssho/Downloads/paperclip-master/pyCapCut log/branch/stash list
- **[reference-analysis]** 원래 주장: pyJianYingDraft 문서상 'CapCut 7 이상' 자동 export가 미지원이다(2차 출처).
  - 정정: pyJianYingDraft README의 원문은 '剪映7+版本对控件进行了隐藏…仅支持剪映6及以下版本'입니다. 국제판 CapCut에서는 pyCapCut JianyingController가 창 이름 '剪映专业版'을 찾다가 실패합니다. 이슈 #17은 open 상태이고, 메인테이너는 2026-09-25에 9.5.0.4050의 export 대화상자가 UIA와 MSAA에 자식 컨트롤을 노출하지 않는다고 답했습니다. pyCapCut README에도 '批量导出: 本模块正在迁移中'이라고 돼 있습니다. 결론적으로 CapCut 국제판 export 자동화는 현재 경로가 없습니다.
  - 근거: https://raw.githubusercontent.com/GuanYixuan/pyJianYingDraft/main/README.md ; https://github.com/GuanYixuan/pyCapCut/issues/17 ; 로컬 pyCapCut/README.md:25-30, pycapcut/jianying_controller.py:222
- **[filmcraft / reference-analysis]** 원래 주장: VectCutAPI의 template_fit은 4다(CapCut 형식을 MCP로 바로 생성하므로 템플릿에 맞다).
  - 정정: mcp_server.py의 도구 11개(create_draft, add_*, add_video_keyframe, get_video_duration, save_draft)는 모두 새 draft를 생성하는 쪽입니다. TS mcp-server의 14개 중 capcut_read_project는 요약만 읽고, capcut_reload_desktop은 Windows UI 재오픈입니다. 렌더나 export 도구는 없습니다. 기본 profile은 jianying_pro_10(剪映 10.2.0/windows)입니다. capcut_legacy는 app_version 6.5.0, os mac으로 하드코딩돼 있습니다. capcut-mcp 각도의 template_fit 2가 타당합니다.
  - 근거: https://raw.githubusercontent.com/sun-guannan/VectCutAPI/main/mcp_server.py ; .../mcp-server/src/tools/index.ts ; .../draft_profiles.py
- **[capcut-encryption]** 원래 주장: KyaniteLabs/mcp-video는 목록상 29 stars다.
  - 정정: KyaniteLabs/mcp-video는 KyaniteLabs/kinocut으로 리다이렉트됩니다. 206★, Apache-2.0, 2026-10-15 push입니다.
  - 근거: https://api.github.com/repos/KyaniteLabs/mcp-video
- **[filmcraft]** 원래 주장: fancyboi999/capcut-mcp는 1년 넘게 갱신이 없다(정체).
  - 정정: archived=true, 95★, 마지막 push 2025-08-21, license null입니다. 채택 후보에서 제외해야 합니다.
  - 근거: https://api.github.com/repos/fancyboi999/capcut-mcp
- **[local-cli]** 원래 주장: 레시피의 segment_ref는 '레시피 순서 기준 op_N'으로 계산하면 된다.
  - 정정: session.append_operation은 add_effect/add_filter에 track이 없으면 add_track op를 먼저 재귀로 추가합니다(_DEDICATED_TRACK_OPS, session.py:34-37, 158-171). _next_op_id는 전체 operations 길이로 번호를 매깁니다(session.py:686-691). 따라서 레시피 순서로 op_N을 계산하면 어긋납니다. CLI를 순차 호출해 반환된 id를 받아 쓰거나, effect/filter op에 track을 명시해야 합니다. 같은 각도가 지적한 다른 결함도 로컬에서 확인했습니다. recipe id 폐기(recipe.py:84-94)와 fade 인자 불일치(plan.py:48,52가 in_duration/out_duration을 안내하는데 op_handlers.py:421-422는 fade_in/fade_out을 읽음)입니다.
  - 근거: 로컬 cli-anything-capcut-main/cli_anything/capcut/core/session.py, core/recipe.py, core/op_handlers.py, commands/plan.py
- **[filmcraft / portable-stack]** 원래 주장: FilmCraft는 Windows 11 크래시 이슈 때문에 이 PC에서 동작이 불확실하다(스모크 테스트 필요).
  - 정정: Windows 11 Pro 26300에서 filmcraft-cli 0.8.0으로 --demo inspect, render PNG(11ms@0.25배), JSONL run, 한글 텍스트, MP4 export가 모두 성공했습니다. 이슈 #380('does not even run on win11 x64')과 bridge 버그 #1538은 여전히 open이고, 폴더 제한 PR #985도 open입니다. 그러니 bridge 모드와 GUI는 여전히 위험하고, 헤드리스 CLI 경로는 쓸 만하다고 보정해야 합니다.
  - 근거: 로컬 실행(scratchpad, --data-dir 격리); https://api.github.com/repos/storytold/filmcraft/issues/380 , /1538 , /985

### 각도 간 모순

- 암호화 원인을 두고 각도끼리 충돌합니다. portable-stack·filmcraft·task 로컬 사실은 '9.6이 암호화', capcut-encryption은 '클라우드 다운로드 draft별 플래그'라고 봅니다. 로컬 재확인 결과는 후자 쪽입니다. 벤츠는 8.5.0 시절에 이미 암호화됐습니다.
- crypto_key_store.dat에 대한 설명이 서로 다릅니다. task 사실과 portable-stack은 '암호화 draft에 존재', capcut-mcp·capcut-encryption은 '지표 아님'입니다. 로컬 확인 결과 지표가 아닙니다.
- '숏폼 (2)'와 '옵틱글래스'의 저장 버전이 엇갈립니다. capcut-mcp는 9.4.0/9.5.0 저장, capcut-encryption은 9.6.0 다운로드라고 합니다. 실제로는 다른 기기의 9.4/9.5 저장본을 이 PC의 9.6.0이 클라우드로 내려받은 것입니다. 이 PC에는 9.4와 9.5가 설치된 적이 없습니다.
- 'Filmcraft' 존재 여부: filmcraft·portable-stack·reference-analysis·local-cli는 storytold/filmcraft로 특정했습니다. capcut-encryption과 capcut-mcp는 '찾지 못함'이라고 했습니다. 실제로는 존재하고 로컬에도 설치돼 있습니다.
- FilmCraft 릴리스: filmcraft·portable-stack은 v0.1.0~v0.8.0 릴리스를, reference-analysis는 'Releases 비어 있음'을, local-cli는 '릴리스·날짜 미확인'이라고 했습니다. Releases API에 존재합니다.
- FilmCraft 텍스트·전환 명령: reference-analysis는 '문서 없음', filmcraft·portable-stack은 '650+ 명령으로 가능'이라고 했습니다. graphics.md와 CLI로 존재를 확인했습니다.
- FilmCraft 납품 적합성: portable-stack은 'README가 납품 비권장'이라고 했지만 다른 각도에는 그런 언급이 없고 README에도 없습니다.
- pyCapCut 활동성: reference-analysis는 '2025-09 마지막 push', capcut-mcp는 '2026-10-15 커밋'이라고 했습니다. 후자가 맞습니다.
- VectCutAPI template_fit 점수가 2(capcut-mcp)와 4(filmcraft, reference-analysis)로 갈립니다. 코드상 템플릿 로드·교체가 없으므로 2가 맞습니다.
- 자동 export 범위: capcut-mcp는 '剪映 6 이하', reference-analysis는 'CapCut 7+ 미지원'이라고 했습니다. 원문은 剪映 기준이고, 국제판 CapCut은 버전과 무관하게 컨트롤러가 미지원입니다.
- fancyboi999/capcut-mcp: capcut-encryption은 archived, filmcraft는 단순 정체라고 했습니다. API 기준 archived=true입니다.
- mcp-video(Kinocut) star 수가 29(capcut-encryption)와 약 205(portable-stack, reference-analysis)로 다릅니다. 현재 206★이고 kinocut으로 이름이 바뀌었습니다.
- 전략 결론이 각도마다 갈립니다. portable-stack은 HyperFrames를 1순위로 두고 CapCut을 보조로, capcut-mcp·capcut-encryption·local-cli는 CapCut CLI 코어에 MCP 추가 없이, filmcraft는 CapCut 1차·FilmCraft 2차로, reference-analysis는 spec-first 두 컴파일러를 제안했습니다. 공통분모는 'MCP 추가 없이 .md → 중립 spec/recipe'입니다.

### 아무도 다루지 않은 부분

- 사용자의 실제 '.md 템플릿' 파일을 아무도 보지 못했습니다(Downloads 검색에서도 미발견). CapCut 고유 효과명이나 resource_id가 들어 있는지, 장면 타이밍 정밀도가 어느 정도인지에 따라 CapCut·FilmCraft·HyperFrames 중 어느 쪽이 맞는지가 바뀌는데, 이 가장 큰 변수가 비어 있습니다.
- '다운받은 CapCut 템플릿'의 출처를 아무도 확인하지 않았습니다(CapCut 템플릿 스토어인지, 팀 스페이스 공유 draft인지). 로컬 암호화 draft는 모두 팀 스페이스(space_id 7327545136085664770) 다운로드분입니다. 롱폼 template.json.bak에는 placeholder_infos가 있습니다. 스토어 템플릿이면 CapCut 도움말상 수익화가 꺼진 템플릿은 '초안 편집 불가'이고 원작자 소재는 보호됩니다.
- 이미 설치된 FilmCraft v0.8.0을 대상으로 한 실측이 없었습니다. 이번 검증에서 헤드리스 render와 export, 한글 텍스트는 확인했습니다. 남은 것은 실제 촬영 소스(폰 HEVC/HDR, 이 PC 소재 중 'hlg' PNG 등) 디코드, 9:16 시퀀스(sequence.settings), 긴 렌더 성능, .fcgt 템플릿화 실험입니다.
- 사람 마감 경로로 '이미 설치된 Adobe Premiere Pro 2021'(C:/Program Files/Adobe)을 아무도 고려하지 않았습니다. FilmCraft는 file.exportFcp7Xml, exportFcpxml, exportOtio를 지원하므로 FilmCraft에서 생성하고 Premiere에서 마감하는 경로가 가능할 수 있습니다(Premiere 2021의 FCP7 XML import 호환성은 미검증).
- Downloads에 remotion-main.zip(약 597MB, 2026-10-16)이 있는데, 모노레포 소스를 쓸지 npm 패키지(`npx create-video`, `npx skills add remotion-dev/skills`)를 쓸지에 대한 논의가 없습니다. 조직 인원 기준 라이선스 해당 여부도 확인되지 않았습니다.
- CapCut 9.6.0이 '도구가 쓴 평문 draft'를 열 수 있는지 아무도 실측하지 않았습니다(공개 실측은 9.3.0까지). 이번 검증도 drafts 폴더 쓰기 금지 때문에 하지 못했습니다. capcut-cli 매트릭스의 CapCut 10.x 행은 '외부 작성 draft를 손상으로 거부'라는 보고와 write-guard 상태인데, 자동 업데이트로 10.x가 들어올 경우의 대응을 다룬 각도가 없습니다.
- CapCut 자동 업데이트 통제가 빠져 있습니다. 2026-10-15에 9.1.0에서 9.6.0으로 사용자 개입 없이 업데이트됐습니다. 업데이트 직후 스모크 테스트를 자동으로 돌리는 방법은 capcut-encryption 각도만 언급했습니다.
- 평가 방법이 없습니다. 레퍼런스 대비 재현도를 어떻게 측정할지(프레임 SSIM이나 지각 지표, 컷 타이밍 오차 허용치)와 사람 검수 비용을 비교하는 기준이 정의되지 않았습니다.
- 음원과 폰트 라이선스(CapCut 내장 상용 폰트·음원을 다른 렌더러로 옮길 수 있는지)를 다룬 각도가 없습니다. CapCut ToS 10조는 Company Content를 제한적 라이선스로만 허용합니다(capcut-encryption 인용, 이번에 재검증은 하지 않음).

### 전략 리스크

- 'CapCut 템플릿을 그대로 재현'하려는 전략의 전제가 약합니다. 사용자가 가진 것은 .md 설명서이고, 원본 draft 중 팀 스페이스분은 일부 암호화돼 있습니다. 평문 루트 파일도 Timelines 쪽이 암호화돼 있을 수 있습니다(옵틱글래스). pyCapCut 템플릿 모드는 평문만 읽고 Timelines는 쓰지 않으므로, '루트 평문만 보고 템플릿으로 쓰기'는 조용히 잘못된 결과를 낼 수 있습니다.
- CapCut 경로에는 최종 MP4 자동화가 없습니다. pyCapCut의 export 컨트롤러는 剪映专业版 창 전용이고(이슈 #17 open), 9.5.0 export 대화상자는 UIA 자식 컨트롤을 노출하지 않습니다. cli-anything-capcut render-headless는 효과·필터·애니메이션·텍스트 위치를 버리는 ffmpeg 근사입니다. 게다가 이 PC에는 ffmpeg가 PATH에 없습니다. 무인 MP4가 요구사항이라면 CapCut은 '편집 가능한 산출물'로만 남습니다.
- 9.6.0 호환성이 미검증입니다. 도구가 쓴 draft의 GUI 실측은 9.3.0이 마지막이고, 'unconventional path' 거부(8.4+/8.7 보고)와 10.x 손상 거부 보고가 있습니다. 같은 recipe를 9.6.0에서 한 번 열어 보기 전에 CapCut을 코어로 고정하면 위험합니다.
- cli-anything-capcut을 '그대로' 쓰면 조용히 실패합니다. recipe id 폐기, duration 'auto'가 0µs로 처리됨, 미등록 op(import_srt/add_color_adjust), fade 인자 불일치, auto-added add_track으로 인한 op_N 밀림(local-cli 지적과 이번 확인)이 있습니다. 에이전트가 만든 recipe는 review --fail-on-warning과 GUI 확인 없이 믿으면 안 됩니다.
- FilmCraft는 생성된 지 약 16일 된 alpha입니다(약 1일 1릴리스, open 이슈와 PR 1,057건). bridge 모드 버그(#1538 open)가 있고 폴더 제한이 없어 사용자 권한이 닿는 모든 경로를 읽고 쓸 수 있습니다(#985 open). v0.8.0 고정, 헤드리스 전용, 전용 작업 폴더 사용이 필수입니다. 명령 이름과 파라미터가 v1 전에 바뀔 수 있으니 JSONL 생성기를 얇게 유지해야 합니다.
- HyperFrames는 스타 수(64,709)와 활동성은 높지만 0.x에 거의 매일 릴리스됩니다. Windows 렌더 실측이 없고, Node 22+, FFmpeg, Puppeteer Chromium이 필요합니다(ffmpeg 미설치). README에 MCP 서버가 없어 '스킬+CLI' 방식만 가능합니다.
- Remotion은 영리조직 직원 4명 이상이면 유료입니다(Creators $25/좌석/월 또는 Automators 렌더당 $0.01·월 최소 $100). 5.0에서 라이선스가 바뀔 예정이라 비용 전제가 변할 수 있습니다. 내려받은 remotion-main.zip(모노레포)을 빌드해 쓰는 것은 불필요한 복잡성입니다.
- MCP를 추가하는 이득이 거의 없습니다. CapCut MCP 계열은 생성 전용이고 렌더가 없습니다(VectCutAPI는 템플릿 로드 없음, capcut_legacy 마커 6.5.0/mac, fancyboi999 archived, dlyrr 404). FilmCraft MCP도 CLI(run JSONL)와 같은 엔진입니다. Claude Code처럼 셸이 있는 에이전트라면 CLI가 더 단순합니다.
- 복호화 우회(jy-draftc, 온라인 복호화, PR #189 방식)는 CapCut 약관 6조의 decipher/circumvent 금지와 저작권법 104조의2 리스크가 있습니다. pyJianYingDraft와 capcut-cli 메인테이너도 거절했습니다. 팀 draft를 외부 사이트에 올리면 유출 위험도 있습니다. 템플릿 원본이 필요하면 평문 상태에서 사본을 확보하는 것 말고는 정당한 경로가 없습니다.
- 중립 spec, CapCut 컴파일러, FilmCraft 컴파일러, HyperFrames 컴파일러를 동시에 만드는 것은 과잉입니다. 템플릿 1~2개로 같은 spec을 CapCut(9.6 열림 확인)과 FilmCraft 헤드리스(이미 설치·동작 확인)에 렌더해 비교한 뒤, 하나를 기본으로 정하고 나머지는 필요할 때 추가하는 순서가 안전합니다.

## 2. 조사 각도별 결과

### capcut-mcp

2026-10-15 기준으로 CapCut/剪映 MCP·API를 조사했고, 결론은 다섯 가지입니다.

(1) ByteDance/CapCut의 공식 공개 편집·렌더 API나 공식 MCP는 찾지 못했습니다. 전부 서드파티이고, 모두 로컬 drafts 폴더에 draft 파일을 쓰는 방식입니다.

(2) 'CapCut MCP'라는 이름이 붙은 프로젝트 대부분은 VectCutAPI(구 CapCutAPI)나 그 래퍼입니다. 이들은 draft를 '처음부터 생성'하는 도구라서 기존 템플릿 불러오기, 소재 교체 같은 tool이 없습니다. 템플릿 모드(load_template/replace_material/replace_text)는 MCP가 아니라 pyCapCut·pyJianYingDraft 같은 라이브러리에 있고, 기존 draft 편집은 capcut-cli, JmsLdrn/capcut-mcp, cutauto 정도가 지원합니다. 이것들도 전부 평문(plaintext) JSON만 읽습니다.

(3) 암호화된 draft를 읽는 도구는 하나도 없습니다. pyJianYingDraft와 capcut-cli는 법적·유지보수 리스크를 이유로 복호화를 명시적으로 거부합니다. VectCutAPI 메인테이너도 "암호화돼서 처리 불가"라고 답했습니다.

(4) MP4 렌더도 로컬에서 깔끔하게 되는 게 없습니다. 남는 길은 CapCut GUI에서 수동 export, Windows UI 자동화(capcut-mate gen_video, pyJianYingDraft export는 剪映 6 이하만), 비공개 유료 클라우드 렌더(VectCut, jcaigc, cutcli)뿐입니다.

(5) CapCut 8.7~9.x는 앱 밖에서 만든 draft를 'unusual/unconventional path'로 거부하거나, 중첩 Timelines/의 내용을 우선 읽는다는 보고가 있습니다. 10.x는 외부 작성 draft를 손상으로 거부한다는 보고가 있습니다. 그래서 오래된 템플릿 마커로 생성하는 MCP(VectCutAPI capcut_legacy=6.5.0)는 최신 CapCut에서 위험합니다.

사용자가 가진 '템플릿'은 CapCut draft가 아니라 .md 설명서입니다. 그래서 'CapCut MCP가 CapCut 템플릿에 맞는다'는 전제는 실제로 성립하지 않습니다. 어떤 도구를 쓰든 .md를 타임라인으로 재구성하는 생성 작업이 필요합니다.

로컬에서 실측한 내용(읽기 전용):
- 2026-10-15에 생성된 '롱폼 영상 프로젝트'는 draft_content.json, template-2.tmp, draft_meta_info.json이 base64 형태의 비JSON입니다. 이 폴더에는 crypto_key_store.dat가 없습니다.
- 반대로 평문인 0729 draft(9.1.0)에는 crypto_key_store.dat가 있습니다. 따라서 keystore 파일이 있다고 암호화된 것은 아닙니다.
- 9.4.0, 9.5.0에서 마지막으로 저장한 draft는 여전히 평문입니다.

**권장:**

결론: 'CapCut MCP'(VectCutAPI 계열)를 코어로 쓰지 마세요. 지금 쓰는 pyCapCut과 cli-anything-capcut CLI+skill을 코어로 유지하고, 그 위에 '마스터 템플릿 draft와 소재·텍스트 교체' 구조를 얹는 게 가장 현실적입니다. VectCutAPI 계열은 템플릿 로드·교체 tool이 없고, 암호화 draft를 처리하지 못하고, 렌더는 비공개 유료 클라우드이고, platform 마커(6.5.0/mac)가 오래돼 9.x에서 거부될 위험이 있습니다. 결국 'CapCut 템플릿에 맞다'는 장점이 실제로는 없습니다.

1) .md → recipe 변환: 에이전트가 .md(장면, 타이밍, 텍스트, 효과)와 레퍼런스 영상·이미지를 cli-anything-capcut의 recipe JSON으로 바꿉니다. .md는 draft가 아니라서 어떤 MCP를 써도 이 재구성 단계는 필요합니다.

2) 마스터 템플릿 draft를 사람이 한 번 만듭니다:
- 복잡한 룩(花字, 텍스트 효과, 복합 클립)은 CapCut GUI에서 레퍼런스를 보고 1회 제작합니다.
- 첫 바이트가 '{'인지 확인해 평문인 동안 drafts 폴더 밖에 읽기 전용 사본으로 보관합니다.
- 이후에는 pyCapCut duplicate_as_template, replace_material_by_name, replace_text로 변형본을 대량 생성합니다.
- 9.6에서 다시 저장하면 암호화될 수 있습니다. 템플릿 원본은 9.6에서 다시 열어 저장하지 말고, 백업본에서 복제하세요.

3) 로컬 pyCapCut을 main으로 올립니다. 13커밋이 뒤처져 있고, 그 사이 신버전 마스크, 텍스트 효과 폰트, 메인트랙 자석 수정이 들어갔습니다. 그 다음 9.6.0에서 생성 draft가 열리는지 GUI로 재검증합니다(검증은 9.3.0까지만 돼 있음).

4) capcut-cli(MIT, 활발)는 교체 대상이 아니라 보조 도구로 쓰세요. doctor, diagnose, lint(암호화·마커·미디어 링크 진단), sync-timelines(9.x 중첩 Timelines), seed-from-store 아이디어를 가져오면 됩니다.

5) 암호화 대응: 복호화 도구를 도입하지 마세요. pyJianYingDraft와 capcut-cli 모두 법적·약관상 이유로 거부하고 있고, 알고리즘도 버전마다 바뀝니다. 대신 CapCut 버전과 설치 파일을 고정·보관하고, 쓰기 전에 버전을 확인합니다. 9.x가 외부 draft를 거부하면 앱에서 만든 빈 shell에 주입하는 패턴으로 우회합니다.

6) MCP가 꼭 필요할 때만(Claude Desktop처럼 셸이 없는 클라이언트) 이 CLI를 감싸는 얇은 MCP를 만드세요. 그 전에 기존 draft 편집용으로 JmsLdrn/capcut-mcp를 참고할 수 있습니다.

7) 최종 MP4: CapCut에는 공식 렌더 API가 없습니다. 선택지는 수동 export, Windows GUI 자동화(취약), 외부 유료 클라우드(소재 업로드 필요)뿐입니다. 사람 검수 없이 MP4까지 자동으로 뽑아야 한다면, 렌더는 B안(ffmpeg/Remotion 계열 'Filmcraft & MCP')에 맡기는 하이브리드가 맞습니다. 이때 CapCut은 '편집 가능한 draft 산출물'용으로 둡니다.

| 선택지 | 템플릿 적합 | 이식성 | 성숙도 |
|---|---|---|---|
| VectCutAPI (sun-guannan, 구 CapCutAPI) — Python mcp_server.py / TS mcp-server | 2/5 | 3/5 | 인기·활발한 편입니다(2,302★, 483 fork, Apache-2.0, 2026-10-12 push). 다만 최근 커밋은 대부분 README 수정이고, 마지막 기능 병합은 PR #80(2026-09-12)입니다. 클라우드 렌더, 웹 클라이언트, MCP 에이전트 코드는 비공개입니다. |
| Atx-Guy/capcut-mcp-server 및 MigueDuque/capcut-mcp-server-extended | 1/5 | 3/5 | Atx-Guy는 72★이고, 2026-01-13에 생성된 뒤 push가 1회뿐입니다(README 기준 MIT). MigueDuque는 10★, MIT, 2026-03-17이 마지막 push입니다. 둘 다 저활동입니다. |
| hey-jian-wei/jianying-mcp | 1/5 | 3/5 | 307★지만 2025-08-22 이후 push가 없어 정체 상태입니다. Apache-2.0 배지가 있으나 GitHub API에서는 license가 감지되지 않았습니다. |
| JmsLdrn/capcut-mcp | 3/5 | 4/5 | 초기 단계입니다(9★, 커밋 1개, MIT, 2026). 효과·전환·리치 텍스트는 best-effort라고 명시돼 있습니다. |
| dlyrr/capcut-mcp | 2/5 | 2/5 | glama 목록에는 v1.0.0(2026-08-08)으로 올라와 있지만, 2026-10-15 현재 GitHub repo는 404입니다. 작성자 스스로 CapCut 앱에서 실제로 테스트한 적은 없다고 밝혔습니다. |
| renezander030/capcut-cli (CLI, MCP 아님) | 4/5 | 5/5 | 매우 활발합니다(895★, MIT, npm v0.29.0 2026-10-09, 2026-10-14에도 커밋). 버전별 증거 수준을 명시한 지원 매트릭스를 운영합니다. |
| pyCapCut / pyJianYingDraft + cli-anything-capcut (현재 로컬 스택) | 4/5 | 4/5 | pyCapCut은 705★이고 2026-10-15 오늘도 커밋(신버전 CapCut 마스크 복구)이 있습니다. 로컬 @00c223a는 main보다 13커밋 뒤처져 있습니다. repo에 LICENSE 파일이 없고 PyPI pycapcut 0.0.3(2025-08)은 오래됐습니다. pyJianYingDraft는 4,571★, Apache-2.0, 0.3.1(2026-10-14)입니다. cli-anything-capcut은 7★, MIT, 2026-09-21 push입니다. |
| Hommy-master/capcut-mate | 2/5 | 3/5 | 활발합니다(약 2.0k★, 289 fork, 670 커밋, 2026-10-14 커밋, Apache-2.0). 정식 release는 없습니다. |
| Hommy-master/cutauto | 3/5 | 4/5 | 소규모입니다(24★, 2 fork, 26 커밋, MIT). 최근 커밋 날짜는 확인하지 못했습니다. |
| @cutcli/cutcli + cutsdk | 2/5 | 4/5 | npm 1.1.8(2026-06-11)입니다. npm 메타에 MIT라고 돼 있지만 소스 repository 링크가 없고 운영 주체도 확인하지 못했습니다. |
| App-shell inject 패턴 (zxypro1/capcut-shell-inject 레시피) | 3/5 | 3/5 | 레시피 수준입니다. CapCut 9.3.0 macOS에서 검증됐다는 보고만 있습니다. |

**사실과 근거:**

- sun-guannan/VectCutAPI: Apache-2.0, 2,302★, 483 fork, 2025-07-11에 생성, 마지막 push 2026-10-12. sun-guannan/CapCutAPI는 VectCutAPI로 리다이렉트됩니다(Moved Permanently). — https://api.github.com/repos/sun-guannan/VectCutAPI (2026-10-15 조회, 신뢰도 high)
- VectCutAPI의 Python MCP tool은 create_draft, add_video, add_audio, add_image, add_text, add_subtitle, add_effect, add_sticker, add_video_keyframe, get_video_duration, save_draft 11개입니다. 템플릿 load나 소재 replace tool은 없습니다. TS mcp-server는 여기에 capcut_list_projects, capcut_read_project, capcut_reload_desktop을 추가합니다. — https://github.com/sun-guannan/VectCutAPI/blob/main/mcp_server.py ; https://github.com/sun-guannan/VectCutAPI/blob/main/mcp-server/src/tools/index.ts (main 브랜치 2026-10-15 조회 (TS MCP는 PR #80, 2026-09-12 병합), 신뢰도 high)
- VectCutAPI save_draft는 dfd_ 폴더를 생성하고, 이걸 CapCut/剪映 drafts 폴더로 복사해야 합니다. 기본 draft_profile은 jianying_pro_10(剪映 10.2.0 마커)입니다. capcut_legacy 프로필의 platform은 app_version 6.5.0, os mac으로 하드코딩돼 있습니다. — https://github.com/sun-guannan/VectCutAPI/blob/main/draft_profiles.py ; README.md (2026-10-15 조회, 신뢰도 high)
- VectCutAPI README는 클라우드 렌더링 모듈, 웹 편집 클라이언트, MCP 편집 에이전트 코드가 오픈소스가 아니라고 밝힙니다. 클라우드 렌더 인터페이스는 docs.vectcut.com으로 안내됩니다(이슈 #67). skill 문서의 /export_draft_to_video는 오픈소스 capcut_server.py 라우트에 없습니다. — https://github.com/sun-guannan/VectCutAPI/issues/67 ; README.md ; vectcut-skill/skill/references/api_reference.md (이슈 답변 2026-04-08, 코드 2026-10-15 조회, 신뢰도 high)
- VectCutAPI 메인테이너는 기존 剪映 draft 편집 질문에 '加密了处理不了'(암호화돼서 처리 불가)라고 답했습니다. — https://github.com/sun-guannan/VectCutAPI/issues/47 (2025-10-10 closed, 신뢰도 high)
- VectCutAPI 이슈 #71: load_template와 dump를 거치면 기존 draft의 sticker/text/effect segment가 조용히 누락됩니다. — https://github.com/sun-guannan/VectCutAPI/issues/71 (2026-06-05 closed, 신뢰도 medium)
- Atx-Guy/capcut-mcp-server는 VectCutAPI 백엔드가 있어야 동작하는 TS MCP입니다(11 tool, README상 MIT). 72★이고 2026-01-13에 생성된 이후 push가 없습니다. MigueDuque 포크는 MIT, 10★, 2026-03-17이 마지막 push입니다. — https://github.com/Atx-Guy/capcut-mcp-server ; https://github.com/MigueDuque/capcut-mcp-server-extended (2026-10-15 조회, 신뢰도 high)
- hey-jian-wei/jianying-mcp는 pyJianYingDraft 기반 剪映 MCP입니다(307★). 마지막 push는 2025-08-22입니다. — https://github.com/hey-jian-wei/jianying-mcp (2026-10-15 조회, 신뢰도 high)
- JmsLdrn/capcut-mcp는 기존 draft에서 segment/material 템플릿을 복제해 편집하는 MCP입니다(MIT, 9★, 커밋 1개). CapCut 실행 중에는 저장을 거부하고, 효과·전환·애니메이션은 best-effort라고 명시합니다. — https://github.com/JmsLdrn/capcut-mcp (2026-10-15 조회, 신뢰도 high)
- dlyrr/capcut-mcp는 glama에 v1.0.0(2026-08-08)으로 등재돼 있지만 GitHub 주소는 404를 반환합니다. — https://glama.ai/mcp/servers/dlyrr/capcut-mcp ; https://github.com/dlyrr/capcut-mcp (2026-10-15 조회, 신뢰도 medium)
- pyCapCut: 705★, 마지막 커밋 2026-10-15('Fix: Restore masks in newer CapCut versions'). 로컬 00c223a는 main보다 13커밋 뒤처져 있습니다. repo에 LICENSE 파일과 license 메타가 없고, PyPI pycapcut 최신은 0.0.3(2025-08-14)입니다. — https://api.github.com/repos/GuanYixuan/pyCapCut/compare/00c223a...main ; https://pypi.org/pypi/pycapcut/json (2026-10-15 조회, 신뢰도 high)
- pyCapCut 템플릿 모드는 '(암호화되지 않은) draft_content.json' 로드, 소재 교체, 텍스트 교체, 트랙 import, 메타 추출을 지원합니다. 생성한 draft는 Windows판 CapCut에서 export해야 하고, 일괄 export 모듈은 아직 이전 작업 중입니다. — https://github.com/GuanYixuan/pyCapCut/blob/main/README.md (2026-10-15 조회, 신뢰도 high)
- pyJianYingDraft 0.3.0에서 사용자 정의 draft 로더 인터페이스(fallback_loader)가 추가됐습니다. 프로젝트는 서드파티 암호화 포맷 복호화 구현을 내장·배포·링크하지 않으며, 내장 제안은 거버넌스·컴플라이언스 리스크로 닫혔다고 명시합니다. 자동 export는 剪映 6 이하에서만 동작합니다. — https://github.com/GuanYixuan/pyJianYingDraft/releases/tag/0.3.0 ; README.md (0.3.0: 2026-07-08, 0.3.1: 2026-10-14, 신뢰도 high)
- renezander030/capcut-cli: MIT, 895★, npm 0.29.0(2026-10-09), 2026-10-14에도 커밋. MCP 서버나 HTTP 데몬 없이 JSON in/out으로 동작하고 실험적인 WASM 읽기 전용 MCP 3종이 있습니다. render는 저해상도 ffmpeg 프록시이며 CapCut 최종 렌더가 아닙니다. — https://cdn.jsdelivr.net/npm/capcut-cli@0.29.0/README.md ; https://github.com/renezander030/capcut-cli (2026-10-15 조회, 신뢰도 high)
- capcut-cli는 암호화 draft를 '감지만 하고 복호화하지 않는다'는 방침입니다. 같은 문서는 'CapCut International은 암호화되지 않고 剪映만 암호화'(2026-09 기준 증거)라고 하는데, 이는 로컬 9.6 관찰과 충돌합니다. — https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md (2026-09 기준 문서, 2026-10-15 조회, 신뢰도 high)
- capcut-cli 버전 매트릭스에 정리된 사례: 번들 6.5.0 템플릿으로 만든 draft는 CapCut 8.7.0 Windows에서 'unusual path'로 거부됐습니다(#111, 2026-09-10). 설치된 앱의 draft로 seed하면 9.3.0에서 round-trip이 성공했습니다. 9.2.8-beta는 Timelines/<id>/draft_info.json을 우선 읽습니다. 10.x는 외부 작성 draft를 손상으로 거부한다는 보고가 있어 쓰기 차단(write-guard) 상태입니다. — https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/version-support.md (2026-10 문서, 2026-10-15 조회, 신뢰도 medium)
- zxypro1/capcut-shell-inject에 따르면 CapCut 9.x는 앱 밖에서 생성된 draft를 '비정상 경로'로 거부합니다. 앱에서 빈 shell을 만들고 종료한 뒤 주입하는 방식은 9.3.0 macOS에서 동작했다고 합니다. — https://github.com/zxypro1/capcut-shell-inject (2026-09(레시피 내용), 2026-10-15 조회, 신뢰도 medium)
- Hommy-master/capcut-mate: Apache-2.0, 약 2.0k★, 670 커밋, 2026-10-14 커밋. gen_video는 'Windows 전용'이고 windows extra 의존성으로 pywin32, pyautogui, uiautomation(GUI 자동화)을 씁니다. 호스팅판 렌더에는 jcaigc.cn apiKey가 필요합니다. — https://github.com/Hommy-master/capcut-mate ; docs/gen_video.md ; pyproject.toml (2026-10-15 조회, 신뢰도 high)
- Hommy-master/cutauto는 미리 등록한 CapCut 템플릿(tpls/)을 로드해 소재를 교체하고 draft를 일괄 생성하는 FastAPI 서비스입니다(MIT, 24★, 26 커밋, pyJianYingDraft 내장). — https://github.com/Hommy-master/cutauto (2026-10-15 조회, 신뢰도 medium)
- @cutcli/cutcli 1.1.8(2026-06-11)은 draft 생성과 API token 기반 클라우드 렌더를 제공하는 CLI입니다. npm 메타에 소스 repository가 없습니다. — https://registry.npmjs.org/@cutcli/cutcli (2026-06-11 게시, 2026-10-15 조회, 신뢰도 medium)
- 검색 범위 안에서 CapCut/ByteDance의 공식 공개 편집·렌더 API나 공식 MCP를 찾지 못했습니다. 서드파티 프로젝트들도 모두 'CapCut has no public API'를 전제로 합니다. — WebSearch(2026-10-15) ; https://glama.ai/mcp/servers/goransmoljanovic015-cell/capcut-mcp-server (2026-10-15, 신뢰도 medium)
- CapCut 템플릿 라이브러리에서 받은 프로젝트는 draft_info.json이 암호화돼 있어 수정할 수 없다는 서드파티 skill의 주장이 있습니다(macOS 기준). — https://www.skills.sh/duckyman-ai/agent-skills/capcut-editor (2026-10-15 조회(작성일 미상), 신뢰도 low)
- pyJianYingDraft PR #198(열림 상태): 剪映 11.4.0 macOS는 도구가 쓴 평문 draft_info.json을 열고 그 자리에서 암호화 포맷으로 업그레이드합니다. 즉 암호화는 '읽기'만 막고 '새 draft 쓰기'는 막지 않으며, 옛 파일명 draft_content.json을 쓰면 '草稿内容已损坏' 오류가 납니다. — https://github.com/GuanYixuan/pyJianYingDraft/issues/198 (2026-09-10, 신뢰도 medium)
- VectCutAPI repo에 포함된 capcut-director skill에 따르면 CapCut 9.x+는 Timelines/<UUID>/draft_content.json을 읽으며, 루트 파일만 쓰면 빈 타임라인이 열립니다. — https://github.com/sun-guannan/VectCutAPI/blob/main/.agents/skills/capcut-director/SKILL.md (2026-10-15 조회, 신뢰도 medium)
- 로컬 관찰(읽기 전용): 2026-10-15에 생성된 '롱폼 영상 프로젝트'는 draft_content.json(504,644B), .bak, template-2.tmp, draft_meta_info.json이 base64 형태의 비JSON입니다(첫 바이트 'BEFFa0eA…'). 이 폴더에는 crypto_key_store.dat가 없고, 평문 JSON인 template.json.bak(348,679B)이 함께 있습니다. 반면 평문인 0729 draft(app_version 9.1.0)에는 crypto_key_store.dat가 있으므로 keystore 존재가 곧 암호화를 뜻하지 않습니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/롱폼 영상 프로젝트/ ; .../0729/ (2026-10-15 로컬 확인, 신뢰도 high)
- 로컬 관찰: app_version 9.4.0('숏폼 영상 프로젝트 (2)')과 9.5.0('옵틱글래스 광각미러 템플릿 1')에서 마지막으로 저장한 draft_content.json은 평문입니다(단 후자의 draft_meta_info.json은 비JSON). '57.08 벤츠 지바겐 광각 [26.04.13]' 폴더는 루트에 파일이 없어 암호화 여부를 확인하지 못했습니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/ (2026-10-15 로컬 확인, 신뢰도 high)
- 로컬 cli-anything-capcut GUI 실측: CapCut 9.3.0.3970(Windows)에서 CLI로 생성한 draft가 목록에 뜨고 정상적으로 열렸습니다. 폰트는 materials.texts[].content의 styles[].font{id,path}를 넣어야 적용되며, id 키가 빠지면 CapCut이 크래시합니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/docs/capcut-gui-verification.md:6-122 (2026-09-01, 신뢰도 high)

**미해결 질문:**

- 'Filmcraft & MCP'가 정확히 어떤 프로젝트인지 찾지 못했습니다. 검색에서 해당 이름이 확인되지 않아 repo URL이 필요합니다.
- CapCut 9.6.0에서 무엇이 암호화를 일으키는지 모릅니다(9.6에서 새로 만든 draft인지, 클라우드 동기화인지, 특정 기능 사용인지). 9.6에서 빈 프로젝트를 새로 만들어 저장한 뒤 draft_content.json 첫 바이트를 확인하는 실험이 필요합니다.
- pyCapCut과 cli-anything-capcut이 생성한 평문 draft가 9.6.0에서 열리는지, 열어서 저장하면 9.6이 암호화로 덮어쓰는지 확인해야 합니다(剪映 9.0/11.4 사례처럼).
- 암호화된 '롱폼' draft 옆의 평문 template.json.bak이 최신 타임라인인지 오래된 스냅샷인지 확인하지 못했습니다.
- 사용자가 받은 '.md 템플릿'은 CapCut 템플릿 라이브러리 항목에서 나온 것인지, 그리고 그 원본 draft에 접근할 수 있는지 알아야 합니다. 템플릿 라이브러리 프로젝트는 암호화돼 있다는 서드파티 주장이 있습니다.
- 최종 MP4까지 무인 자동화가 필수인지, CapCut GUI에서 사람이 export해도 되는지에 따라 하이브리드 렌더 경로가 필요한지가 갈립니다.
- pyCapCut에 LICENSE가 없는데, 상업적 사용이나 재배포가 계획돼 있다면 저자에게 라이선스를 확인해야 합니다.
- GitHub API 호출 한도에 걸려 capcut-mate, cutauto, JmsLdrn의 정확한 최근 push 날짜 일부는 확인하지 못했습니다.

### filmcraft

사용자가 말한 'Filmcraft & MCP'는 GitHub의 storytold/filmcraft(FilmCraft)입니다. 이 이름을 쓰는 제품 중 'MCP 지원 + AI 에이전트 이식성'이라는 설명에 맞는 것은 이것 하나입니다. ArtCraft 팀(조직명 storytold)이 만든 순수 Rust 오픈소스 NLE(비선형 편집기)이며, Premiere Pro를 클린룸 방식으로 다시 구현했습니다. 라이선스는 MIT OR Apache-2.0이고 무료입니다. 저장소는 2026-09-30에 만들어졌고(현재 약 15일 경과), 최신 버전은 v0.8.0(2026-10-14)입니다. 2주 동안 9번 릴리스됐고 스타는 약 13.5k입니다. 프로젝트는 .fcproj(UTF-8 JSON, schema_version 13, 시간 단위 254,016,000,000 ticks/s)로 저장됩니다. 650개가 넘는 엔진 명령을 UI, CLI, JSON-lines TCP 제어 채널, MCP(stdio) 서버가 똑같이 호출합니다. 렌더링에는 FFmpeg를 쓰지 않습니다. 자체 Rust 코덱과 wgpu GPU 합성(CPU 경로도 있음)을 쓰고, `filmcraft-cli export`로 GUI 없이 MP4를 렌더링할 수 있습니다. Windows, macOS, Linux, FreeBSD, WebAssembly를 지원합니다.
다만 아직 alpha입니다. 자체 평가로 'Ready for real work'가 약 56%(2026-10-10 측정)입니다. Windows 11 시작 크래시 이슈, MCP bridge 모드 버그가 열려 있고, PR CI도 없습니다. CapCut 드래프트, CapCut 템플릿, 타 앱 템플릿(.mogrt 포함) 가져오기는 지원하지 않으며 의도적으로 거부합니다. 효과·전환·텍스트 라이브러리도 CapCut이 아니라 Premiere 기준입니다. 그래서 'CapCut 템플릿 .md → 재현' 용도라면 FilmCraft로는 근사 재구성만 됩니다. 컷, 타이밍, 텍스트, 키프레임 줌, 전환, 자막 정도가 가능하고, CapCut 고유 텍스트 애니메이션, 스티커, 필터, 효과는 그대로 재현할 수 없습니다.
같은 이름의 다른 제품도 있습니다. filmcraft.tools는 독립 운영되는 유료 생성형 AI(MiniMax H3) 수정 서비스로, 타임라인 편집기가 아니고 MCP도 없습니다. filmcraft.online은 같은 엔진의 웹 빌드로, 호스팅 MCP(mcp.artcraftweb.org)가 있다고 하지만 저장소 문서에서는 확인하지 못했습니다. filmcraft.shop은 제3자 위키입니다. `filmcraft-mcp`라는 이름의 별도 npm, PyPI, GitHub 패키지는 찾지 못했습니다.

**권장:**

결론부터 말하면 'CapCut MCP냐 FilmCraft냐' 중 하나를 고르기보다, 백엔드에 종속되지 않는 중간 레시피를 원본으로 두고 백엔드 두 개를 붙이는 방식을 권합니다.

1) 원본(Source of truth): 다운로드한 CapCut 템플릿 .md와 레퍼런스 영상·이미지를 에이전트가 레시피 JSON으로 바꿉니다. 레시피에는 장면, 시작·길이(초), 미디어 슬롯, 텍스트, 전환, 키프레임, 효과 의도가 들어갑니다. cli-anything-capcut에 이미 있는 recipe JSON 스키마를 그대로 확장하면 됩니다.

2) 1차 백엔드는 CapCut 경로입니다(템플릿을 충실히 재현하는 것이 우선일 때). 이미 설치된 cli-anything-capcut과 pyCapCut을 쓰고, 토큰 효율이 좋은 CLI를 MCP보다 우선합니다. CapCut 고유 텍스트 애니메이션, 필터, 효과, 스티커가 필요한 템플릿은 이 경로만 원본에 가깝게 재현할 수 있습니다. 단, 9.6 계열로 저장한 드래프트는 암호화돼서 template mode로 읽을 수 없습니다. 그러니 '기존 드래프트를 읽는 방식' 대신 '.md에서 새 드래프트를 생성하는 방식'으로 설계하세요. 템플릿 원본 드래프트가 꼭 필요하면 암호화되지 않은 9.1.0 시절 드래프트만 쓰세요. VectCutAPI MCP는 대안이나 참고용으로만 보는 게 좋습니다.

3) 2차 백엔드로 FilmCraft를 붙입니다(이식성과 완전 headless 자동화가 필요할 때). 대상은 컷, 텍스트, 키프레임 줌, 전환, 자막 위주의 단순한 템플릿입니다. `filmcraft-cli run script.jsonl`과 `filmcraft-cli --project p.fcproj export out.mp4`로 GUI 없이 MP4까지 뽑을 수 있습니다. 같은 엔진을 MCP headless 모드(`filmcraft-cli mcp --project p.fcproj`)로 띄우면 render_frame PNG를 레퍼런스 이미지와 비교하는 검증 루프를 에이전트가 직접 돌릴 수 있습니다. 이 점은 CapCut 경로보다 확실히 낫습니다.

FilmCraft를 쓸 때 주의할 점은 다음과 같습니다.
(a) v0.8.0(2026-10-14)으로 버전을 고정합니다. 매일 릴리스가 나오고 alpha이며 Ready 약 56%입니다.
(b) bridge 모드는 피하고 headless 모드를 씁니다. bridge에는 #1538, #1539 버그가 열려 있습니다.
(c) 폴더 제한 기능이 없으니 전용 작업 폴더에서만 쓰고 원본 미디어는 복사해 둡니다.
(d) CapCut 고유 효과는 '대체 매핑 표'를 만들어 근사합니다.
(e) Windows 11 크래시 이슈가 있으니 먼저 MSI나 portable로 `filmcraft-cli --demo inspect sequence`, `export` 스모크 테스트를 해 보세요.

filmcraft.tools(유료 생성형 서비스)와 filmcraft.online의 호스팅 MCP(공식 여부 미확인)는 이 파이프라인에 넣지 않는 것을 권합니다. 실행 순서는 다음과 같습니다. 템플릿 1–2개를 골라 .md를 레시피로 바꾸고, 같은 레시피를 CapCut 백엔드와 FilmCraft 백엔드로 각각 렌더링합니다. 그다음 레퍼런스와의 시각적 차이와 수작업 보정 시간을 비교해, 템플릿 유형별로 기본 백엔드를 정합니다.

| 선택지 | 템플릿 적합 | 이식성 | 성숙도 |
|---|---|---|---|
| FilmCraft (storytold/filmcraft) — 공식 MCP/CLI 포함 데스크톱 NLE | 2/5 | 5/5 | alpha. 저장소 생성 2026-09-30, v0.1.0(2026-10-02)부터 v0.8.0(2026-10-14)까지 9번 릴리스. 스타 13,497, 포크 5,538, 이슈와 PR을 합친 open 936건(2026-10-15 기준). 자체 평가 Feature breadth 약 86%, Ready for real work 약 56%(2026-10-10). PR에서 테스트를 돌리는 CI 없음(gaps.md G4). MCP 관련 open 이슈 36건. |
| filmcraft.tools — 'filmcraft AI Video Editor'(동명의 다른 제품) | 1/5 | 1/5 | 상용 SaaS이며 출시일은 확인하지 못했습니다(© 2026). 월 $14.9–$99.9 크레딧 요금제입니다. |
| filmcraft.online — FilmCraft 웹(WASM) 빌드 + 호스팅 MCP(공식 여부 미확인) | 2/5 | 3/5 | 'Early alpha'로 표기돼 있습니다. 운영 주체가 명시되지 않았습니다. 저장소 docs/web.md에는 window.filmcraft JS API만 있고 이 호스팅 MCP 도메인은 찾지 못했습니다. |
| cli-anything-capcut v0.5.7 + pyCapCut (로컬에 이미 있음, CapCut 경로) | 4/5 | 2/5 | 로컬 설치본은 패치된 pyCapCut @00c223a입니다. 이번 조사에서 원격 저장소의 활성도는 다시 확인하지 않았습니다. |
| VectCutAPI (sun-guannan/VectCutAPI, 구 CapCutAPI) — CapCut/JianYing 드래프트 생성 MCP | 4/5 | 3/5 | 스타 약 2.3k, 마지막 push 2026-10-12, Apache-2.0입니다. GitHub Releases는 비어 있습니다. 클라우드 렌더 모듈은 오픈소스가 아닙니다. |
| fancyboi999/capcut-mcp | 3/5 | 2/5 | 스타 95개, 마지막 push 2025-08-21로 1년 넘게 갱신이 없습니다. 라이선스는 GitHub에서 감지되지 않았습니다. |

**사실과 근거:**

- 'FilmCraft' 공식 저장소는 storytold/filmcraft이며, 설명은 'An open-source, nonlinear video editor written by scratch in pure Rust', 홈페이지는 https://getartcraft.com/apps/filmcraft입니다. — https://api.github.com/repos/storytold/filmcraft (2026-10-15, 신뢰도 high)
- 저장소 생성일 2026-09-30, 마지막 push 2026-10-15, 스타 13,497, 포크 5,538, open_issues_count 936(이슈와 PR 합계)입니다. GitHub가 감지한 라이선스는 Apache-2.0이고, README는 MIT OR Apache-2.0 듀얼이라고 적고 있습니다. — https://api.github.com/repos/storytold/filmcraft (2026-10-15, 신뢰도 high)
- 릴리스는 v0.1.0(2026-10-02), v0.1.1(10-03), v0.2.0(10-05), v0.2.1(10-06), v0.4.0(10-08), v0.5.0(10-10), v0.6.0(10-11), v0.7.2(10-12), v0.8.0(10-14)입니다. v0.8.0 에셋에는 windows-x64.msi, portable.zip, arm64, x86, macOS dmg, filmcraft-cli macOS zip, Linux 여러 포맷, FreeBSD, filmcraft-web zip이 있습니다. — https://api.github.com/repos/storytold/filmcraft/releases (2026-10-15, 신뢰도 high)
- `filmcraft-cli mcp`는 MCP를 stdio로 제공합니다. headless 모드(--demo 또는 --project p.fcproj)와 bridge 모드(--bridge 127.0.0.1:9876, `filmcraft --control 9876`으로 띄운 앱 조종)가 있습니다. 도구는 command_list, command_run, command_batch, doc_inspect, render_preview, project_inspect, sequence_inspect, media_import, render_frame이고, bridge 전용으로 ui_inspect, ui_elements, ui_click, ui_drag, ui_key, ui_type, ui_screenshot, ui_control이 있습니다. 리소스는 filmcraft://document, filmcraft://commands입니다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/agents.md (2026-10-15 (main 브랜치), 신뢰도 high)
- Windows MSI 설치본에는 filmcraft-cli.exe가 함께 들어 있습니다(기본 경로 C:\Program Files\FilmCraft\filmcraft-cli.exe, PATH에는 추가되지 않음). `claude mcp add filmcraft -- "C:\Program Files\FilmCraft\filmcraft-cli.exe" mcp`로 등록할 수 있습니다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/agents.md (2026-10-15 (main), 신뢰도 high)
- MCP 서버에는 폴더를 제한하는 플래그가 없어 사용자가 접근할 수 있는 모든 경로를 읽고 쓸 수 있습니다. 이를 제한하는 옵션을 추가하자는 요청이 open 이슈 #985입니다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/agents.md ; https://github.com/storytold/filmcraft/issues/985 (2026-10-11 (이슈), 2026-10-15 (문서), 신뢰도 high)
- CLI로 GUI 없이 편집하고 렌더링할 수 있습니다. `filmcraft-cli run script.jsonl`(JSONL 명령 배치), `--project p.fcproj --save exec <cmd> key=value`, `--project p.fcproj export out.mp4`(작업이 끝날 때까지 기다림)를 씁니다. 종료 코드는 0이 성공, 1이 명령 실패, 2가 사용법 오류이며, 오프라인 미디어가 있으면 1입니다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/agents.md (2026-10-15 (main), 신뢰도 high)
- .fcproj는 'UTF-8 JSON with an explicit schema version' 형식입니다(format: filmcraft.project, schema_version 13). 미디어는 경로로만 참조하고 파일에 넣지 않습니다. 시간 단위는 254,016,000,000 ticks/초이고, 명령은 seconds, frame, timecode로도 받습니다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/project-files.md (2026-10-15 (main), 신뢰도 high)
- 렌더링 백엔드는 FFmpeg를 쓰지 않습니다(FFmpeg는 외부 테스트 오라클로만 사용). 자체 Rust 코덱과 wgpu GPU 합성(Metal, Vulkan, DX12, WebGPU), 그리고 CPU 경로를 씁니다. Lumetri, 키잉, 내보내기 렌더는 아직 CPU에서 돕니다. — https://github.com/storytold/filmcraft (README Status/Architecture) (2026-10-15, 신뢰도 high)
- README 기준 FilmCraft는 alpha입니다. 2026-10-10에 Premiere Pro 26.5.2와 비교해 다시 측정한 값은 Feature breadth 약 86%, Ready for real work 약 56%입니다. AI 기능은 'Few so far'이고 STT는 선택 사항이며 기본으로 꺼져 있습니다. — https://github.com/storytold/filmcraft (README Status) (2026-10-10 (측정), 2026-10-15 (조회), 신뢰도 high)
- gaps.md G4에 따르면 PR에서 cargo test나 xtask ci를 돌리는 워크플로가 없습니다. Windows 11에서 실행되지 않거나 설치 후 실패하는 이슈(#380, #582, #413, #477)가 근거로 나열돼 있습니다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/gaps.md (2026-10-15 (main), 신뢰도 high)
- MCP 관련 open 버그가 있습니다. 느린 명령 뒤 bridge가 응답을 멈추는 #1538, 1080p60 H.264에서 bridge의 render_frame이 반환하지 않는 #1539, bridge inspect 결과가 부정확한 #1477입니다. MCP 키워드 open 이슈는 총 36건입니다. — https://api.github.com/search/issues?q=repo:storytold/filmcraft+mcp+is:issue+is:open (2026-10-15, 신뢰도 high)
- FilmCraft 그래픽 템플릿은 자체 .fcgt(JSON) 형식만 지원합니다. 문서에 'FilmCraft never reads or imports Adobe .mogrt files (or any other application's template packages)'라고 돼 있어, CapCut 템플릿을 직접 가져올 방법은 없습니다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/graphics.md (2026-10-15 (main), 신뢰도 high)
- FilmCraft 저장소에서 CapCut 언급은 사용자 요청성 이슈뿐입니다. CapCut 같은 앱을 만들어 달라는 #1688, 재생 품질이 CapCut보다 못하다는 #1405, CapCut 레이아웃의 워크스페이스를 추가해 달라는 #1666이 있습니다. CapCut 드래프트를 가져오는 기능이나 로드맵은 찾지 못했습니다. — https://api.github.com/search/issues?q=repo:storytold/filmcraft+capcut (2026-10-15, 신뢰도 high)
- FilmCraft가 지원하는 교환 포맷은 FCP7 XML, FCPXML 1.9–1.11, OpenTimelineIO, CMX 3600 EDL, AAF, OMF 2.0이며, 자막은 SRT, WebVTT, SCC입니다. .prproj는 아직 열 수 없습니다. — https://github.com/storytold/filmcraft (README) (2026-10-15, 신뢰도 high)
- 한국어 UI는 부분 지원입니다(#508). 설치된 시스템 한글 폰트(Malgun Gothic 등)가 있어야 쓸 수 있습니다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/localization-parity.md (2026-10-13 (문서 Last updated), 신뢰도 high)
- filmcraft.tools는 MiniMax H3 reference mode 기반의 생성형 수정 도구입니다. FAQ에서 'not a timeline editor'라고 밝히고, 월 $14.9–$99.9 크레딧 요금제를 운영합니다. 'Independently operated, using the ArtCraft team's open-source FilmCraft engine'이라고 적혀 있고, API나 MCP 언급은 없습니다. — https://filmcraft.tools/ai-video-editor/ (2026-10-15 (조회, 페이지 © 2026), 신뢰도 medium)
- filmcraft.online은 FilmCraft 웹(WASM) 빌드를 무료로 제공하며 호스팅 MCP(mcp.artcraftweb.org/mcp?token=…)를 안내합니다. 그러나 저장소 docs/web.md에서는 이 도메인을 찾지 못해 공식 여부를 확인할 수 없습니다. — https://filmcraft.online/ ; https://raw.githubusercontent.com/storytold/filmcraft/main/docs/web.md (2026-10-15, 신뢰도 low)
- npm, PyPI, GitHub에서 'filmcraft-mcp'라는 이름의 독립 패키지는 찾지 못했습니다. MCP는 FilmCraft 본체(filmcraft-cli)에 들어 있습니다. — WebSearch "filmcraft-mcp" (2026-10-15) ; https://snapcraft.io/filmcraft (2026-10-15, 신뢰도 medium)
- VectCutAPI(sun-guannan, 구 CapCutAPI)는 스타 2,302개, 마지막 push 2026-10-12, Apache-2.0입니다. mcp_server.py(stdio)로 CapCut/JianYing 드래프트를 생성합니다. README에는 암호화된 드래프트에 대한 언급이 없고, 클라우드 렌더 모듈은 공개되지 않았습니다. — https://github.com/sun-guannan/VectCutAPI ; https://api.github.com/repos/sun-guannan/VectCutAPI (2026-10-15, 신뢰도 medium)
- fancyboi999/capcut-mcp는 스타 95개, 마지막 push가 2025-08-21입니다. — https://api.github.com/repos/fancyboi999/capcut-mcp (2026-10-15, 신뢰도 high)

**미해결 질문:**

- CapCut 9.6.0이 암호화되지 않은 draft_content.json으로 새로 만든 드래프트(pyCapCut 출력)를 정상으로 열고, 다시 저장할 때 암호화로 바꾸는지 실측이 필요합니다. 이 결과에 따라 CapCut 경로가 계속 쓸 만한지가 갈립니다.
- 사용자가 받은 CapCut 템플릿 .md에 CapCut 고유 효과·애니메이션 ID가 얼마나 들어 있는지(FilmCraft로 근사할 수 있는 비율) 실제 파일을 보고 확인해야 합니다.
- FilmCraft v0.8.0 Windows 빌드가 이 PC(GPU, 드라이버)에서 크래시 없이 실행되는지 확인이 필요합니다. 특히 headless `filmcraft-cli export`가 GPU 없이 CPU 경로로 안정적으로 도는지도 봐야 합니다.
- FilmCraft의 한글 타이틀 렌더링 품질(시스템 폰트 Malgun Gothic 사용, OpenType 셰이핑)과 CapCut 한글 폰트와의 차이를 확인하지 못했습니다.
- filmcraft.online의 호스팅 MCP(mcp.artcraftweb.org)가 ArtCraft 팀의 공식 서비스인지 저장소 문서에서 확인하지 못했습니다.
- CapCut 데스크톱이 FCPXML이나 OTIO로 타임라인을 내보낼 수 있는지 확인하지 못했습니다. 가능하다면 FilmCraft의 FCPXML/OTIO 가져오기를 통한 반자동 변환 경로가 생깁니다.
- FilmCraft 명령 이름과 파라미터가 v1.0 전에 얼마나 자주 바뀔지(하위 호환 정책) 문서에서 확인하지 못했습니다.

### portable-stack

결론부터 말하면 A(CapCut MCP)와 B(FilmCraft MCP) 중 하나만 고르는 방식은 권하지 않습니다. 대신 3단 구조를 권합니다: 다운로드한 .md 템플릿 → 도구에 묶이지 않는 spec JSON → 코드 기반 렌더러.

[CapCut 경로의 한계] 현재 로컬 상황에서는 다음 이유로 완전 자동화의 핵심 경로로 쓰기 어렵습니다.
- 오늘(2026-10-15) CapCut 9.6으로 저장한 draft_content.json은 암호화되어 있습니다. 그래서 pyCapCut 템플릿 모드로 기존 draft를 읽을 수 없습니다.
- 커뮤니티 자료(2026-09)는 'CapCut International은 암호화하지 않는다'고 하지만, 로컬에서 확인한 사실이 이를 뒤집습니다. 9.x 어딘가에서 국제판에도 암호화가 들어간 것으로 보입니다.
- 9.2 이후 빌드는 Timelines/ 폴더에서 타임라인을 읽고, 8.4 이후 빌드는 오래된 템플릿 기반 draft를 거부할 수 있다는 보고가 있습니다.
- cli-anything-capcut의 render는 중국판(剪映)에서만 동작합니다. render-headless는 ffmpeg 근사 렌더라서 CapCut 고유 이펙트가 재현되지 않습니다.

[FilmCraft의 위치] 사용자가 말한 'Filmcraft'는 storytold/filmcraft입니다. Rust로 만든 Premiere 스타일 NLE이며, 내장 `filmcraft-cli mcp`가 650개 이상의 명령, headless 모드, render_frame, file.exportMedia를 제공합니다. MCP 설계는 조사한 후보 중 가장 깔끔합니다. 다만 2026-09-30 전후에 생성되어 v0.1.0(10/02)에서 v0.8.0(10/14)까지 온 지 2주 된 알파입니다. 스스로 실사용 준비도를 56%로 평가하고, 납품용으로 쓰지 말라고 안내합니다. 또 컷 편집용 NLE라서 CapCut식 텍스트 애니메이션 템플릿 재현과는 성격이 맞지 않습니다.

[템플릿 재현에 가장 맞는 도구] 글로 된 스펙과 레퍼런스 미디어로 템플릿을 재현하는 데는 HTML 또는 React 기반 'video-as-code' 스택이 가장 적합합니다.
- HyperFrames (heygen-com, Apache-2.0)
  - 생성일: 2026-03-10
  - 2026-10-15 기준 v0.8.160, 스타 64k
  - Claude Code 등에서 쓰는 스킬 21개 제공
  - headless Chrome + FFmpeg로 결정론적 렌더
  - Windows 렌더 관련 수정이 릴리스 노트에 있음
- Remotion (v4.0.535)
  - 가장 성숙하고 공식 Agent Skills가 있음
  - MCP는 deprecated
  - 영리조직 직원이 4명 이상이면 유료: Creators 좌석당 $25/월, Automators 렌더당 $0.01·월 최소 $100

[보조 수단]
- FFmpeg MCP인 Kinocut(KyaniteLabs/mcp-video 1.16.1): 컷, 자막, 오버레이 같은 전처리에 사용
- Shotstack과 Creatomate: 클라우드를 써도 된다면 대안. 둘 다 공식 hosted MCP와 템플릿 JSON을 제공

[유지 관리가 약한 도구] MoviePy, Editly, Motion Canvas는 마지막 릴리스가 2025년입니다. OpenCut은 MCP와 headless가 아직 '계획' 단계입니다. DaVinci Resolve는 21.1부터 무료판에서 스크립팅이 빠져 Studio가 필요합니다. 셋 모두 우선순위가 낮습니다.

**권장:**

[권장 전략: '.md 템플릿 → 중립 spec JSON → 렌더러' 3단 구조]
A(CapCut MCP)와 B(FilmCraft MCP)를 둘 다 구축하지 마세요.

1. 단일 진실 원천(spec JSON) 만들기
   - 에이전트가 다운로드한 .md를 읽어 짧은 spec JSON으로 바꿉니다.
   - 필드 예: scenes[]{start, dur, media_slot, text{content, font, in_anim, out_anim}, transition, effect_intent}, music{path, bpm}
   - CapCut 고유 이펙트 이름은 effect_intent 필드에 '의도'로만 남깁니다(예: 'zoom-punch on beat', 'typewriter').

2. 1순위 렌더러: HyperFrames
   - 무료, Apache-2.0이고 Claude Code 스킬을 제공합니다.
   - HTML/GSAP으로 CapCut식 텍스트 애니메이션과 트랜지션을 재현하기 가장 쉽습니다.
   - /music-to-video는 비트 싱크에, /embedded-captions는 자막에 씁니다.
   - 검증 루프: render → ffmpeg로 레퍼런스 영상과 같은 타임코드의 스틸 추출 → 에이전트가 비교 → 수정.
   - 0.x 버전이므로 package.json에서 버전을 고정합니다.

3. 2순위(대체): Remotion
   - 더 높은 안정성과 생태계가 필요할 때 선택합니다.
   - 조직이 직원 4명 이상 영리법인이면 라이선스 비용(좌석당 $25/월 또는 렌더당 $0.01·월 최소 $100)을 미리 확인해야 합니다.
   - HyperFrames의 /remotion-to-hyperframes 스킬이 있어 나중에 갈아타기도 쉽습니다.

4. 3순위: 클라우드 템플릿 API(Creatomate 또는 Shotstack 공식 hosted MCP)
   - 대량 일괄 생산과 사람의 시각적 검수가 중요하고, 미디어 업로드가 허용될 때만 고려합니다.
   - 그 외에는 Kinocut(FFmpeg MCP)을 레퍼런스 컷 추출, 자막 같은 전처리 보조로만 씁니다.

[CapCut 경로(A)] 이미 갖춘 cli-anything-capcut recipe로 유지합니다. 같은 spec JSON에서 draft를 생성해 'CapCut에서 사람이 마지막 손질할 때'만 쓰는 보조 출력으로 둡니다.
- CapCut 9.6은 draft를 암호화하므로 기존 draft를 읽는 템플릿 모드는 쓸 수 없습니다.
- 새 draft를 9.6이 열 수 있는지는 반드시 실측이 필요합니다.
- 최종 export는 GUI에서 수동으로 해야 합니다.
- 별도의 CapCut MCP 서버(VectCutAPI 등)를 추가할 이점은 적습니다. 로컬 CLI가 같은 기능을 더 적은 토큰으로 제공합니다.

[FilmCraft(B)] 지금은 관찰 대상으로 둡니다. MCP 설계는 우수하지만 생성된 지 2주 된 알파이고 납품용 사용을 비권장합니다. CapCut식 템플릿 재현보다 실촬영 컷 편집에 맞습니다. 1~2개월 뒤 v1에 가까워지면, 레퍼런스 촬영본을 컷 편집하는 단계에서 다시 검토하세요.

| 선택지 | 템플릿 적합 | 이식성 | 성숙도 |
|---|---|---|---|
| HyperFrames (heygen-com/hyperframes) + Agent Skills | 5/5 | 5/5 | 매우 활발하지만 0.x 버전이라 변화가 잦습니다. 2026-03-10 생성, v0.8.160(2026-10-15), 스타 약 64k, Apache-2.0. Windows 렌더 관련 수정이 최신 릴리스 노트에 있습니다. |
| Remotion (+ remotion-dev/skills) | 4/5 | 4/5 | 가장 성숙합니다. npm remotion 4.0.535(2026-10-12), 스타 약 64.2k. 공식 Agent Skills가 있고, 공식 MCP는 deprecated입니다(hosted 서버는 2026-08-31 이후 종료 예정). |
| CapCut MCP 계열 (sun-guannan/VectCutAPI 등) + 로컬 pyCapCut/cli-anything-capcut | 4/5 | 1/5 | VectCutAPI는 스타 약 2.3k, Apache-2.0이며 일부 모듈은 비공개입니다. CapCut 버전이 바뀔 때마다 깨지기 쉽습니다. |
| FilmCraft (storytold/filmcraft) 내장 MCP (`filmcraft-cli mcp`) | 2/5 | 4/5 | 매우 초기 알파입니다. 2026-09-30 전후 생성, v0.1.0(2026-10-02)에서 v0.8.0(2026-10-14)까지 왔습니다. 스스로 실사용 준비도를 약 56%로 평가하고, 사본으로만 쓰고 납품용으로 쓰지 말라고 안내합니다. MIT/Apache-2.0, 스타 약 13.5k입니다. |
| FFmpeg MCP: Kinocut (KyaniteLabs/mcp-video) | 2/5 | 4/5 | 1.16.1(2026-10-05 체크포인트), Apache-2.0, 스타 약 205입니다. |
| Creatomate (공식 hosted MCP) | 4/5 | 3/5 | 상용 SaaS입니다. 공식 MCP 문서가 있습니다. |
| Shotstack (공식 hosted MCP) | 4/5 | 3/5 | 상용 SaaS입니다. 문서에 MCP 도구 목록이 있습니다. |
| JSON2Video | 3/5 | 3/5 | 상용 SaaS이며, MCP 유지 주체가 불명확합니다(공식인지 커뮤니티인지 출처가 상충). |
| Editly (mifi/editly) | 3/5 | 3/5 | 정체 상태입니다. npm 0.14.2가 2025-01-19에 마지막으로 나왔고, 유지보수자는 1인입니다(README). MIT, 스타 약 5.5k입니다. |
| MoviePy | 2/5 | 4/5 | 2.2.1(2025-05-21)이 마지막 PyPI 릴리스이고 README에 'Maintainers wanted'라고 적혀 있습니다. MIT, 스타 약 15k입니다. |
| Revideo / Motion Canvas | 3/5 | 3/5 | Motion Canvas는 @motion-canvas/core 3.17.2(2025-02-16)가 마지막 릴리스이고 스타 약 19.3k입니다. Revideo는 @revideo/core 0.11.0(2026-07-10)이고 스타 약 4.1k입니다. 둘 다 활동이 낮습니다. |
| OpenCut (OpenCut-app/OpenCut) | 1/5 | 3/5 | 스타 약 94.6k이지만 재작성 단계입니다. MCP 서버, headless 모드, Editor API는 '계획(upcoming)'입니다. |
| DaVinci Resolve MCP (samuelgursky/davinci-resolve-mcp) | 2/5 | 2/5 | Resolve 자체는 성숙했고 MCP는 커뮤니티 프로젝트입니다(약 1.4k 스타, v2.60.0 2026-07-06; 제3자 집계라 미검증). |

**사실과 근거:**

- FilmCraft는 Rust로 처음부터 만든 오픈소스 NLE입니다. MIT/Apache-2.0이고, Windows(x64/arm64/x86), macOS, Linux, WASM 빌드가 있습니다. 비디오 이펙트 93개, 트랜지션 약 30개를 제공하며, 650개 이상의 엔진 명령을 MCP, TCP JSON 제어 채널, CLI로 노출합니다. 알파 단계이며 실사용 준비도를 약 56%로 자체 평가합니다. — https://github.com/storytold/filmcraft (2026-10-15 조회, 신뢰도 high)
- FilmCraft의 `filmcraft-cli mcp`는 headless 모드(--demo/--project, 창 없음)와 bridge 모드(--bridge 127.0.0.1:9876, `filmcraft --control 9876`로 실행한 앱 제어)를 지원합니다. 도구는 command_list, command_run, command_batch, sequence_inspect, media_import, render_frame, render_preview가 있고, file.exportMedia(wait:true)로 export합니다. — https://github.com/storytold/filmcraft/blob/main/docs/agents.md (2026-10-15 조회, 신뢰도 high)
- FilmCraft 릴리스 이력: v0.1.0(10/02), v0.2.1(10/06), v0.6.0(10/11), v0.7.2(10/12), v0.8.0(10/14, Latest). 리포 생성일은 2026-09-30 전후로 보고됩니다. — https://github.com/storytold/filmcraft/releases ; https://pasqualepillitteri.it/en/news/22531/filmcraft-free-premiere-pro-alternative-guide-rust (2026-10-14 (릴리스), 2026-10 (블로그), 신뢰도 high)
- FilmCraft의 .fcproj는 스키마 버전(v1~13 이력)이 있는 compact UTF-8 JSON입니다. 미디어는 경로로만 참조합니다. 외부 도구가 이 파일을 생성하는 공식 경로는 문서화되어 있지 않습니다. — https://github.com/storytold/filmcraft/blob/main/docs/project-files.md (2026-10-15 조회, 신뢰도 high)
- jhonsu01/filmcraft-mcp-server는 FilmCraft와 무관한 비공식 래퍼입니다(도구 11개, Apache-2.0, 스타 0, FilmCraft 0.2.1 기준으로 테스트). — https://github.com/jhonsu01/filmcraft-mcp-server (2026-10-15 조회, 신뢰도 high)
- HyperFrames: 2026-03-10 생성, 스타 64,002, Apache-2.0, 설명은 'Write HTML. Render video. Built for agents.' 최신 릴리스는 v0.8.160(2026-10-15)이고, 릴리스 노트에 Windows 첫 렌더 관련 수정이 있습니다. — https://api.github.com/repos/heygen-com/hyperframes ; https://api.github.com/repos/heygen-com/hyperframes/releases (2026-10-15, 신뢰도 high)
- HyperFrames는 headless Chrome으로 프레임을 seek하고 FFmpeg로 인코딩합니다(Node 22 이상). GSAP, CSS, Lottie, Three.js 어댑터, catalog 블록, frame.md 디자인 템플릿, Claude Code/Codex/Cursor/Gemini CLI용 스킬을 제공합니다. 전용 MCP 서버는 README에서 확인되지 않았습니다. — https://raw.githubusercontent.com/heygen-com/hyperframes/main/README.md (2026-10-15 조회, 신뢰도 high)
- Remotion 무료 라이선스 대상은 개인, 직원 3명 이하 영리조직, 비영리, 평가 목적입니다. 그 밖에는 Company License가 필요하며, 5.0에서 라이선스가 일부 바뀔 예정입니다. — https://github.com/remotion-dev/remotion/blob/main/LICENSE.md (2026-10-15 조회, 신뢰도 high)
- Remotion Company License 가격: Creators 좌석당 $25/월, Automators 렌더당 $0.01(월 최소 $100), Enterprise 월 $500부터. — https://www.remotion.pro/license (2026-10-15 조회, 신뢰도 high)
- Remotion MCP 서버는 deprecated입니다. hosted 서버는 2026-08-31 이후 종료되며, 대체 수단은 Agent Skills(/remotion-docs 등)입니다. — https://www.remotion.dev/docs/ai/mcp (2026-10-15 조회 (페이지에 날짜 없음), 신뢰도 high)
- Remotion Agent Skills는 `npx skills add remotion-dev/skills`로 설치합니다. /remotion-best-practices, /remotion-render, /remotion-captions 등이 포함되며 Claude Code, Codex, Cursor를 지원합니다. — https://www.remotion.dev/docs/ai/skills (2026-10-15 조회, 신뢰도 high)
- npm 최신 버전: remotion 4.0.535(2026-10-12), @revideo/core 0.11.0(2026-07-10), @motion-canvas/core 3.17.2(2025-02-16), editly 0.14.2(2025-01-19), hyperframes 0.8.160(2026-10-15). PyPI moviepy 2.2.1(2025-05-21). — https://registry.npmjs.org/ ; https://pypi.org/pypi/moviepy/json (2026-10-15 조회, 신뢰도 high)
- VectCutAPI(구 CapCutAPI): 스타 약 2.3k, Apache-2.0. save_draft가 dfd_ 폴더를 만들고, 이를 CapCut/剪映 drafts 폴더로 복사하는 방식입니다. draft_profile은 capcut_legacy/jianying_legacy/jianying_pro_10이며, mcp_server.py(stdio, 도구 11개)를 제공합니다. MCP Editing Agent와 클라우드 렌더 모듈은 비공개입니다. — https://github.com/sun-guannan/VectCutAPI (2026-10-15 조회, 신뢰도 high)
- 커뮤니티 자료는 剪映 6.0 이상만 draft_content.json을 AES 암호화하고 CapCut International은 테스트한 모든 버전에서 암호화하지 않는다고 기술합니다. 그러나 로컬 CapCut 9.6으로 2026-10-15에 저장한 draft는 암호화되어 있어(crypto_key_store.dat 존재) 이 기술과 충돌합니다. — https://github.com/renezander030/capcut-cli/blob/master/docs/jianying-encryption.md ; 로컬: C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft (2026-09 (문서 근거), 2026-10-15 (로컬), 신뢰도 medium)
- CapCut 8.4 이상은 오래된 템플릿 기반 draft를 'unconventional path'로 거부할 수 있습니다. 9.2 이후 빌드는 Timelines/에서 타임라인을 읽어 루트 파일만 쓰면 반영되지 않을 수 있습니다. 앱 버전을 고정하는 공식 방법은 없습니다. — https://voyager.so/blog/capcut-mcp (2026-09-17, 신뢰도 medium)
- cli-anything-capcut의 `render`는 GUI 창 이름 '剪映专业版'에 의존하므로 국제판 CapCut 9.4.0에서 실패합니다. `render-headless`는 CapCut 없이 ffmpeg만으로 렌더합니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/README.md:168-184 (로컬 v0.5.7, 신뢰도 high)
- cli-anything-capcut README는 MCP 도구 스키마가 컨텍스트를 차지하므로 CLI가 토큰 효율이 높다고 주장합니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/README.md:19-27 (로컬 v0.5.7, 신뢰도 high)
- Kinocut(KyaniteLabs/mcp-video) 1.16.1: MCP 도구 203개(FFmpeg 편집 32, 트랜지션 3, 텍스트/레이아웃 6, HyperFrames 18 등), Apache-2.0, Windows/macOS/Linux 지원, Python 3.11 이상과 FFmpeg 필요. — https://github.com/KyaniteLabs/mcp-video (2026-10-05 (릴리스 체크포인트), 신뢰도 high)
- OpenCut은 처음부터 다시 쓰는 중입니다. 지금 쓸 수 있는 것은 classic 버전이며, MCP 서버, headless 모드, Editor API는 upcoming(미제공)입니다. 스타 약 94.6k, MIT. — https://github.com/OpenCut-app/OpenCut (2026-10-15 조회, 신뢰도 high)
- DaVinci Resolve 21.1부터 무료판의 Python 스크립팅이 Studio 전용으로 옮겨졌습니다('moved the ability to script in Python to the Studio version'). — https://www.pugetsystems.com/blog/2026/09/10/how-davinci-resolve-free-v21-1-scripting-changes-affect-puget-bench/ (2026-09-10, 신뢰도 high)
- Shotstack 공식 MCP: https://mcp.shotstack.io/ (Streamable HTTP, OAuth 또는 x-api-key). 도구는 studio, render_video, get_render_status, 템플릿 CRUD, render_template, generate_asset 등입니다. — https://shotstack.io/docs/guide/agents/mcp-server/ (2026-10-15 조회 (페이지에 날짜 없음), 신뢰도 high)
- Shotstack 가격: 무료 10크레딧(30일), PAYG $10에 50분, Starter $39/월에 250분, Pro $99/월에 750분, Scale $199/월에 2,000분, Volume $499/월에 10,000분. — https://shotstack.io/pricing/ (2026-10-15 조회, 신뢰도 high)
- Creatomate는 공식 hosted MCP(https://api.creatomate.com/mcp)를 제공합니다. 도구는 get_guide, 템플릿 CRUD, create_render/get_render이고, 포맷은 RenderScript JSON입니다. 720p 25fps 1분에 약 14크레딧이며, 무료 체험은 50크레딧입니다. — https://creatomate.com/docs/fundamentals/getting-started/mcp-integration ; https://creatomate.com/pricing (2026-10-15 조회, 신뢰도 high)
- JSON2Video 가격: 무료 600크레딧(워터마크 포함), Hobby $16.63/월(연간 결제)에 50분, Professional $49.95/월에 200분. 가격 페이지에 MCP 언급이 없고, MCP는 커뮤니티 패키지로 보입니다. — https://json2video.com/pricing/ ; https://www.flowhunt.io/mcp-servers/json2video-mcp/ (2026-10-15 조회, 신뢰도 medium)
- Editly는 JSON5 스펙과 gl-transitions를 쓰고 텍스트 레이어는 title, subtitle, news-title, slide-in-text입니다. README에 1인 유지보수라고 적혀 있습니다. MIT, 스타 약 5.5k. — https://github.com/mifi/editly (2026-10-15 조회, 신뢰도 high)
- 'Filmcraft'라는 이름으로 공개 웹을 검색하면 storytold/filmcraft(ArtCraft 계열) 외의 AI 영상 제품은 확인되지 않았습니다. 사용자의 Downloads 폴더에 artcraft-launcher-0.3.2-windows-x64.msi가 있습니다. — https://github.com/storytold/filmcraft ; 로컬: C:/Users/bssho/Downloads (2026-10-15, 신뢰도 medium)

**미해결 질문:**

- 로컬 CapCut 9.6이 pyCapCut/cli-anything-capcut이 만든 비암호화 새 draft를 정상적으로 여는지 확인되지 않았습니다(Timelines/ 구조 반영 여부 포함). CapCut 경로를 유지하려면 반드시 실측해야 합니다.
- 다운로드한 .md 템플릿에 CapCut 고유 프리셋 이름(텍스트 애니메이션, 필터, 스티커, 트랜지션)이 얼마나 들어 있는지 모릅니다. 많다면 'CapCut 프리셋 → GSAP/CSS 레시피' 매핑표를 먼저 만들어야 합니다.
- 사용자 조직이 Remotion 무료 대상(개인 또는 직원 3명 이하 영리조직)인지 확인이 필요합니다. 아니면 Remotion에 비용이 발생합니다.
- 레퍼런스 미디어를 클라우드(Shotstack/Creatomate)에 업로드해도 되는지(저작권, 보안 정책) 확인이 필요합니다.
- 사용자가 말한 'Filmcraft & MCP'가 storytold/filmcraft 내장 `filmcraft-cli mcp`인지, 비공식 jhonsu01/filmcraft-mcp-server인지, 또는 다른 제품인지 확인되지 않았습니다(Downloads에 artcraft-launcher-0.3.2 msi가 있음).
- HyperFrames의 Windows 11 렌더(Node 22, FFmpeg, Chromium 다운로드)와 한글 폰트(Pretendard 등) 렌더는 로컬에서 직접 확인하지 않았습니다.
- HyperFrames 전용 MCP 서버는 확인하지 못했습니다(스킬과 CLI 방식). MCP가 꼭 필요하다면 Kinocut의 HyperFrames 도구 18개로 대체할 수 있는지 검토가 필요합니다.
- Creatomate 플랜의 정확한 달러 가격은 가격 페이지에서 추출하지 못했습니다(크레딧 수만 확인).

### reference-analysis

결론: A(CapCut MCP)와 B(FilmCraft MCP) 중 하나를 고르는 것보다, 중간 편집 명세(Edit Spec JSON)를 먼저 두는 구조가 낫습니다. 레퍼런스 영상과 템플릿 .md를 이 명세로 바꾼 뒤 렌더 대상별 컴파일러를 두 개 둡니다. (1) CapCut 쪽은 이미 설치·패치된 pyCapCut과 cli-anything-capcut recipe를 씁니다. (2) 포터블 쪽은 OTIO를 거쳐 FilmCraft, Resolve, Premiere로 보내거나 HyperFrames/Remotion으로 렌더합니다.

조사 결과 요약:
(a) 사용자가 말한 'Filmcraft'는 storytold/filmcraft로 보입니다(추정). Rust로 Premiere를 클린룸 재구현한 프로젝트이며 alpha 단계입니다. 2026-10-10 측정 기준 실무 준비도는 약 56%입니다. headless MCP(command_run/command_batch/render_frame)와 OTIO·EDL·FCP7 XML 읽기/쓰기, .cube LUT, lumetri.applyMatch를 지원해서 에이전트 친화성과 이식성은 높습니다. 다만 CapCut 고유의 효과·전환·텍스트 애니메이션 이름과는 1:1로 대응되지 않고, 타이틀/텍스트 명령은 문서에 나와 있지 않습니다.
(b) 'CapCut MCP'는 대부분 VectCutAPI(sun-guannan, HTTP 서버 + MCP stdio)를 감싼 얇은 래퍼입니다(Atx-Guy, MigueDuque 등). 하는 일은 결국 draft 파일 생성으로, 로컬 pyCapCut과 같습니다. 여기에 서버 계층과 CapCut 9.x 호환성 불확실성이 더해집니다.
(c) 레퍼런스를 분석하는 쪽은 2026년 기준 도구가 충분히 성숙했습니다. 컷 경계는 PySceneDetect 0.7.2(2026-10-11, OTIO/EDL/FCPXML 출력과 save-keyframes 지원)가 프레임 단위로 거의 정확하게 잡습니다. 점진적 전환은 TransNetV2/AutoShot으로 보완합니다. 비트·다운비트·곡 구간은 beat_this와 allin1, 텍스트는 PaddleOCR 한국어 인식과 LLM 교정, 장면 의미·슬롯 설명은 Claude 프레임 비전이나 Gemini 비디오가 맡습니다. 색은 color-matcher로 맞춘 뒤 .cube로 굽습니다.
(d) 사람이 꼭 봐야 하는 부분이 있습니다. 전환·효과 종류를 정확한 CapCut 에셋으로 식별하는 일(VEU-Bench에서 비디오 LLM은 컷 유형·전환 인식이 약했고, 일부는 무작위 추측보다 낮았습니다), 한글 폰트 식별, 유료·라이선스 에셋, 최종 취향 판단입니다. Gemini는 기본 1fps에 MM:SS 타임스탬프라서 컷 타이밍을 정하는 용도로는 쓰면 안 됩니다. 의미 라벨링에만 써야 합니다.

제안하는 중간 명세(장면 단위 필드):
- start/dur: 초 단위 소수점 3자리. fps를 함께 적고 snap 근거(예: downbeat#3)를 남깁니다.
- slot: 미디어 자리. kind, aspect, min_src_dur, subject_hint, fit
- motion: zoom/pan 키프레임
- texts[]: 문구 또는 {{PLACEHOLDER}}, style_ref, in/out 애니메이션 클래스, 표시 시간
- transition_out: 전환 클래스, dur, capcut 이름 매핑, fallback
- effects[]
- color: LUT, 매칭 기준 프레임
- audio_cue: sfx, 덕킹, 비트 정렬
- confidence와 needs_review

전역 영역에는 canvas, audio(bpm, beats, downbeats, sections), styles(텍스트 스타일 토큰)를 둡니다. .md는 의도(문구·구성)의 기준이고, 분석 결과는 타이밍의 기준입니다.

중요한 로컬 이슈가 하나 있습니다. capcut-cli 문서는 'CapCut International은 암호화 안 됨'이라고 하지만, 사용자 PC에서는 9.6.0으로 저장한 draft가 암호화되어 있었습니다. 그래도 같은 문서에 따르면 암호화는 '앱이 만든 draft 읽기'만 막고 '새 draft 쓰기'는 막지 않습니다. 템플릿 정보를 .md와 레퍼런스 영상에서 가져오는 이 전략에서는 치명적이지 않습니다. 단, 9.6.0이 pyCapCut으로 만든 평문 draft를 정상적으로 여는지는 직접 확인해야 합니다.

**권장:**

추천 전략은 'Spec-first, 두 컴파일러'입니다. CapCut MCP나 FilmCraft MCP 하나를 고르는 대신, 아래 순서로 파이프라인을 만드세요.

1) 수집: 템플릿 .md를 파싱해 장면 수·문구·대략적 타이밍·효과 이름으로 명세 골격을 만듭니다. 여기서 .md는 '의도'의 기준입니다.

2) 레퍼런스 분석(자동):
- PySceneDetect 0.7.2의 detect-adaptive로 컷 경계를 잡고 save-otio와 save-keyframes를 출력합니다. 디졸브·페이드 같은 점진적 전환이 많으면 TransNetV2나 AutoShot을 보조로 씁니다.
- 오디오는 beat_this(또는 allin1)로 bpm, beats, downbeats, 곡 구간을 뽑습니다.
- 장면마다 처음·중간·끝 프레임을 추출해 Claude 비전에 JSON 스키마 출력으로 넘깁니다. 슬롯 설명, 텍스트 박스 위치·색·크기, 모션 추정, 전환 '클래스' 후보를 받습니다.
- 텍스트는 PaddleOCR 한국어 인식 결과에 .md 문구를 대조해 LLM이 교정합니다.
- 색은 color-matcher로 맞춘 뒤 colour-science로 .cube를 굽습니다.
- Gemini는 전체 맥락 요약에만 씁니다. 1fps라서 타이밍 근거로는 금지입니다.

3) 병합: 타이밍은 분석 결과를 우선하고 다운비트에 스냅합니다. 문구와 구성은 .md를 우선합니다. 필드마다 confidence와 needs_review를 붙입니다.

4) 사람 게이트: 컨택트 시트와 레퍼런스 대비 표로 전환·효과·폰트 매핑만 확인받습니다. cli-anything-capcut의 preview/review를 활용하면 됩니다.

5) 컴파일:
- 주 경로는 명세를 cli-anything-capcut recipe JSON으로 바꾸고 import-recipe와 save --auto-fix를 거쳐 CapCut draft를 만드는 것입니다. 이미 패치·검증된 로컬 pyCapCut을 쓰고, CapCut 에셋 enum과 직접 매핑됩니다. MCP 래퍼는 필요해질 때 CLI를 얇게 감싸면 충분합니다.
- 보조 포터블 경로는 명세를 OTIO(컷·슬롯·디졸브·마커, 텍스트/효과는 metadata)로 바꿔 FilmCraft·Resolve로 보내거나, HyperFrames 또는 json-render/Remotion으로 직접 렌더하는 것입니다.

6) 검증 루프: 렌더 결과에 PySceneDetect를 다시 돌려 컷 타이밍 오차와 장면 수를 레퍼런스와 자동 비교합니다. FilmCraft를 쓴다면 render_frame으로 대조합니다.

명세 골격(장면 1개 예시):
{"spec_version":"0.1","canvas":{"w":1080,"h":1920,"fps":30},"audio":{"bgm_slot":"bgm","bpm":128,"downbeats_s":[0.0,1.875],"sections":[{"label":"chorus","start":12.4,"end":28.0}]},"styles":{"title_a":{"font_hint":"굵은 고딕","capcut_font":null,"size_pct":7.5,"color":"#FFFFFF","stroke":{"color":"#000000","w":0.08},"anchor":[0.5,0.18]}},"scenes":[{"id":"s01","start":0.000,"dur":1.875,"snap":"downbeat#1","slot":{"id":"clip_1","kind":"video","aspect":"9:16","min_src_dur":2.0,"subject_hint":"제품 클로즈업","fit":"cover"},"motion":{"type":"zoom_in","from":1.0,"to":1.12,"ease":"ease_out"},"texts":[{"text":"{{HOOK}}","style":"title_a","t":[0.1,1.7],"in":{"class":"pop","dur":0.3},"out":{"class":"fade","dur":0.2}}],"transition_out":{"class":"whip_left","dur":0.25,"capcut":null,"fallback":"cut"},"effects":[{"class":"flash","at":0.0,"dur":0.1,"capcut":null}],"color":{"lut":"look_01.cube","ref_frame":"ref_s01.jpg"},"audio_cue":{"sfx":"whoosh","at":1.65,"duck_db":-6},"confidence":{"timing":0.97,"transition":0.55,"text_style":0.7},"needs_review":["transition_out","effects"]}]}

시간은 초 단위로 저장하고 컴파일러가 변환합니다. pyCapCut은 마이크로초, OTIO는 RationalTime, FilmCraft는 tick(초당 254,016,000,000)입니다. capcut 필드가 null이면 사람이 고르거나 fallback을 씁니다.

자동화 경계:
- 신뢰 가능(자동): 하드컷 타이밍, 비트·구간 스냅, 텍스트 내용, 대략적 위치·색·크기, 키프레임 샘플, 슬롯 설명, 근사 색 매칭, 자막 타이밍.
- 반자동(LLM 후보 + 사람 확인): 전환 클래스, 효과 유형, 텍스트 인/아웃 애니메이션, 줌/팬 수치, 속도 램프.
- 사람 필수: 정확한 CapCut 에셋 ID(전환·효과·폰트), 한글 폰트 식별, 유료·라이선스 에셋과 음원, 레퍼런스 푸티지·음악 복제 여부(편집 문법만 복제), 최종 취향 QA와 CapCut 최종 export 클릭.

FilmCraft는 이식성 면에서 가장 유망합니다. 하지만 alpha(실무 준비도 약 56%)이고 텍스트/전환 명령이 문서화되어 있지 않으니, 지금은 OTIO 수신처와 색 매칭 용도로 시험만 하고 주 렌더러로는 쓰지 마세요.

| 선택지 | 템플릿 적합 | 이식성 | 성숙도 |
|---|---|---|---|
| A1. 로컬 pyCapCut + cli-anything-capcut (CLI, MCP 없이) | 5/5 | 2/5 | 사용자 PC에 이미 설치·패치·검증됨. pyCapCut 원본 레포의 마지막 push는 2025-09경(제3자 인덱스 기준). CapCut 9.x 레이아웃 변화(Timelines 중첩, draft_meta_info)는 로컬 패치에 의존합니다. |
| A2. VectCutAPI + CapCut MCP 래퍼 (Atx-Guy/capcut-mcp-server, MigueDuque/capcut-mcp-server-extended 등) | 4/5 | 3/5 | VectCutAPI는 GitHub 2.3k stars, Apache-2.0이며 Releases 목록은 비어 있습니다. 래퍼들은 소규모 커뮤니티 프로젝트입니다. CapCut 9.x 지원 여부는 명시되어 있지 않습니다. |
| B. FilmCraft (storytold/filmcraft) + 내장 MCP | 2/5 | 4/5 | alpha. README 기준 Premiere 26.5.2 대비 기능 폭 약 86%, 실무 준비도 약 56%(2026-10-10 측정). GitHub 페이지 표시는 13.5k stars이며 릴리스 태그는 표시되지 않습니다. MIT/Apache-2.0입니다. |
| C. 레퍼런스 → 명세 분석 스택 (PySceneDetect / TransNetV2·AutoShot / beat_this·allin1·librosa / PaddleOCR / Claude·Gemini 비전 / color-matcher) | 5/5 | 5/5 | PySceneDetect 0.7.2(2026-10-11) 활발. librosa 0.11.0(2025-03). beat_this 1.1.0(ISMIR 2024). PaddleOCR 3.1(2025-06, 한국어 PP-OCRv5). TransNetV2는 2025~26 공식 pip 릴리스를 찾지 못했고 PyTorch 포트만 있습니다. |
| D. 포터블 렌더러: HyperFrames(heygen-com) / Remotion json-render / Kinocut(KyaniteLabs, 구 mcp-video) | 3/5 | 5/5 | HyperFrames는 Apache-2.0, Node 22+, 에이전트 skill을 제공합니다. Kinocut은 v1.16.1(2026-10-05)로 MCP 도구 203개, 장면 검출과 Hyperframes 도구를 포함하고 1.15.0부터 Windows를 지원합니다. json-render remotion skill은 2026-07 업데이트입니다(제3자 표기). |

**사실과 근거:**

- FilmCraft는 Rust로 Adobe Premiere Pro를 클린룸 재구현한 오픈소스 NLE이며 alpha 상태다. 2026-10-10 Premiere 26.5.2 기준으로 재측정한 기능 폭은 약 86%, 실무 준비도는 약 56%다. MIT/Apache-2.0 이중 라이선스. — https://raw.githubusercontent.com/storytold/filmcraft/main/README.md (2026-10-10 (parity 측정일), 신뢰도 high)
- FilmCraft MCP는 `filmcraft-cli mcp`(headless 또는 --bridge)로 실행된다. 도구는 command_list, command_run, command_batch, doc_inspect, render_preview, project_inspect, sequence_inspect, media_import, render_frame이고 bridge 모드에서는 ui_* 도구가 추가된다. 시간 단위는 tick(초당 254,016,000,000)이며 seconds/frame/timecode도 받는다. headless 모드에는 폴더 제한이 없다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/agents.md (2026-10 (조회일 2026-10-15), 신뢰도 high)
- FilmCraft 파일 포맷 지원: OTIO read+write(80%), FCP7 XML read+write, EDL read+write, FCPXML read(XtoCC 경유), SRT/WebVTT/SCC read+write, .cube/.3dl LUT read. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/file-format-parity.md (2026-10 (조회일 2026-10-15), 신뢰도 high)
- FilmCraft 컨트롤 프로토콜 문서에는 lut.import, lumetri.setInputLut, lumetri.applyMatch, effects.setDefaultTransition이 있다. 타이틀/텍스트(graphics.*, titles.*)와 OTIO import 명령 id는 문서화되어 있지 않다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/control-protocol.md (2026-10 (조회일 2026-10-15), 신뢰도 medium)
- FilmCraft .fcproj는 UTF-8 JSON(현재 schema_version 13)이다. project 객체의 필드 구조는 문서화되지 않았고, 빌드보다 새로운 schema는 거부한다. — https://raw.githubusercontent.com/storytold/filmcraft/main/docs/project-files.md (2026-10 (조회일 2026-10-15), 신뢰도 high)
- FilmCraft GitHub 페이지 표시 기준 13.5k stars, 5.5k forks이며 Releases 항목은 비어 있다. — https://github.com/storytold/filmcraft (2026-10-15 조회, 신뢰도 medium)
- VectCutAPI(sun-guannan): GitHub 2.3k stars, Apache-2.0. HTTP API와 MCP(stdio)를 제공하고 draft_profile은 capcut_legacy/jianying_legacy/jianying_pro_10이다. 클라우드 렌더링 모듈은 오픈소스가 아니며 CapCut 버전별 지원(암호화 등)은 명시되어 있지 않다. — https://github.com/sun-guannan/VectCutAPI (2026-10-15 조회, 신뢰도 medium)
- Atx-Guy/capcut-mcp-server(11개 도구, stdio/HTTP)와 MigueDuque/capcut-mcp-server-extended는 VectCutAPI 백엔드를 먼저 실행해야 하는 래퍼다. — https://github.com/Atx-Guy/capcut-mcp-server ; https://github.com/MigueDuque/capcut-mcp-server-extended (2026-10-15 조회(검색 요약), 신뢰도 medium)
- PySceneDetect 0.7.2(2026-10-11)는 save-keyframes 명령을 추가했고, EDL/FCPXML/FCP7/OTIO 출력 함수가 경로·핸들을 받는다. 0.7(2026-05-03)은 VFR 타임스탬프를 개편했고(Python 3.10+) write_scene_list_otio 등을 추가했다. 0.6.6(2025-03-09)에서 save-otio와 save-edl이 도입됐다. — https://www.scenedetect.com/changelog (2026-10-11, 신뢰도 high)
- TransNetV2는 2025~2026년 공식 pip 릴리스를 확인하지 못했다(원본은 TensorFlow, PyTorch 포트는 존재). AutoShot(CVPRW 2023)은 SHOT 숏폼 데이터셋에서 TransNetV2보다 F1이 4.2% 높다고 보고했다. — https://github.com/soCzech/TransNetV2 ; https://arxiv.org/abs/2304.06116 (2023-04 (AutoShot), 2026-10-15 조회, 신뢰도 medium)
- OmniShotCut(arXiv 2604.24762, 2026-04 v1, 2026-05 v2)은 전환 계열을 합성 데이터로 학습하는 관계형 shot boundary detection을 제안했다. abs 페이지에는 코드 링크가 없다. — https://arxiv.org/abs/2604.24762 (2026-05-21, 신뢰도 medium)
- beat_this(CPJKU, ISMIR 2024)는 DBN 후처리 없는 beat/downbeat 트래커로 `pip install beat-this`(MIT, 1.1.0)로 설치한다. madmom의 마지막 push는 2024-08경(미러 기준)이다. — https://github.com/CPJKU/beat_this (2026-04-14 (최근 push, 제3자 표기), 신뢰도 medium)
- allin1(mir-aidj/all-in-one)은 tempo, beats, downbeats, 기능 구간(intro/verse/chorus/bridge/outro)을 JSON으로 출력한다. madmom git 설치와 NATTEN(Linux/Windows)이 필요하다. — https://github.com/mir-aidj/all-in-one (2026-10-15 조회, 신뢰도 medium)
- librosa 0.11.0은 2025-03-11 릴리스이며 beat_track 시그니처는 0.10.2와 같다. — https://librosa.org/doc/main/changelog.html (2025-03-11, 신뢰도 high)
- Gemini API 비디오 이해: 기본 1 FPS 샘플링, MM:SS 타임스탬프(초 미만 정밀도 없음). static 모드에서 fps와 start/end offset을 조정할 수 있고 약 100(low)~300 tokens/s, 오디오는 32 tokens/s로 처리된다. — https://ai.google.dev/gemini-api/docs/video-understanding (2026-10-13, 신뢰도 high)
- Claude 비전: API 요청당 이미지 최대 600장(200k 컨텍스트 모델은 100장)이고 20장을 넘으면 각 변 2000px 이하 권장/제한이 적용된다. 비용은 ⌈w/28⌉×⌈h/28⌉ visual tokens이며 Claude 4.7+는 긴 변 2576px 고해상도 tier다. 애니메이션은 첫 프레임만 쓰므로 영상은 프레임 추출이 필요하다. — https://platform.claude.com/docs/en/build-with-claude/vision (2026-10-15 조회, 신뢰도 high)
- VEU-Bench(CVPR 2025): 19개 세부 과제에서 11개 비디오 LLM이 컷 유형·전환 등 편집 요소 인식에 큰 어려움을 보였고 일부는 무작위보다 낮았다. 미세조정 모델 Oscars는 오픈소스 대비 정확도를 28.3% 이상 끌어올렸다. — https://arxiv.org/abs/2504.17828 (2025-04-24, 신뢰도 high)
- Edit3K(arXiv 2403.16048)는 효과·애니메이션·전환·필터·스티커·텍스트 같은 편집 컴포넌트 3,094종을 618,800개 영상으로 구성한 데이터셋과 표현 학습을 제안했다. 컴포넌트 인식·검색·추천이 목표다. — https://arxiv.org/abs/2403.16048 (2025-02-25 (v2), 신뢰도 high)
- PaddleOCR 3.1.0(2025-06-29)에서 한국어를 포함한 37개 언어 PP-OCRv5 인식 모델이 추가됐다. korean_PP-OCRv5_mobile_rec의 라인 정확도는 88.0%다. — https://huggingface.co/PaddlePaddle/korean_PP-OCRv5_mobile_rec (2025-06-29, 신뢰도 medium)
- color-matcher(hahnec) 0.6.0(2025-03-30)은 MKL/HM/Reinhard/MVGD 색 전이를 제공한다. .cube 내보내기 기능은 확인하지 못했고 colour-science의 write_LUT_IridasCube로 구워야 한다. — https://www.piwheels.org/project/color-matcher/ (2025-03-30, 신뢰도 medium)
- OpenTimelineIO 최신 확인 버전은 0.18.1(2025-11-09)이다. v0.16부터 어댑터는 OpenTimelineIO-Plugins 패키지로 분리됐다. — https://www.piwheels.org/project/opentimelineio (2025-11-09, 신뢰도 medium)
- capcut-cli(renezander030) 문서: 암호화는 '앱이 작성한 draft 읽기'를 막지만 새 draft 쓰기는 막지 않는다. 문서는 'CapCut International은 암호화되지 않음'이라고 적었지만 사용자 로컬의 CapCut 9.6.0 저장 draft는 암호화되어 있어 서로 모순된다. CapCut 9.2.8+는 Timelines/<id>/draft_info.json을 읽고, 최신 빌드는 draft_meta_info.json의 draft_materials로 미디어 import를 결정한다. — https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md ; https://raw.githubusercontent.com/renezander030/capcut-cli/master/CHANGELOG.md (2026-10-09 (CHANGELOG 0.29.0), 신뢰도 medium)
- pyJianYingDraft 문서 기준으로 CapCut 7 이상에서는 자동 export가 지원되지 않는다(2차 출처 인용). — https://docsearch.algolia.com/mcp/docs/repo/guanyixuan/pyjianyingdraft (2026-10-15 조회, 신뢰도 low)
- 로컬 pyCapCut의 metadata에는 TransitionType, FilterType, FontType, VideoSceneEffectType, VideoCharacterEffectType, IntroType, OutroType, GroupAnimationType, TextLoopAnim, MaskType 등 CapCut 에셋 enum이 있다(transition_meta.py 약 1,100줄, filter 약 450, font 약 350개 항목 라인). VideoSegment에는 add_transition/add_filter/add_mask/add_animation/add_keyframe가 있다. — C:/Users/bssho/Downloads/paperclip-master/pyCapCut/pycapcut/metadata/transition_meta.py:5 ; C:/Users/bssho/Downloads/paperclip-master/pyCapCut/pycapcut/video_segment.py:476 (2026-10-15 (로컬), 신뢰도 high)
- cli-anything-capcut recipe는 name/width/height/fps와 operations 배열(add_video, add_video_animation, add_filter, add_text, add_text_animation 등, segment_ref로 연결)로 구성된다. v0.4 CLI는 LUT와 크로마키를 지원하지 않는다. CLI 코드에는 장면 검출·비트 분석 기능이 없다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/claude-skill/references/recipe-guide.md:1 ; .../claude-skill/references/recipes/social-short.json:1 (2026-10-15 (로컬), 신뢰도 high)
- HyperFrames(heygen-com/hyperframes)는 HTML/CSS/애니메이션을 headless Chrome과 FFmpeg로 결정적 MP4로 렌더한다. Apache-2.0이고 Node 22+가 필요하며 `npx skills add heygen-com/hyperframes`로 에이전트 skill을 제공한다. — https://github.com/heygen-com/hyperframes (2026-10-15 조회(검색 요약), 신뢰도 medium)
- Kinocut(KyaniteLabs, 구 mcp-video): v1.16.1(2026-10-05), MCP 도구 203개, 장면 검출, Hyperframes 도구 18개, sources/steps/outputs JSON 워크플로, Windows 지원(1.15.0+). 비디오 LUT 지원은 불명확하다. — https://github.com/KyaniteLabs/mcp-video (2026-10-05, 신뢰도 medium)
- FableCut(ronak-create)은 브라우저 에디터이며 project.json을 에이전트가 패치하면 UI가 핫리로드된다. Claude Code가 타임라인 전체를 JSON 하나로 작성한 데모가 있고 OTIO는 어댑터로만 지원한다. — https://hn.svelte.dev/item/48845422 ; https://github.com/ronak-create/FableCut (2026-07경(상대 날짜 '3개월 전'), 신뢰도 medium)
- coreyhaines31/marketingskills v2.8.11은 바이럴 영상을 컷 리듬, 온스크린 텍스트, 자막 스타일, 페이싱 등 9개 차원의 beat-sheet로 역설계하는 레퍼런스를 추가했다. 원본 푸티지·음악이 아니라 '편집 문법'만 복제하라는 원칙과 실행 전 리뷰 게이트를 포함한다. — https://newreleases.io/project/github/coreyhaines31/marketingskills/release/v2.8.11 (2026-10-15 조회, 신뢰도 medium)
- vercel-labs/json-render의 remotion skill은 fps/width/height/durationInFrames와 tracks/clips를 가진 JSON 타임라인 spec을 Remotion 컴포지션으로 렌더한다. — https://skillselion.com/skills/vercel-labs/json-render/remotion (2026-07-08 (제3자 표기), 신뢰도 medium)

**미해결 질문:**

- CapCut 9.6.0이 pyCapCut/cli-anything-capcut으로 만든 평문 draft를 정상적으로 열고 저장 시 암호화로 변환하는지 실측해야 합니다. capcut-cli 문서는 'International은 암호화 안 됨'이라고 하지만 로컬 관찰과 모순됩니다.
- 다운로드한 템플릿 .md에 CapCut 에셋 이름이나 resource_id(전환·효과·폰트·텍스트 애니메이션)가 들어 있습니까? 들어 있으면 가장 어려운 '에셋 식별'이 단순 매핑으로 바뀝니다.
- 사용자가 말한 'Filmcraft&MCP'가 storytold/filmcraft가 맞습니까? 맞다면 `filmcraft-cli commands`로 타이틀/텍스트·전환 적용 명령 id가 실제로 있는지 확인해야 합니다.
- FilmCraft의 OTIO import가 전환(디졸브)과 metadata를 얼마나 보존하는지는 문서에 없어 라운드트립 테스트가 필요합니다.
- CapCut 최종 export를 자동화할 수 없다면(7+ 미지원 보고) 렌더는 사람이 클릭할지, HyperFrames 같은 대체 렌더러를 쓸지 결정해야 합니다.
- TransNetV2의 유지보수 중인 PyTorch pip 패키지가 있는지, 또는 AutoShot이나 OmniShotCut 코드가 실사용 가능한지 확인되지 않았습니다.
- VectCutAPI 기반 CapCut MCP가 CapCut 9.x(Timelines 중첩, draft_meta_info의 draft_materials 등록)와 호환되는지 검증되지 않았습니다.
- 레퍼런스 영상·음원의 저작권 범위를 정해야 합니다. 편집 문법만 복제하고 원본 푸티지·BGM은 교체한다는 정책을 명세에 강제할지 결정이 필요합니다.

### capcut-encryption

결론: 이 PC의 CapCut은 모든 초안을 암호화하지 않습니다. 초안마다 따로 암호화합니다. 그래서 '.md 설명 + 레퍼런스 미디어 → 새 평문 초안 생성' 경로는 지금(9.6.0)도 막혀 있지 않습니다. 다만 '기존 CapCut 초안을 템플릿으로 읽거나 다시 읽어오는(round-trip) 작업'은 클라우드(팀 스페이스)에서 내려받은 초안부터 깨지기 시작했습니다.

[로컬 실측, 읽기 전용]
- 설치 버전: Apps 폴더에 6.3.0~9.6.0 버전 폴더 22개가 있습니다. 9.6.0.4097은 2026-10-15 14:16~14:27에 자동 업데이트됐고(ProductInfo.xml full_appver=9.6.0.4097), 9.1.0.3879는 2026-07-27에 설치됐습니다.
- 클라우드에서 받지 않은 로컬 초안 40여 개는 모두 평문 JSON입니다. 8.5.0·8.6.0·8.9.1·9.0.0·9.1.0이 저장했고 app_source는 cc(국제판)입니다.
- 암호화된 초안은 모두 클라우드 다운로드 초안입니다(root_meta_info.json에 draft_cloud_last_action_download=true, tm_draft_cloud_space_id=7327545136085664770).
  (1) '57.08 벤츠 지바겐 광각': 2026-05-26 다운로드, 17:01 저장 시 암호화. 당시 최신 설치본은 8.5.0입니다.
  (2) '롱폼 영상 프로젝트': 오늘 14:19 다운로드, 14:33 저장 시 암호화. 9.6.0 설치 직후이고, Timelines 9개도 모두 암호화됐습니다.
  (3) '옵틱글래스 광각미러 템플릿 1': 오늘 17:46~17:49에 9.6.0으로 다운로드. Timelines 16개와 draft_meta_info.json은 암호화됐지만, 루트 draft_content.json은 그 시점에는 평문이었습니다.
- 반대로 클라우드 다운로드인데 평문인 초안도 있습니다. '숏폼 영상 프로젝트 (1)'(8.5.0, 같은 날 5/26)과 '숏폼 영상 프로젝트 (2)'(오늘 17:50, 9.6.0)입니다.
- 따라서 '특정 버전부터 전부 암호화'가 아닙니다. 초안별 플래그로 보입니다. 표지는 draft_virtual_store.json의 type:2 목록에 있는 {"is_encrypted":true,"path":"draft_content.json"}입니다(롱폼, 옵틱글래스에서 확인). 같은 플래그는 8.3.0(2026-04) 초안에서 음원 wav 하나에도 붙어 있었습니다.
- crypto_key_store.dat는 판별 지표가 아닙니다. 평문 초안(0729, 42.포르쉐 등)에도 있고, 암호화된 롱폼에는 없습니다.
- 9.6.0이 '로컬에서 새로 만든' 초안까지 암호화하는지는 아직 확인되지 않았습니다. 9.6.0으로 저장된 로컬 초안이 아직 없습니다. 오늘 14:20에 저장된 '42. 09 포르쉐'는 last_modified 9.1.0이고 평문입니다.
- 참고: 지금 CapCut이 실행 중이고 클라우드 초안을 내려받고 있습니다(.locked, 17:46~17:50 파일 생성). 아무것도 수정하지 않았습니다.

[공개 자료]
- JianYing(중국판): 6.0+부터 draft_content.json을 AES로 암호화한다는 데 커뮤니티 의견이 일치합니다. 5.9가 마지막 평문 라인으로 알려져 있습니다.
- CapCut 국제판: 'CapCut International은 암호화하지 않는다'는 서술이 아직 다수입니다(capcut-cli 문서, Voyager 2026-09-17, pyJianYingDraft #105). 이 PC 실측은 이와 다릅니다. 국제판(cc)에서도 클라우드·템플릿 계열 초안은 암호화됩니다. 2026-05 duckyman-ai skill 문서도 'CapCut 템플릿 라이브러리에서 받은 프로젝트는 암호화'라고 적고 있습니다.
- 평문 초안 열기: CapCut 9.3.0.3970(Windows, cli-anything-capcut 실측 2026-09-01)과 9.3.0(macOS, capcut-shell-inject)에서 도구가 만든 평문 초안이 열렸습니다. 다만 다음 제약이 보고됐습니다.
  · 오래된 템플릿 마커로 시드하면 8.4+/9.3에서 'unconventional/unusual path' 거부
  · 9.1.0 macOS에서 draft_meta_info.json의 draft_materials가 비어 있으면 미디어 relink 요구(pyCapCut #13)
  · 9.2.8-beta4 macOS에서 기존 프로젝트의 루트만 수정하면 무시됨(Timelines/<id> 우선)
- 우회책: 구버전 고정은 공식적으로 위험합니다(구버전 비활성화, 로그인·클라우드 불가 가능, 구버전 설치본 미제공). 복호화는 CapCut 약관 6조('decipher, reverse engineer…', 'circumvent…')와 한국 저작권법 104조의2(기술적 보호조치 무력화 금지)에 저촉될 위험이 큽니다. pyJianYingDraft 메인테이너도 법적 리스크를 이유로 복호화 PR #189를 거절했습니다.
- 스토어 템플릿: 수익화를 켜지 않은 템플릿은 공식적으로 '초안 편집 불가'이고, 원작자 미디어는 보호됩니다. 프로그램으로 쓸 방법은 사실상 없습니다.
- 'Filmcraft'라는 이름의 MCP나 프로젝트는 웹 검색 2회로도 찾지 못했습니다.

**권장:**

권장: A안(생성 전용 경로)을 기본으로 하고, C안(로컬 골든 템플릿)을 보조로 씁니다. 렌더 전용인 F안은 필요할 때 추가합니다. MCP 추가와 복호화는 하지 마세요.

1) 사용자 입력은 이미 '.md 설명 + 레퍼런스 미디어'입니다. 그래서 CapCut이 암호화한 템플릿이나 초안을 읽을 필요가 애초에 없습니다. 흐름은 'LLM이 .md를 읽고 recipe JSON 작성 → cli-anything-capcut(pyCapCut)이 새 평문 초안 생성 → CapCut에서 열어 확인·마감·내보내기'로 갑니다. 9.6.0도 평문 초안을 직접 생성하고 읽으므로(숏폼 (2) 실측) 암호화는 이 경로를 막지 않습니다.
2) MCP냐 CLI냐: 암호화 관점에서 CapCut MCP(VectCutAPI 등)는 같은 초안 포맷에 의존하므로 리스크가 같습니다. 이미 Claude skill이 있는 CLI(cli-anything-capcut)가 있으니 MCP를 추가할 필요가 없습니다. MCP 전용 클라이언트가 꼭 필요할 때만 CLI를 감싼 얇은 래퍼를 고려하세요.
3) 템플릿 모드(C)를 쓸 때는 '로컬에서 직접 만든 초안'만 원본으로 씁니다. 클라우드(팀 스페이스)에서 받은 초안은 암호화될 수 있으니 쓰지 마세요. 골든 템플릿은 CapCut을 종료한 상태에서 첫 바이트가 '{'인지 확인하고, 평문 사본을 별도 폴더에 백업한 뒤 duplicate_as_template로 사용합니다.
4) 업데이트 가드레일: 버전을 고정하는 대신 CapCut 업데이트 직후 스모크 테스트를 돌립니다. 순서는 (a) cli-anything-capcut으로 최소 초안 생성 → (b) CapCut에서 열림과 'unconventional path' 경고 여부 확인 → (c) 저장·종료 후 draft_content.json, Timelines/*/draft_content.json, draft_virtual_store.json의 type:2 is_encrypted를 점검입니다. 특히 9.6.0이 '로컬 신규 초안'도 암호화하는지는 지금 바로 1회 확인하세요. 아직 증거가 없습니다.
5) 기존 초안 수정(패치)은 피하고 항상 새 초안을 생성하세요. 루트만 쓰는 방식은 Timelines/<id>가 있는 기존 프로젝트에서 무시될 수 있습니다. draft_meta_info.json의 draft_materials도 채워야 relink 문제를 줄일 수 있습니다(pyCapCut #13).
6) 복호화(jy-draftc, 온라인 복호화 사이트, PR #189 방식)와 구버전 고정 및 방화벽 차단은 비권장입니다. 각각 약관 6조와 저작권법 104조의2 리스크, 그리고 로그인·클라우드 차단 및 보안 리스크가 있습니다. 스토어 템플릿은 원본 소재를 복제하지 말고 .md에 기술된 구조(장면, 타이밍, 텍스트, 효과 '유형')만 재구성하세요.

| 선택지 | 템플릿 적합 | 이식성 | 성숙도 |
|---|---|---|---|
| A. 생성 전용 경로: .md → recipe JSON → cli-anything-capcut(pyCapCut) → 새 평문 초안 → CapCut에서 열고 내보내기 | 4/5 | 3/5 | 개인 프로젝트이며 v0.5.7입니다. 저장소 문서(docs/capcut-gui-verification.md, 2026-09-01)에 CapCut 9.3.0.3970 GUI 실측 기록이 있습니다(세그먼트·텍스트 정상, 폰트는 content.styles[].font 주입 후 해결). 9.6.0에서는 아직 검증되지 않았습니다. |
| B. CapCut MCP 서버(VectCutAPI 등) | 4/5 | 3/5 | VectCutAPI는 커뮤니티에서 가장 큽니다(Voyager 2026-09-17 기준 약 2.2k stars). 그 외 capcut-mcp 계열은 소규모이고, 일부는 archived 상태입니다(fancyboi999/capcut-mcp). |
| C. pyCapCut 템플릿 모드 + 로컬 '골든 템플릿' 초안 | 5/5 | 2/5 | pyCapCut 템플릿 모드는 '최근 이전되어 호환성 문제 가능'으로 표시돼 있습니다. 로컬 평문 초안 40여 개(8.5.0~9.1.0)로는 바로 쓸 수 있습니다. |
| D. 구버전 CapCut 고정(예: Apps/9.1.0.3879 유지, 자동 업데이트 차단) | 3/5 | 1/5 | 비공식입니다. 공식 업데이트 차단 설정은 찾지 못했습니다. 구버전 설치본은 공식 미제공입니다(CapCut 도움말, 2026-01-06). |
| E. 암호화 초안 복호화(jy-draftc, 커뮤니티 AES-GCM 구현, 온라인 복호화 사이트) | 5/5 | 1/5 | 비공식이며 버전마다 깨집니다. jy-draftc 0.1.1(winget, JianYing 전용 주장, 2026-08-10 갱신)이 있고, pyJianYingDraft PR #189는 2026-06-25에 거절됐습니다. |
| F. CapCut 비의존 렌더러(FFmpeg/MoviePy/Remotion 계열, 예: KyaniteLabs/mcp-video) | 2/5 | 5/5 | 여러 오픈소스 MCP와 라이브러리가 있습니다(mcp-video는 Apache-2.0이고 목록상 29 stars). 이번 각도에서는 깊이 검증하지 않았습니다. |

**사실과 근거:**

- 이 PC의 CapCut 설치 폴더에는 6.3.0.2438부터 9.6.0.4097까지 버전 폴더 22개가 있습니다. 9.6.0 파일은 2026-10-15 14:16~14:27에 기록됐고, ProductInfo.xml의 full_appver는 9.6.0.4097입니다. — C:/Users/bssho/AppData/Local/CapCut/Apps (ls), C:/Users/bssho/AppData/Local/CapCut/Apps/ProductInfo.xml (2026-10-15, 신뢰도 high)
- 클라우드에서 받지 않은 로컬 초안은 모두 평문 JSON입니다. platform/last_modified_platform 기준 8.5.0, 8.6.0, 8.9.1, 9.0.0, 9.1.0이 저장했고 app_source는 'cc'(국제판)입니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/*/draft_content.json (읽기 전용 스캔) (2026-10-15, 신뢰도 high)
- 암호화된 초안 3개는 모두 클라우드 다운로드 초안입니다(draft_cloud_last_action_download=true, tm_draft_cloud_space_id=7327545136085664770). 대상은 '57.08 벤츠 지바겐 광각'(2026-05-26 17:01 저장, 당시 최신 설치본 8.5.0), '롱폼 영상 프로젝트'(2026-10-15 14:33, Timelines 9개 모두 암호화), '옵틱글래스 광각미러 템플릿 1'(2026-10-15 17:46~17:49 다운로드, Timelines 16개와 draft_meta_info.json 암호화)입니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/root_meta_info.json 및 각 폴더 (2026-10-15, 신뢰도 high)
- 클라우드 다운로드 초안이라도 모두 암호화되지는 않습니다. '숏폼 영상 프로젝트 (1)'(8.5.0, 2026-05-26)과 '숏폼 영상 프로젝트 (2)'(9.6.0, 2026-10-15 17:50)는 평문입니다. 따라서 암호화는 버전 전역 스위치가 아니라 초안별 플래그로 보입니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/숏폼 영상 프로젝트 (1), (2) (2026-10-15, 신뢰도 medium)
- 초안별 암호화 표지는 draft_virtual_store.json의 type:2 목록에 있는 {"is_encrypted":true,"is_hidden":true,"path":"draft_content.json"}입니다. 이 항목은 롱폼과 옵틱글래스에 있습니다. 같은 구조는 8.3.0으로 저장된 '전사스 템플릿3'(2026-04)에서 음원 wav 하나에도 붙어 있습니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/롱폼 영상 프로젝트/draft_virtual_store.json (2026-10-15, 신뢰도 medium)
- crypto_key_store.dat는 초안 암호화 지표가 아닙니다. 평문 초안(0729, 42. 09 포르쉐 등 다수)에도 있고, 암호화된 '롱폼 영상 프로젝트'에는 없습니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft (폴더별 파일 목록) (2026-10-15, 신뢰도 high)
- 암호화된 초안 폴더에도 CapCut이 쓴 평문 스냅샷이 남아 있습니다. 롱폼의 template.json.bak(14:18, 8.3.0 생성, 9.5.0 최종 수정)과 벤츠의 template.json.bak(8.3.0 생성, 8.5.0 최종 수정)입니다. 다만 다운로드 시점의 사본이라 이후 편집 내용은 반영되지 않습니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/롱폼 영상 프로젝트/template.json.bak (2026-10-15, 신뢰도 high)
- CapCut '조합 프리셋'(Presets/Combination/.../preset_draft/draft_content.json, 6.8.1로 생성)은 평문입니다. JianYing 9.1.0에서도 프리셋 폴더의 draft_content.json이 암호화되지 않는다는 보고가 있습니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Presets/Combination/Presets/나의 사전 설정1/preset_draft; https://github.com/GuanYixuan/pyJianYingDraft/issues/142 (2026-10-15 / 2025-09-19, 신뢰도 medium)
- Windows 로컬 초안에서는 루트 draft_content.json과 Timelines/<main_timeline_id>/draft_content.json이 해시까지 같은 미러입니다. pyCapCut과 cli-anything-capcut 코드에는 Timelines나 draft_info를 쓰는 부분이 없습니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/0729 (md5 비교); C:/Users/bssho/Downloads (grep) (2026-10-15, 신뢰도 high)
- pyCapCut 템플릿 모드는 '(암호화되지 않은) draft_content.json'만 로드합니다. 로컬 코드도 json.load(script_file.py:215)를 쓰므로 암호화 파일에서는 즉시 예외가 납니다. — https://github.com/GuanYixuan/pyCapCut ; C:/Users/bssho/Downloads/paperclip-master/pyCapCut/pycapcut/script_file.py:215 (2026-10-15, 신뢰도 high)
- JianYing(중국판)은 6.0+부터 draft_content.json을 AES로 암호화하고, 5.9.x가 '마지막으로 널리 쓰인 평문 라인'입니다. 공개 자료에서 찾은 가장 이른 암호화 언급은 2024-04-15의 emosheeep/capcut-export README 메모입니다. — https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md ; https://github.com/emosheeep/capcut-export (2026-09 / 2024-04-15, 신뢰도 medium)
- 커뮤니티 문서 다수는 'CapCut International은 암호화되지 않는다'고 적고 있습니다. 이 PC의 실측(국제판 cc 초안 중 클라우드 다운로드분 암호화)과 어긋납니다. — https://voyager.so/blog/capcut-mcp ; https://github.com/GuanYixuan/pyJianYingDraft/issues/105 (2026-09-17 / 2025-07-16, 신뢰도 medium)
- CapCut macOS용 agent skill 문서는 'CapCut 템플릿 라이브러리 프로젝트는 draft_info.json이 암호화(ByteDance 독자 암호화)되어 수정할 수 없고, 로컬에서 만든 프로젝트만 읽고 쓸 수 있다'고 적고 있습니다. — https://www.skills.sh/duckyman-ai/agent-skills/capcut-editor (2026-05-18 (First Seen), 신뢰도 medium)
- CLI로 생성한 평문 초안이 CapCut 9.3.0.3970(Windows)에서 정상적으로 열렸습니다(세그먼트·텍스트 정상). 폰트는 content.styles[0].font={id,path}를 주입해야 적용되고, id 키가 없으면 CapCut이 크래시합니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/docs/capcut-gui-verification.md (2026-09-01, 신뢰도 medium)
- CapCut 8.4+/9.3은 오래된 템플릿 마커로 시드한 초안을 'This draft comes from an unconventional path and cannot be used'로 거부할 수 있습니다. 설치된 앱이 만든 빈 셸 초안에 주입하면 피할 수 있습니다. — https://github.com/zxypro1/capcut-shell-inject ; https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md (2026-09-10~11, 신뢰도 medium)
- pyCapCut이 draft_meta_info.json의 draft_materials를 비워 두면, CapCut 9.1.0(macOS)이 가져온 미디어를 접근 불가로 표시하고 relink를 요구한다는 보고가 있습니다(미해결). — https://github.com/GuanYixuan/pyCapCut/issues/13 (2026-08-18, 신뢰도 medium)
- JianYing 11.4.0(macOS)은 평문 draft_info.json을 받아 연 뒤 제자리에서 암호화 형식으로 업그레이드합니다. JianYing 9.0.0(Windows)은 도구가 쓴 평문 초안을 열고, 닫을 때 레거시 미러를 암호화합니다. — https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md (2026-09-10, 신뢰도 medium)
- pyJianYingDraft 메인테이너는 JianYing 6+ 로컬 AES-GCM 복호화 PR #189를 2026-06-25에 거절했습니다. 사유는 '제3자 앱 암호화 포맷의 구체적 복호화 구현'에 따른 거버넌스·법적 리스크와 프라이버시이고, 대신 사용자가 권리를 확인한 경우 쓸 수 있는 fallback_loader 훅을 제시했습니다. — https://github.com/GuanYixuan/pyJianYingDraft/pull/189 (2026-06-25, 신뢰도 high)
- capcut-cli는 암호화를 감지만 하고 복호화하지 않습니다. 사유는 법적 리스크(역공학된 비허가 알고리즘)와 포인트 릴리스마다 바뀌는 키·알고리즘입니다. — https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md (2026-09, 신뢰도 high)
- CapCut 이용약관(2026-04-15 개정) 6조는 'copy, decipher, modify, adapt, translate, reverse engineer, disassemble, decompile'과 'circumvent or bypass any measures'를 금지합니다. 10조는 Company Content를 제한적·취소 가능한 라이선스로만 허용합니다. 한국 사용자에게는 한국법이 준거법이고 한국 법원이 전속관할입니다. — https://www.capcut.com/clause/terms-of-service (2026-04-15, 신뢰도 high)
- CapCut 공식 도움말: 구버전은 비활성화될 수 있고(older versions may be disabled), 오래된 버전은 클라우드나 계정 로그인과 호환되지 않을 수 있습니다. 구버전 설치 패키지는 제공하지 않습니다. — https://www.capcut.com/help/being-forced-to-update-capcut ; https://www.capcut.com/help/return-to-older-version-of-capcut (2025-12-25 / 2026-01-06, 신뢰도 high)
- CapCut 공식 도움말: 템플릿 수익화가 켜져 있지 않으면 사용자는 템플릿 초안을 편집할 수 없고, 원작자의 영상·사진 소재는 보호됩니다. — https://www.capcut.com/help/what-is-template-monetization (2026-01-07, 신뢰도 high)
- 한국 저작권법 104조의2는 기술적 보호조치(접근통제 포함)의 무력화를 금지합니다. 101조의4 프로그램코드역분석은 정당한 이용자가 호환에 필요한 정보를 얻는 경우에만 허용되고, 다른 목적 이용이나 제3자 제공은 금지됩니다. 법률 자문이 아닌 일반 법리 요약입니다. — https://copyright.or.kr/eng/doc/quarterly_pdf/231 Law and Policy Study on Reverse Engineering Provisions under the Copyright Act.pdf (확인 불가(학술 자료), 신뢰도 medium)
- 'Filmcraft'라는 이름의 MCP나 영상 편집 프로젝트는 웹 검색 2회로도 찾지 못했습니다. — WebSearch 'Filmcraft MCP video editing AI agent github', '"filmcraft" AI video editor agent' (2026-10-15, 신뢰도 medium)

**미해결 질문:**

- CapCut 9.6.0이 '로컬에서 새로 만든' 초안도 암호화하나요? 9.6.0이 저장한 로컬 초안이 아직 없어 확인하지 못했습니다. 9.6.0에서 빈 초안을 만들고 클립 하나를 넣어 저장·종료한 뒤 첫 바이트를 확인하면 알 수 있습니다.
- 클라우드 다운로드 초안 중 일부만 암호화되는 기준은 무엇인가요(업로더 버전, 유료·상용 소재 포함 여부, 서버 A/B 플래그 등)? 벤츠·롱폼·옵틱글래스는 암호화됐고 숏폼 (1)·(2)는 평문이었습니다.
- 옵틱글래스 초안의 루트 draft_content.json은 17:49 시점에 평문이었습니다. virtual_store에는 암호화 대상으로 등록돼 있는데, 다음 저장 때 암호화되나요?
- pyCapCut·cli-anything-capcut이 만든 평문 초안이 CapCut 9.6.0(Windows)에서 'unconventional path' 경고나 relink 없이 열리나요? 공개 검증은 9.3.0까지만 있습니다.
- JianYing 6.0의 정확한 출시일과 빌드 번호는 공식 릴리스 노트로 확인하지 못했습니다(커뮤니티 서술과 2024-04-15 메모만 있음).
- 사용자가 말한 'Filmcraft & MCP'의 정확한 저장소나 제품명은 무엇인가요? 웹 검색으로 찾지 못했습니다. 링크가 있으면 같은 기준으로 다시 평가할 수 있습니다.
- 팀 스페이스 초안의 template.json.bak(평문 스냅샷)을 템플릿 원본으로 읽는 것이 팀이나 CapCut 정책상 허용되나요? 기술적 우회는 아니지만 스냅샷이 오래됐을 수 있고, 팀 소유 콘텐츠일 수 있습니다.

### local-cli

이미 받아 둔 cli-anything-capcut v0.5.7(juliang8507)은 'AI 에이전트 → CapCut 드래프트 생성' 경로의 뼈대로 쓰기에 가장 가깝습니다. 갖춘 것: 이벤트 소스 세션, --json 출력, Claude 스킬, validate/review/preview. 다만 '다운받은 템플릿 재현'에는 그대로 쓸 수 없습니다. 근거는 아래와 같습니다.
(1) 레시피 포맷: {name,width,height,fps,operations:[{op,args}]}. 템플릿 .md의 장면·타이밍·텍스트·효과를 add_video/add_image/add_text/add_effect/add_filter/add_video_transition/add_text_animation/add_keyframe/add_audio(_fade)로 1:1 옮길 수는 있습니다. 하지만 apply_recipe가 레시피의 "id"를 버리고 op_N으로 다시 매기며(core/recipe.py:84-94, core/session.py:174-175), width/height/fps도 무시합니다. 또 "duration":"auto"는 실제로 0µs로 파싱됩니다(직접 실행해 확인). 그래서 동봉된 레시피 템플릿 5종(segment_ref "main", import_srt, add_color_adjust, "auto")은 그대로 적용하면 깨집니다.
(2) 기존 드래프트 가져오기: import-draft는 평문 JSON만 읽습니다(json.loads, import_draft.py:31-40). 그나마 video/audio/text만 복원하는 손실 변환이고 애니메이션·마스크·효과는 버립니다. 이 PC의 9.6 드래프트처럼 암호화된 draft_content.json(base64 형태 텍스트)은 '파싱 실패'로 끝납니다. pyCapCut의 템플릿 모드(load_template / replace_material_by_name / replace_text)는 CLI가 아예 쓰지 않습니다.
(3) MP4 렌더: render는 pyCapCut JianyingController(uiautomation)로 중국판 剪映专业版 창만 조종하므로 국제판 CapCut에서는 동작하지 않습니다. render-headless는 CapCut도 저장된 드래프트도 쓰지 않고, 세션 op 로그를 ffmpeg filter_complex로 직접 조립합니다. 지원 범위는 V1 concat/xfade, V2+ 오버레이, 오디오 믹스, SRT 번인뿐입니다. 필터·효과·애니메이션·스티커·마스크·색보정·텍스트 위치/애니메이션·속도는 반영되지 않습니다. 이 PC에는 ffmpeg가 PATH에 없습니다.
(4) MCP와 비교: 저장소에 MCP 코드는 없고, README는 토큰 효율 때문에 CLI를 택했다고 설명합니다(외부 벤치마크 인용이며 자체 측정은 아님). Claude Code처럼 셸이 있는 에이전트라면 CLI+스킬로 충분합니다. MCP 래퍼는 셸이 없는 클라이언트용으로만 의미가 있고, 템플릿 재현 능력 자체는 바뀌지 않습니다.

**권장:**

권장 전략은 '하이브리드, CLI 유지, MCP 추가 안 함'입니다.

1. 백본: 이미 받은 cli-anything-capcut + Claude 스킬을 Claude Code(Bash)에서 그대로 쓰세요. 셸이 있는 에이전트라면 MCP 래퍼는 이득이 거의 없습니다. 템플릿 재현 능력도 같아서 지금은 만들지 않는 게 맞습니다(YAGNI). Claude Desktop처럼 셸이 없는 클라이언트가 필요해질 때 coarse tool 5~8개짜리 얇은 래퍼만 추가하면 됩니다.

2. 템플릿 .md → 레시피 변환은 에이전트가 직접 작성하게 하세요. plan 명령(API 키 필요, fade 인자 버그 있음)과 동봉 레시피 템플릿(id·auto·미등록 op 때문에 깨짐)은 쓰지 마세요. 변환 규칙:
- 캔버스: project new --preset/--width/--height로 먼저 정합니다. 레시피의 width는 무시됩니다.
- 장면: add_video/add_image에 start와 duration을 명시적으로 줍니다('auto' 금지, 'Ns'나 µs). 클립 중간 구간이 필요하면 ffmpeg로 미리 잘라서(asset transcode 또는 별도 trim) 넣습니다.
- 전환·애니메이션·키프레임: segment_ref를 '레시피 순서 기준 op_N'으로 계산하거나, CLI를 순차 호출하며 반환된 id를 받아 씁니다.
- 텍스트: add_text + style/clip_settings + add_text_animation. 효과·필터 이름은 alias search로 확인합니다.
- 색: color_adjust 계열 CLI. 오디오: add_audio + add_audio_fade(fade_in/fade_out).
- 레퍼런스 영상은 media-info와 preview --thumbs로 타이밍을 맞추는 데만 쓰입니다. 장면·비트 검출 기능은 없습니다.

3. '정확한 재현'이 목표라면, 템플릿 드래프트가 평문일 때(CapCut 9.1 이하로 저장된 것, 또는 template.json.bak) pyCapCut 템플릿 모드(duplicate_as_template → replace_material_by_name/replace_text)로 슬롯만 교체하는 작은 명령을 추가하는 것이 최선입니다. 암호화된 9.6 드래프트는 어떤 경로로도 직접 다룰 수 없으니, 템플릿 원본을 평문 상태로 확보하는 것이 전제입니다.

4. 렌더: 국제판 CapCut에서는 render가 동작하지 않습니다. 최종본은 save 후 CapCut GUI에서 수동 export하고, render-headless는 ffmpeg를 설치한 뒤 구조·타이밍 미리보기용으로만 쓰세요(효과·필터·애니메이션이 빠짐).

5. 크로스플랫폼, 헤드리스 최종 렌더, MCP 이식성이 CapCut 효과 충실도보다 중요해지면 그때 FilmCraft를 검토하세요. 단 CapCut 템플릿 import가 없으므로 '재현'이 아니라 '재구현'이 됩니다.

| 선택지 | 템플릿 적합 | 이식성 | 성숙도 |
|---|---|---|---|
| cli-anything-capcut v0.5.7 + 동봉 Claude 스킬 (현 상태 그대로) | 2/5 | 2/5 | v0.5.7(2026-09-21), GitHub 별 7개·포크 1개·커밋 15개, 1인 유지보수입니다. 테스트 398개가 통과한다고 자체 보고합니다. CapCut 9.3.0에서 GUI 실측(드래프트 열림, 세그먼트 배치, 폰트 반영)을 했고, postprocess 8종은 시각 확인을 하지 못했습니다. 이 PC에는 아직 설치되지 않았습니다(cli_anything import 불가, pycapcut만 paperclip의 pyCapCut에서 import됨). |
| cli-anything-capcut + pyCapCut 템플릿 모드 확장 (평문 템플릿 드래프트 슬롯 교체) | 4/5 | 2/5 | API는 pyCapCut upstream(@00c223a, 2025-09-12 커밋, 로컬 패치 있음)에 이미 있습니다. 확장 코드는 아직 존재하지 않으며 직접 작성해야 합니다(수십~백여 줄 규모로 추정). |
| cli-anything-capcut을 얇은 MCP 서버로 감싸기 | 2/5 | 3/5 | 존재하지 않으며 직접 작성해야 합니다. |
| 기존 커뮤니티 CapCut MCP 서버 (예: JmsLdrn/capcut-mcp, sun-guannan/VectCutAPI의 mcp_server.py) | 3/5 | 3/5 | JmsLdrn/capcut-mcp는 별 9개·커밋 1개입니다. VectCutAPI는 별 약 2.3k이고 클라우드 렌더 모듈은 비공개입니다(2026-10-15 조회). |
| FilmCraft (storytold/filmcraft) CLI/MCP | 1/5 | 5/5 | 'alpha'라고 스스로 표기합니다(Premiere 대비 기능 폭 약 86%, '실사용 준비' 약 56%). GitHub 페이지에는 별 13.5k로 표시되나 릴리스·날짜는 확인되지 않았습니다(2026-10-15 조회). |

**사실과 근거:**

- README는 MCP 대신 CLI를 택한 이유를 '도구 스키마가 컨텍스트를 상시 점유하기 때문'이라고 설명합니다. 인용한 토큰 효율 벤치마크(ScaleKit 2026, Jannik Reinhard 2026)는 도구 방식 일반에 대한 외부 측정이며 이 프로젝트를 직접 잰 수치가 아니라고 명시합니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/README.ko.md:17-27 (2026-09-21 (v0.5.7), 신뢰도 high)
- render는 pyCapCut의 JianyingController에 위임합니다. 이 코드는 창 이름 '剪映专业版'과 '导出' 같은 중국어 UI 라벨을 찾으므로 국제판 CapCut에서는 동작하지 않습니다(CapCut 9.4.0 실측 오류: 剪映窗口未找到). — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/commands/render.py:3-11,94-116; CHANGELOG.md:8-30 (2026-09-21, 신뢰도 high)
- pyCapCut issue #17(국제판 CapCut에서 JianyingController 미동작)은 열린 상태로 미해결입니다. 메인테이너는 CapCut 9.5.0.4050의 export 대화상자가 UI Automation/MSAA에 자식 컨트롤을 노출하지 않는다고 답했습니다. — https://github.com/GuanYixuan/pyCapCut/issues/17 (2026-09-21 개설 / 2026-09-25 메인테이너 답변 (2026-10-15 조회), 신뢰도 high)
- render-headless는 CapCut이나 저장된 드래프트를 전혀 쓰지 않습니다. 세션 op 로그를 해석해 ffmpeg 명령(filter_complex: concat/xfade, overlay, amix, subtitles)을 조립하고, libx264/aac로 인코딩합니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/commands/render_headless.py:1-29,647-1132 (2026-09-21 (v0.5.7), 신뢰도 high)
- render-headless의 지원 op는 add_track/video/image/audio/text, fade, transition(xfade 9종), keyframe(uniform_scale/alpha/transform_x·y)뿐입니다. animation/filter/effect/mask/background/sticker/audio_effect는 미지원입니다. text_style_patch/color_adjust/color_wheels는 조용히 무시합니다. set_reverse·add_lut 같은 postprocess op는 '알 수 없는 op'로 분류되어, --allow-unsupported가 없으면 렌더가 실패합니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/commands/render_headless.py:60-90,263-274,1166-1173 (2026-09-21 (v0.5.7), 신뢰도 high)
- render-headless는 텍스트를 단일 스타일 SRT로 번인합니다. 세그먼트별 스타일이 다르면 첫 세그먼트 스타일로 통일하고, 글자 크기와 위치(clip_settings)는 반영하지 않습니다. V1의 transform_x/y 키프레임과 speed도 반영하지 않습니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/commands/render_headless.py:390-474,757-790,1044-1054 (2026-09-21 (v0.5.7), 신뢰도 high)
- import-draft는 draft_content.json을 json.loads로 읽습니다. 암호화된 파일은 'draft_content.json 파싱 실패'로 중단됩니다. 복원 범위는 video/audio/text 트랙 세그먼트(시간, 경로, 텍스트, 크기·색)뿐이고, extra_material_refs(애니메이션, 효과, 마스크 등)는 요약만 남깁니다. 결과물은 '읽기 전용 분석용, lossy' 세션입니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/commands/import_draft.py:17-21,31-40,215-254,269-272 (2026-09-21 (v0.5.7), 신뢰도 high)
- import-draft --from은 폴더뿐 아니라 JSON 파일 경로도 직접 받습니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/commands/import_draft.py:24-28 (2026-09-21 (v0.5.7), 신뢰도 high)
- 이 PC의 암호화 드래프트 2개('롱폼 영상 프로젝트', '57.08 벤츠 지바겐 광각 [26.04.13]')는 draft_content.json과 Timelines/<uuid>/draft_content.json이 모두 base64 형태 텍스트입니다(JSON 아님). 다만 같은 폴더의 template.json.bak은 평문 JSON입니다. '롱폼' 쪽은 트랙 3개, 세그먼트 36개, 약 132.7초 분량이며 placeholder_infos 36개와 drafts 7개를 담고 있어, 템플릿에서 만든 프로젝트의 초기 스냅샷으로 보입니다. — C:/Users/bssho/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/롱폼 영상 프로젝트/template.json.bak (로컬 읽기 전용 파싱) (2026-10-15, 신뢰도 medium)
- apply_recipe는 각 operation의 op와 args만 append_operation에 넘기고 레시피의 'id'는 버립니다. append_operation은 항상 _next_op_id(op_N)를 새로 붙입니다. 따라서 'segment_ref':'main'처럼 사용자 정의 id를 참조하는 레시피는 replay에서 'segment_ref not found'로 실패합니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/core/recipe.py:84-94; core/session.py:158-176,686-691; core/segment_utils.py:59-63 (2026-09-21 (v0.5.7), 신뢰도 high)
- apply_recipe는 레시피의 width/height/fps를 적용하지 않습니다. 캔버스는 import 대상 세션(project new --preset/--width/--height)에서 정해집니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/core/recipe.py:79-107; commands/project.py:31-41 (2026-09-21 (v0.5.7), 신뢰도 high)
- parse_time_value('auto')는 0을 반환합니다(로컬 python -I -B로 직접 실행해 확인). 'auto'는 start에서만 해석되므로, 레시피나 CLI의 duration 'auto'는 길이 0µs 세그먼트가 됩니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/core/time_utils.py:22-83; core/op_handlers.py:160-169; commands/media.py:35-49 (2026-10-15 실행 검증, 신뢰도 high)
- 동봉 레시피 템플릿(claude-skill/references/recipes/*.json)은 미등록 op인 'import_srt'와 'add_color_adjust'(실제 op 이름은 color_adjust이고 srt import는 add_text로 전개됨), duration 'auto', 사용자 정의 id를 씁니다. luxury-b2b.json은 SKILL.md가 '제거됨'이라고 적은 필터 별칭 'cinematic'을 씁니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/claude-skill/references/recipes/luxury-b2b.json; core/op_handlers.py:617-657; claude-skill/SKILL.md:93-96 (2026-09-21 (v0.5.7), 신뢰도 high)
- add_video 핸들러는 source_timerange를 항상 0부터 잡습니다. 소스 in-point(클립 중간 구간)를 지정하는 인자가 없습니다(코드 전체에서 source_start 같은 인자 0건). — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/core/op_handlers.py:155-180 (2026-09-21 (v0.5.7), 신뢰도 high)
- save는 매번 세션을 replay해 DraftFolder.create_draft(..., allow_replace=True)로 같은 이름의 새 드래프트를 만들고 덮어씁니다. CapCut GUI에서 같은 드래프트에 한 수정은 사라집니다. pyCapCut 템플릿 모드(load_template / duplicate_as_template / replace_material_by_name / replace_text / import_track)는 CLI 어디에서도 호출하지 않습니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/capcut_cli.py:174-185; C:/Users/bssho/Downloads/paperclip-master/pyCapCut/pycapcut/draft_folder.py:109,127; pycapcut/script_file.py:201,531,588,626,672 (2026-09-21 (CLI) / 2025-09-12 (pyCapCut @00c223a), 신뢰도 high)
- plan 명령은 Claude API(anthropic SDK, ANTHROPIC_API_KEY 필요, 기본 모델 claude-sonnet-4-5)로 자연어를 레시피 JSON으로 바꾸고, validate_recipe 실패 시 1회 재시도합니다. 단 LLM에 주는 fade 인자 설명(in_duration/out_duration)이 핸들러가 읽는 fade_in/fade_out과 달라서, 생성된 페이드는 0으로 처리됩니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/commands/plan.py:48,52,242-281,300; core/op_handlers.py:421-422 (2026-09-21 (v0.5.7), 신뢰도 high)
- SKILL.md와 render-workflow.md는 아직도 GUI render를 '정확함/최종 납품용 기본값'으로 권장합니다. 이는 v0.5.7 CHANGELOG의 '국제판 미동작' 확인과 모순됩니다. 또 SKILL.md는 'CapCut MCP 도구 호출'을 안티패턴(해당 MCP 없음)으로 적어 두었습니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/claude-skill/SKILL.md:215-224,452; claude-skill/references/render-workflow.md:83-129 (2026-09-21 (v0.5.7), 신뢰도 high)
- preset kenburns의 pan-lr/pan-tb 패턴은 'transform_x/transform_y' 키프레임 op를 기록합니다. 그러나 replay 핸들러의 _KEYFRAME_PROP_MAP에는 position_x/y만 있어 '알 수 없는 keyframe property' 예외가 날 것으로 보입니다. 또 키프레임 time을 타임라인 절대시각(cursor_us)으로 넘기는데, pyCapCut add_keyframe은 세그먼트 기준 오프셋을 받습니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/cli_anything/capcut/commands/preset.py:599-668; core/op_handlers.py:474-503; C:/Users/bssho/Downloads/paperclip-master/pyCapCut/pycapcut/segment.py:247-269 (2026-09-21 (v0.5.7), 신뢰도 medium)
- 이 PC에서 cli-anything-capcut은 설치되어 있지 않습니다(cli_anything import 불가). pycapcut은 C:/Users/bssho/Downloads/paperclip-master/pyCapCut(로컬 수정: script_file.py, util.py)에서 import됩니다. ffmpeg/ffprobe는 PATH에 없어 render-headless와 미디어 길이 자동 감지가 지금은 동작하지 않습니다. — 로컬 확인 (python 3.14 importlib.util.find_spec, Get-Command ffmpeg, git status) (2026-10-15, 신뢰도 high)
- CLI가 만든 드래프트에 대한 GUI 실측(드래프트 인식, 세그먼트 배치, 폰트)은 CapCut 9.3.0에서만 이루어졌습니다. postprocess 8종의 시각 확인은 하지 못했습니다. 9.6에서의 동작은 문서상 검증된 적이 없습니다. — C:/Users/bssho/Downloads/cli-anything-capcut-main/cli-anything-capcut-main/docs/capcut-gui-verification.md:6-7,53-58; claude-skill/SKILL.md:110-117 (2026-09-01, 신뢰도 high)
- juliang8507/cli-anything-capcut의 GitHub 저장소는 별 7개, 포크 1개, 커밋 15개이며 Releases는 비어 있습니다. — https://github.com/juliang8507/cli-anything-capcut (2026-10-15 조회, 신뢰도 medium)
- FilmCraft(storytold/filmcraft)는 Rust 기반 오픈소스 NLE입니다. filmcraft-cli(650개 이상 명령), 'filmcraft-cli -- mcp' 헤드리스 MCP 서버, --control JSON-lines 제어 서버를 제공하고 FCPXML/OTIO/EDL/AAF 교환을 지원합니다. CapCut 드래프트 import는 언급이 없고, 스스로 'alpha'라고 표기합니다. — https://github.com/storytold/filmcraft ; https://sourceforge.net/mirror/filmcraft/profile/ (2026-10-15 조회, 신뢰도 medium)
- JmsLdrn/capcut-mcp는 기존 드래프트를 읽고 세그먼트를 복제·이동·트림·분할하는 MCP 도구를 제공합니다(capcut_read_timeline, capcut_raw_patch 등). export/렌더 도구는 없고, 암호화 드래프트도 언급하지 않습니다. — https://github.com/JmsLdrn/capcut-mcp (2026-10-15 조회, 신뢰도 medium)
- VectCutAPI(sun-guannan)는 mcp_server.py(stdio)와 HTTP API로 드래프트 생성을 제공합니다. 클라우드 렌더 모듈은 오픈소스가 아니고, 암호화 드래프트 대응은 언급이 없습니다. — https://github.com/sun-guannan/VectCutAPI (2026-10-15 조회, 신뢰도 medium)

**미해결 질문:**

- 사용자가 말한 '다운받은 CapCut 템플릿 .md'의 실제 포맷과 예시가 필요합니다. Downloads 아래에서는 찾지 못했습니다. 장면별 시간, 효과 이름(중국어 enum인지, CapCut 리소스 ID인지), 텍스트 스타일이 어떤 형태로 적혀 있는지에 따라 레시피 변환 규칙이 달라집니다.
- CapCut 9.6이 pyCapCut/cli-anything-capcut이 쓴 평문 draft_content.json을 정상적으로 여는지, 열고 저장하면 다시 암호화하는지 아직 검증되지 않았습니다(문서 실측은 9.3.0까지).
- '롱폼 영상 프로젝트'의 template.json.bak(평문, placeholder_infos 36개)이 다운받은 템플릿 원본과 같은지, 그리고 import-draft나 pyCapCut load_template의 입력으로 신뢰할 수 있는지 확인이 필요합니다.
- 사용자가 말한 'Filmcraft & MCP'가 storytold/filmcraft를 뜻하는지 확인이 필요합니다. 맞다면 그 MCP 도구 목록(docs/agents.md)은 아직 확인하지 않았습니다.
- 최종 산출물이 CapCut 렌더 품질(템플릿 효과 그대로)이어야 하는지, ffmpeg 수준(컷, 자막, 전환만)으로도 충분한지 정해야 합니다. 이 답에 따라 render-headless를 최종 렌더로 쓸 수 있는지가 갈립니다.
- 템플릿의 효과·전환·텍스트 애니메이션이 pyCapCut enum(별칭)에 있는지 확인이 필요합니다. 다운로드형 CapCut 리소스 ID 효과라면 재생성 방식으로는 재현할 수 없고, 템플릿 모드 복제만 가능합니다.

## 3. pyCapCut 구조 리뷰 (확인된 이슈)

`fix/template-mode-data-loss` @00e08e6에서 고친 항목은 ✅로 표시했습니다. 나머지는 아직 남아 있습니다.

### template-data

- ✅ [high] `pycapcut/draft_folder.py:57` remove()/create_draft(allow_replace=True)에서 draft_name이 검증되지 않아 "", ".", "..", 절대경로로 초안 루트 전체 또는 그 상위 폴더가 rmtree됨
- ✅ [high] `pycapcut/script_file.py:800` dump()가 파일을 "w"로 먼저 연 뒤 dumps()를 호출하므로, 직렬화 중 예외가 나면 원본 draft_content.json이 0바이트로 잘림
- [low] `pycapcut/draft_folder.py:81` create_draft(allow_replace=True)가 새 내용이 생기기 전에 기존 초안을 즉시 rmtree함. save() 전에 스크립트가 실패하면 원본은 사라지고 meta만 남은 깨진 초안이 남음
- [low] `pycapcut/draft_folder.py:150` duplicate_as_template(allow_replace=True)가 copytree(dirs_exist_ok=True)로 기존 폴더 위에 병합 복사하여 이전 초안의 파일(커버, .bak, template-2.tmp, Resources)이 남음
- [low] `pycapcut/draft_folder.py:46` has_draft()는 대소문자를 구분하는 정확한 이름 비교인데, create_draft/remove는 os.path.exists를 쓰므로 Windows에서 판단이 엇갈려 다른 초안이 삭제될 수 있음
- [low] `pycapcut/draft_folder.py:85` draft_meta_info.json은 정적 템플릿을 그대로 복사할 뿐이라 draft_name/draft_fold_path/draft_root_path/tm_duration/draft_materials가 채워지지 않고, draft_timeline_materials_size_는 8114로 고정됨
- [low] `pycapcut/draft_folder.py:150` duplicate_as_template이 원본 meta를 그대로 복사해, 새 초안이 원본의 draft_name/draft_fold_path를 가리키고 tm_duration도 저장 후 content와 어긋남
- [low] `pycapcut/script_file.py:779` draft_content.json의 create_time/update_time이 항상 0이고, name/path도 빈 문자열로 저장됨
- [low] `pycapcut/script_file.py:781` dumps()가 canvas_config.ratio를 항상 "original"로 덮어써서 템플릿의 화면비 설정(예: "9:16")이 사라짐
- [low] `pycapcut/draft_folder.py:150` duplicate_as_template이 실패해도 복사된 폴더가 남아 재시도가 FileExistsError로 막히고, 같은 이름으로 allow_replace하면 알 수 없는 shutil.Error가 남
- ✅ [low] `pycapcut/script_file.py:176` 수정 (c)가 불완전: 클래스 속성은 fps: float인데 ScriptFile.__init__과 create_draft는 fps: int = 30이라, 새 초안은 "fps": 30(int)으로, 로드한 초안은 30.0으로 저장됨

### template-mode

- ✅ [medium] `pycapcut/script_file.py:342` 텍스트/스티커 세그먼트의 speed 머티리얼이 등록되지 않아, pycapcut이 만든 텍스트 트랙은 import_track 시 항상 AssertionError가 발생함
- ✅ [medium] `pycapcut/template_mode.py:167` ShrinkMode.cut_head가 시작점만 뒤로 밀고 길이는 줄이지 않아 다음 세그먼트와 겹침
- ✅ [medium] `pycapcut/template_mode.py:187` ExtendMode.extend_head가 시작점만 앞으로 옮기고 길이는 늘리지 않음(세그먼트가 이동만 하고 속도가 어긋남)
- [medium] `pycapcut/script_file.py:561` import_track이 현재 세그먼트가 아닌 raw_data(로드 당시 원본)에서 머티리얼 id를 모아, 수정한 트랙을 가져오면 참조가 끊김
- [medium] `pycapcut/script_file.py:569` import_track이 text_templates → texts 같은 중첩 참조를 따라가지 않아, 텍스트 템플릿 트랙을 가져오면 하위 텍스트가 빠지고 replace_text는 KeyError가 나거나 조용히 아무것도 하지 않음
- ✅ [medium] `pycapcut/script_file.py:620` replace_material_by_name이 'type' 대신 존재하지 않는 'material_type' 키에 써서, 동영상을 사진으로(또는 반대로) 바꿔도 type이 그대로 남음
- [medium] `pycapcut/template_mode.py:201` replace_material_by_seg가 호출자의 Timerange 객체를 그대로 저장하고, cut_material_tail에서 그 객체를 직접 수정함(세그먼트끼리 같은 객체를 공유)
- [medium] `pycapcut/script_file.py:584` 템플릿 모드 편집 후 초안 duration이 갱신되지 않음: import_track은 offset을 무시하고, replace_material_by_seg의 extend/push는 길이를 반영하지 않음
- [low] `pycapcut/script_file.py:578` 서로 다른 두 트랙이 같은 머티리얼을 공유하면, 각각 import_track할 때 같은 id의 머티리얼이 두 번 복사됨
- [low] `pycapcut/template_mode.py:128` 편집하지 않고 load→save만 해도 세그먼트별 render_index가 트랙 최댓값으로 덮어써지고, tracks 배열 순서가 바뀜
- [low] `pycapcut/template_mode.py:182` 템플릿 모드가 세그먼트 목록이 시간순이라고 가정하지만, pycapcut은 추가한 순서대로 저장함(이웃 판정 오류로 겹침이나 순서 역전 발생)
- [low] `pycapcut/script_file.py:696` replace_text가 원래 텍스트가 빈 문자열이면 ZeroDivisionError로 실패하고, 새 텍스트가 빈 문자열이면 styles가 모두 사라짐

### generation

- [medium] `pycapcut/audio_segment.py:175` AudioSegment.add_keyframe가 문자열 시간을 해석하지 않음: README 예제를 따라 하면 time_offset이 "0s" 문자열로 저장됨
- [medium] `pycapcut/script_file.py:419` import_srt의 기본 인자 TextStyle/ClipSettings를 모든 자막과 이후 호출이 함께 공유함
- [medium] `pycapcut/script_file.py:305` add_segment 이후의 세그먼트 수정(애니메이션·효과·텍스트 등)이 머티리얼에 반영되지 않아 끊긴 extra_material_refs가 생김
- [low] `pycapcut/script_file.py:441` import_srt가 원자적이지 않음: 겹치는 큐나 파싱 오류가 나면 반쯤 들어간 상태로 남고, 같은 트랙명으로 재시도해도 실패함
- [low] `pycapcut/time_util.py:25` tim()이 단위 없는 문자열을 조용히 0으로, 끝에 남은 숫자는 버림 ("1.5"→0, "1m30"→60s)
- ✅ [low] `pycapcut/segment.py:201` 텍스트·스티커 세그먼트가 materials.speeds에 없는 Speed id를 항상 참조함
- [low] `pycapcut/local_materials.py:68` VideoMaterial의 crop_settings 기본값 CropSettings()를 모든 머티리얼이 공유함
- [low] `pycapcut/segment.py:257` uniform_scale과 scale_x/scale_y의 상호배타 검사가 한 방향만 적용되어 균일 스케일 키프레임이 X축 전용으로 바뀜
- [low] `pycapcut/text_segment.py:348` 텍스트 루프 애니메이션 시작점이 인트로의 끝이 아니라 시작(항상 0)으로 계산되어 인트로와 겹침
- [low] `pycapcut/script_file.py:298` 세그먼트와 Timerange를 참조로 공유해도 막지 않음: 한 세그먼트를 옮기면 다른 세그먼트도 움직이고, 같은 세그먼트를 두 번 추가하면 id와 머티리얼이 중복됨
- [low] `pycapcut/script_file.py:378` ScriptFile.add_effect는 독스트링과 달리 초과 파라미터를 조용히 버림 (VideoSegment.add_effect의 오류 메시지는 '音频效果'로 잘못됨)
- [low] `pycapcut/time_util.py:41` Timerange와 애니메이션 시간에 검증이 없음: 음수 duration과 음수 아웃트로 시작점을 받아들이고, duration=0은 기본값으로 바뀜

### metadata

- [medium] `pycapcut/video_segment.py:370` IntroType/OutroType 기본 길이(최대 3초)가 클램프되지 않아 짧은 영상 세그먼트에서 출장 애니메이션 start가 음수가 됨
- [low] `pycapcut/metadata/video_scene_effect.py:3371` VideoSceneEffectType 7개 파라미터의 default_value가 [min,max] 범위를 벗어남(최대 2.5 > 1.0)
- [low] `pycapcut/metadata/video_scene_effect.py:4361` VideoSceneEffectType.圣诞Kira와 圣诞kira가 from_name 정규화 후 충돌해 from_name('圣诞kira')가 다른 리소스를 돌려줌
- [low] `README.md:456` README/english_readme/pypi_readme 예제가 존재하지 않는 enum 멤버(FilterType.原生肤, FilterType.冰雪世界, FontType.文轩体)와 `from pyJianYingDraft import`를 사용함
- [low] `pycapcut/metadata/effect_meta.py:108` from_name이 CapCut 표시 이름으로 175개 멤버(FontType은 348개 중 113개)를 찾지 못함
- [low] `pycapcut/metadata/tone_effect.py:4` tone_effect.py / speech_to_song.py는 25-08 갱신 때 export에서 빠졌지만 파일은 남아 배포되고, 쓰려고 하면 TypeError가 남
- [low] `pycapcut/metadata/audio_scene_effect.py:24` AudioSceneEffectType 36개 항목이 음색(tone) 모델 md5를 공유하고 파라미터가 없어, 음색 효과가 '场景音' 카테고리로 잘못 분류됐을 가능성이 큼
- [low] `pycapcut/text_segment.py:339` TextSegment.add_animation이 AnimationMeta.duration을 무시함: 텍스트 애니메이션 83개의 기본 길이와 비정상값(60초/100초)이 죽은 데이터
- [low] `pycapcut/metadata/audio_scene_effect.py:188` AudioSceneEffectType의 Commuting/In_Womb/Office가 같은 이름 'strength' 파라미터를 2개씩 가짐
- [low] `pycapcut/metadata/effect_meta.py:87` parse_params 오류 메시지가 EffectParam 객체 repr을 출력해 어느 파라미터가 문제인지 알 수 없음
- [low] `pycapcut/metadata/__init__.py:10` `import pycapcut`가 약 4,936개 enum 멤버를 즉시 생성해 import 시간의 약 절반을 메타데이터가 차지함
- [low] `pycapcut/metadata/effect_meta.py:140` 메타데이터 클래스/모듈 이름과 export 범위가 서로 맞지 않음(TransitionMeta/EffectEnum 미노출, MaskMeta docstring 오기 등)

### docs

- [medium] `README.md:442` README의 효과/필터/애니메이션 예제 4개가 존재하지 않는 패키지 `pyJianYingDraft`를 import하고, 정의되지 않은 `draft.`를 사용함
- ✅ [medium] `pycapcut/script_file.py:342` pycapcut으로 만든 텍스트/스티커 세그먼트가 speed 소재를 내보내지 않아 참조가 끊기고, README의 '트랙 가져오기' 기능이 데모 초안에서 AssertionError로 죽음
- [medium] `README.md:456` README 예제가 존재하지 않는 enum 멤버(FilterType.原生肤/冰雪世界, FontType.文轩体)를 사용해 AttributeError가 남
- [medium] `pycapcut/audio_segment.py:175` README대로 `audio_segment.add_keyframe("0s", 0.6)`을 호출하면 문자열 "0s"가 그대로 JSON에 기록되고, 다음 키프레임 추가 시 TypeError가 남
- [medium] `pycapcut/script_file.py:584` README 예제처럼 `import_track(..., offset=...)`을 쓰면 초안 duration이 offset을 반영하지 않음
- [low] `README.md:548` '导入字幕' 예제에 쉼표가 빠져 SyntaxError가 나고, 쉼표를 고쳐도 같은 트랙에 반복 import하면 SegmentOverlap이 남
- [low] `README.md:29` 기능 목록이 쓸 수 없는 '批量导出' 기능을 ☑️로 표시하고, `#批量导出草稿` 앵커는 없는 제목을 가리킴
- [low] `README.md:485` '添加片段动画' 설명(타입 하나만 받고 길이는 기본값)이 현재 시그니처와 demo.py에 맞지 않음
- [low] `README.md:311` '素材截取与整体变速' 예제: 속도 주석이 틀리고(5.0, 실제 4.0), 중간에 예외가 나서 끝까지 실행되지 않으며, 메인 트랙 세그먼트가 0초에서 시작하지 않음
- [low] `README.md:344` '视频整体调节'이 clip_settings로 자르기·밝기를 설정할 수 있다고 하지만 ClipSettings에는 해당 매개변수가 없음
- [low] `README.md:42` 기능 목록에 ☑️로 적힌 스티커 추가, 텍스트 테두리·배경, 이미지 자르기, 오디오 효과에 사용 예제나 클래스 설명이 없음
- [low] `english_readme.md:84` 중·영 문서와 demo.py 사이 불일치, 그리고 pyJianYingDraft 시절 이름이 남아 있음

### packaging

- ✅ [medium] `pycapcut/script_file.py:123` 작업 트리가 origin/main보다 13커밋 뒤처져 있어 미커밋 수정 패치가 main에 적용되지 않고, main에 새로 들어온 common_mask가 (b)와 같은 중복 버그를 다시 일으킴
- [low] `setup.py:8` pypi_readme.md가 sdist 매니페스트에 들어가지 않아, 릴리스 트리에 파일이 있어도 sdist→wheel 빌드가 실패함
- [low] `pycapcut/jianying_controller.py:168` jianying_controller의 내보내기 대기 루프가 timeout을 무시하고 무한 busy-loop에 빠지며, CapCut이 아니라 剪映 창만 찾음
- [low] `pycapcut/script_file.py:276` 트랙 조회 실패 시 TrackNotFound/AmbiguousTrack이 아니라 bare NameError가 발생하고, 예외 클래스가 공개 API에서 빠져 있음
- [low] `.flake8:8` .flake8 exclude가 존재하지 않는 pyJianYingDraft/ 경로를 가리켜, 생성된 pycapcut/metadata 파일이 대량 lint 대상이 됨
- [low] `setup.py:5` LICENSE·license 메타데이터·pyproject.toml·py.typed·__version__가 없고, 13커밋이 추가돼도 버전이 0.0.3에 고정됨
- [low] `setup.py:23` imageio(numpy+pillow)가 GIF 길이 계산 한 곳에서만 지연 import되는데 필수 의존성이고, requirements.txt에는 win32 마커가 빠져 있음
- [low] `pycapcut/metadata/tone_effect.py:4` tone_effect.py·speech_to_song.py가 패키지에 포함되지만 HEAD에서는 어디서도 쓰이지 않는 죽은 모듈임
