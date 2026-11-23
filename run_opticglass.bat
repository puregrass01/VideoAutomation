@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
set "PYTHONUTF8=1"
cd /d "%~dp0"

if not "%~1"=="" goto :CLI_ARG

:: 인자 없이 더블클릭 실행 시 GUI 메뉴(opticglass_gui.py)를 바로 띄웁니다.
start "" pyw "%~dp0opticglass_gui.py"
if errorlevel 1 (
    py "%~dp0opticglass_gui.py"
)
exit /b 0

:MENU
echo.
echo ============================================================================
echo   OpticGlass (옵틱글래스) 유튜브 영상/썸네일 자동화 런처 (CLI 모드)
echo ============================================================================
echo   [1] 새 PC 초기 세팅 (폰트 설치 + pyCapCut 설치 + 세션 복원 + 검증)
echo   [2] 템플릿 및 전 차종 시나리오 무결성 검증 (check_templates + check_text_outputs)
echo   [3] 전 차종 통합 파이프라인 일괄 실행 (cybertruck, santafe, bmwx5, sealion7)
echo   [4] 영상 리빌드 없이 썸네일만 즉시 재생성 (santafe --skip-video-rebuild)
echo   --------------------------------------------------------------------------
echo   [5] 차종 하나 실행 (슬러그 입력, 차종 폴더 선택은 GUI의 Drive 차종 폴더)
echo   [0] 1 -^> 2 -^> 3 전체 순차 실행 (3이 썸네일까지 만듦)
echo   [G] GUI 창 열기 (opticglass_gui.py)
echo   [Q] 종료
echo ============================================================================
set /p CHOICE="원하는 작업 번호를 입력하세요 (0~5, G, Q): "

if /i "%CHOICE%"=="1" goto :STEP1
if /i "%CHOICE%"=="2" goto :STEP2
if /i "%CHOICE%"=="3" goto :STEP3
if /i "%CHOICE%"=="4" goto :STEP4
if /i "%CHOICE%"=="5" goto :ONE_CAR
if /i "%CHOICE%"=="0" goto :RUN_ALL
if /i "%CHOICE%"=="G" (
    start "" pyw "%~dp0opticglass_gui.py"
    exit /b 0
)
if /i "%CHOICE%"=="Q" exit /b 0
goto :MENU

:CLI_ARG
if /i "%~1"=="cli" goto :MENU
if /i "%~1"=="gui" (
    start "" pyw "%~dp0opticglass_gui.py"
    exit /b 0
)
if /i "%~1"=="1" goto :STEP1_ONCE
if /i "%~1"=="setup" goto :STEP1_ONCE
if /i "%~1"=="2" goto :STEP2_ONCE
if /i "%~1"=="check" goto :STEP2_ONCE
if /i "%~1"=="3" goto :STEP3_ONCE
if /i "%~1"=="all" goto :RUN_ALL_ONCE
if /i "%~1"=="4" goto :STEP4_ONCE
if /i "%~1"=="thumb" goto :STEP4_ONCE
:: an unknown argument (a typo, help) shows the menu instead of installing and building everything
goto :MENU

:STEP1
call :STEP1_ONCE
pause
goto :MENU

:STEP1_ONCE
echo.
echo [1] 새 PC 초기 세팅 실행 중...
call setup.bat /nopause
exit /b %errorlevel%

:STEP2
call :STEP2_ONCE
pause
goto :MENU

:STEP2_ONCE
echo.
echo [2] 템플릿 및 전 차종 시나리오 무결성 검증 실행 중...
py video-automation/work/check_templates.py
if errorlevel 1 exit /b 1
py video-automation/work/check_text_outputs.py
if errorlevel 1 echo [주의] check_text_outputs.py가 차이를 보고했습니다. 빌드가 초안을 다시 만듭니다.
exit /b 0

:STEP3
call :STEP3_ONCE
pause
goto :MENU

:STEP3_ONCE
echo.
echo [3] 차종별 통합 파이프라인 실행 중 (cybertruck, santafe, bmwx5, sealion7)...
set "FAILED="
for %%C in (cybertruck santafe bmwx5 sealion7) do (
    py video-automation/work/gdrive_pipeline.py --vehicle %%C
    if errorlevel 1 set "FAILED=!FAILED! %%C"
)
if defined FAILED (
    echo [오류] 실패한 차:!FAILED!
    exit /b 1
)
exit /b 0

:STEP4
call :STEP4_ONCE
pause
goto :MENU

:STEP4_ONCE
echo.
echo [4] 영상 리빌드 없이 썸네일만 즉시 재생성 (santafe)...
py video-automation/work/gdrive_pipeline.py --vehicle santafe --skip-video-rebuild
exit /b %errorlevel%

:ONE_CAR
echo.
set "SLUG="
set /p SLUG="차종 슬러그 (예: santafe): "
if "%SLUG%"=="" goto :MENU
py video-automation/work/gdrive_pipeline.py --vehicle %SLUG%
pause
goto :MENU

:RUN_ALL
call :RUN_ALL_ONCE
pause
goto :MENU

:RUN_ALL_ONCE
call :STEP1_ONCE
if errorlevel 1 exit /b 1
call :STEP2_ONCE
if errorlevel 1 exit /b 1
call :STEP3_ONCE
exit /b %errorlevel%
