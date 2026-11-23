@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
set "PYTHONUTF8=1"
cd /d "%~dp0"

echo ============================================================================
echo  [OpticGlass] 전체 자동화 파이프라인 일괄 실행 (1.세팅 -^> 2.검증 -^> 3.빌드·썸네일)
echo ============================================================================

echo.
echo [1/3] 새 PC 초기 세팅 (프로그램 설치 + 폰트 + pyCapCut + 세션 복원 + 검증)
call setup.bat /nopause
if errorlevel 1 (
    echo [오류] 초기 세팅 중 문제가 발생했습니다.
    pause
    exit /b 1
)

echo.
echo [2/3] 템플릿 및 전 차종 시나리오 무결성 검증
py video-automation/work/check_templates.py
if errorlevel 1 (
    echo [오류] check_templates.py 검증 실패
    pause
    exit /b 1
)
py video-automation/work/check_text_outputs.py
if errorlevel 1 (
    echo [주의] check_text_outputs.py가 차이를 보고했습니다. 다음 단계의 빌드가 초안을 다시 만듭니다.
)

echo.
echo [3/3] 차종별 통합 파이프라인 실행 (Google Drive 동기화 -^> 영상 초안 빌드 -^> 1280x720 썸네일 생성)
set "FAILED="
for %%C in (cybertruck santafe bmwx5 sealion7) do (
    py video-automation/work/gdrive_pipeline.py --vehicle %%C
    if errorlevel 1 set "FAILED=!FAILED! %%C"
)

echo.
echo ============================================================================
if defined FAILED (
    echo  [오류] 실패한 차:!FAILED!  위 출력에서 원인을 확인하세요.
    echo ============================================================================
    pause
    exit /b 1
)
echo  [완료] 모든 명령어 실행이 정상적으로 끝났습니다.
echo ============================================================================
pause
