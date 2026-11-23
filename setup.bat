<# : batch header (cmd runs these lines; PowerShell reads them as a comment). Keep it ASCII and the file BOM-less.
@echo off
chcp 65001 >nul
set "SETUP_ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ([IO.File]::ReadAllText('%~f0', [Text.Encoding]::UTF8))"
set "RC=%errorlevel%"
if /i not "%~1"=="/nopause" pause
exit /b %RC%
#>
# =============================================================================
# OpticGlass (옵틱글래스) 유튜브 자동화 워크플로우 — 타 PC 설치·부트스트랩 (setup.bat 하나로 실행)
# 실행 방법: setup.bat 더블클릭 (다른 스크립트·GUI에서 부를 때는 setup.bat /nopause)
# 위 batch 머리말이 이 파일 전체를 PowerShell로 실행한다. 아래는 PowerShell 코드.
# 없는 프로그램(Python, ffmpeg, CapCut, agy, Node.js)은 winget으로 설치하고, 폰트·패키지·세션을 복원한다.
# 필요한 프로그램·버전·로그인 전체 목록: DISTRIBUTION.md
# 필수 프로그램이 없으면 무엇이 없는지 알려 주고 종료 코드 1로 끝난다 (run_all_pipeline.bat이 여기서 멈춤).
# =============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"
$RepoRoot = $env:SETUP_ROOT.TrimEnd('\')
Set-Location $RepoRoot
$env:PYTHONUTF8 = "1"
$Missing = New-Object System.Collections.Generic.List[string]   # 필수: 없으면 롱폼 빌드가 멈춤
$Warnings = New-Object System.Collections.Generic.List[string]  # 선택: 해당 기능만 안 됨

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [OpticGlass Portable Setup] 다른 PC 환경 자동 복원 시작" -ForegroundColor Cyan
Write-Host " Workspace Root: $RepoRoot" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. 없는 프로그램 설치 (winget). 설치됐는지는 2단계가 다시 확인한다
Write-Host "`n[1/7] 없는 프로그램 설치 중 (winget: Python, ffmpeg, CapCut, agy, Node.js)..." -ForegroundColor Yellow
$PyUsable = $false
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -c "import sys, tkinter; sys.exit(sys.version_info < (3, 12))" 2>$null
    $PyUsable = $LASTEXITCODE -eq 0
}
$AgyFound = (Get-Command agy -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $env:USERPROFILE ".gemini\bin\agy.exe"))
$Need = [ordered]@{
    "Python.Python.3.14"    = -not $PyUsable                                       # py/pyw 런처, tcl/tk 포함
    "Gyan.FFmpeg"           = -not (Get-Command ffmpeg -ErrorAction SilentlyContinue)  # full build: libx264, libmp3lame
    "ByteDance.CapCut"      = -not (Test-Path (Join-Path $env:LOCALAPPDATA "CapCut\Apps"))
    "Google.AntigravityCLI" = -not $AgyFound                                       # agy
    "OpenJS.NodeJS.LTS"     = -not (Get-Command node -ErrorAction SilentlyContinue)    # 파이프라인은 안 씀 (Claude Code 등 도구용)
}
$Todo = @($Need.Keys | Where-Object { $Need[$_] })
if (-not $Todo) {
    Write-Host "  = 모두 설치되어 있음" -ForegroundColor Gray
} elseif (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "  - winget이 없어 자동 설치를 건너뜀: Microsoft Store의 '앱 설치 관리자'를 설치하거나 DISTRIBUTION.md 1장대로 직접 설치 ($($Todo -join ', '))" -ForegroundColor DarkYellow
} else {
    foreach ($id in $Todo) {
        Write-Host "  + 설치: $id" -ForegroundColor Green
        & winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { Write-Host "  - $id 설치 실패 (종료 코드 $LASTEXITCODE)" -ForegroundColor DarkYellow }
    }
    # 방금 설치한 프로그램이 이 창에서 바로 보이도록 PATH를 다시 읽음
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

# 2. 필수 프로그램 확인
Write-Host "`n[2/7] 필수 프로그램 확인 중 (Python, ffmpeg, CapCut, agy, gdrive)..." -ForegroundColor Yellow
$PyOk = $false
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pyv = & py -c "import sys, tkinter; print('%d.%d.%d' % sys.version_info[:3]); sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $PyOk = $true
        Write-Host "  = Python $pyv (tkinter 포함)" -ForegroundColor Gray
    } else {
        $Missing.Add("Python 3.12 이상 + tcl/tk (지금: $pyv, requirements.txt의 numpy 2.5가 3.12를 요구). python.org 설치 프로그램에서 'tcl/tk and IDLE'을 켜고 설치")
    }
} else {
    $Missing.Add("Python (py 런처). python.org에서 64-bit 3.14를 설치 (py launcher, tcl/tk 포함)")
}

$Ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($Ffmpeg) {
    $encoders = (& ffmpeg -hide_banner -encoders 2>$null) -join "`n"
    $lacks = @("libx264", "libmp3lame") | Where-Object { $encoders -notmatch $_ }
    if ($lacks) {
        $Missing.Add("ffmpeg에 인코더가 없음: $($lacks -join ', '). gyan.dev full build 권장 (winget install Gyan.FFmpeg)")
    } else {
        Write-Host "  = ffmpeg: $((& ffmpeg -version 2>$null | Select-Object -First 1))" -ForegroundColor Gray
    }
} else {
    $Missing.Add("ffmpeg (PATH). winget install Gyan.FFmpeg 후 새 터미널에서 다시 실행")
}

$CapCutApps = Join-Path $env:LOCALAPPDATA "CapCut\Apps"
if (-not (Test-Path $CapCutApps)) {
    $Missing.Add("CapCut 데스크톱 (설치 후 한 번 실행하고 로그인)")
}

$GdriveCmd = Join-Path $RepoRoot ".agents\skills\gdrive\scripts\gdrive.cmd"
if (-not (Test-Path $GdriveCmd)) {
    $Missing.Add("gdrive 런처 ($GdriveCmd): 저장소가 온전히 복사되지 않음")
}

# 3. 번들 폰트 설치 (Paperlogy 7 Bold / 9 Black, NotoSansKR Bold Static 등)
Write-Host "`n[3/7] 번들 폰트 설치 확인 중 (video-automation/assets/fonts/)..." -ForegroundColor Yellow
$FontsSrc = Join-Path $RepoRoot "video-automation\assets\fonts"
$UserFontsDir = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts"
$RegPath = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts"
if (-not (Test-Path $UserFontsDir)) {
    New-Item -ItemType Directory -Path $UserFontsDir -Force | Out-Null
}
if (Test-Path $FontsSrc) {
    Get-ChildItem -Path $FontsSrc -Filter "*.ttf" | ForEach-Object {
        $dstFont = Join-Path $UserFontsDir $_.Name
        if (-not (Test-Path $dstFont)) {
            Copy-Item -LiteralPath $_.FullName -Destination $dstFont -Force
            New-ItemProperty -Path $RegPath -Name "$($_.BaseName) (TrueType)" -Value $dstFont -PropertyType String -Force | Out-Null
            Write-Host "  + 설치 완료: $($_.Name)" -ForegroundColor Green
        } else {
            Write-Host "  = 이미 존재함: $($_.Name)" -ForegroundColor Gray
        }
    }
} else {
    $Missing.Add("번들 폰트 폴더 ($FontsSrc): 저장소가 온전히 복사되지 않음")
}

# 4. Python 패키지: requirements.txt(원본 PC에서 확인한 버전 고정) + 로컬 패치 pyCapCut editable
Write-Host "`n[4/7] Python 패키지 설치 중 (requirements.txt + pyCapCut editable)..." -ForegroundColor Yellow
$PyCapCutDir = Join-Path $RepoRoot "pyCapCut"
if (-not (Test-Path (Join-Path $PyCapCutDir "setup.py"))) {
    $Missing.Add("pyCapCut 패치본 ($PyCapCutDir). git clone으로는 빈 폴더가 오므로 배포 zip이나 원본 PC 폴더를 복사")
} elseif ($PyOk) {
    & py -m pip install -r (Join-Path $RepoRoot "requirements.txt") -e $PyCapCutDir --quiet --disable-pip-version-check
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  + requirements.txt 버전과 pyCapCut(editable) 설치 완료" -ForegroundColor Green
    } else {
        $Missing.Add("pip install 실패 (인터넷 연결, Python 버전 확인). 위 pip 오류를 보세요")
    }
}

if ($PyOk) {
    # CapCut 버전 게이트와 agy 위치는 파이프라인 코드가 보는 그대로 확인
    $probe = & py -c @"
import sys; sys.path.insert(0, r'$RepoRoot\video-automation\work')
import preflight_check, llm
r = preflight_check.run_preflight()
print('capcut', r['status'], r['highest_version'], r['verified_max_version'])
print('agy', 'ok' if llm._agy().exists() else 'missing', llm._agy())
"@ 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0 -or -not ($probe -match "^agy ")) {
        $Warnings.Add("CapCut/agy 확인 실패 (llm_config.json 형식 등): $(($probe | Select-Object -Last 3) -join ' / ')")
    }
    foreach ($line in $probe) {
        $f = $line -split " ", $(if ($line -like "agy *") { 3 } else { 4 })  # the agy path may hold spaces
        if ($f[0] -eq "capcut" -and (Test-Path $CapCutApps)) {
            if ($f[1] -eq "ok") {
                Write-Host "  = CapCut $($f[2]) (자동 배포 가능, 확인된 최고 버전 $($f[3]))" -ForegroundColor Gray
            } elseif ($f[1] -eq "blocked_v10") {
                $Warnings.Add("CapCut $($f[2]) (10.x)는 외부 초안 쓰기가 차단됨: 9.7.x로 되돌리거나 capcut_stage의 초안을 수동으로 사용")
            } else {
                $Warnings.Add("CapCut $($f[2])가 확인된 버전 $($f[3])보다 새것 (status=$($f[1])): 초안이 capcut_stage에만 남음. 스모크 테스트 후 preflight_check.py의 VERIFIED_MAX_VERSION을 올리거나 수동 배포")
            }
        }
        if ($f[0] -eq "agy") {
            if ($f[1] -eq "ok") {
                Write-Host "  = agy: $($f[2])" -ForegroundColor Gray
            } else {
                $Warnings.Add("agy 없음 ($($f[2])): 썸네일 사진 AI 검수·AI 배경·대사 초안·GUI 영상 수정이 안 됨. Antigravity 설치·로그인, 다른 곳이면 llm_config.json의 agy_path에 경로")
            }
        }
    }
}

# 5. Antigravity 세션 대화 내역(Brain) 및 Hermes 스킬 복원
Write-Host "`n[5/7] 이전 세션 대화 내역(Archive) 및 스킬 복원 중..." -ForegroundColor Yellow
$BrainArchive = Join-Path $RepoRoot "archive\sessions\antigravity_brain"
$TargetBrainRoot = Join-Path $env:USERPROFILE ".gemini\antigravity\brain"
if (Test-Path $BrainArchive) {
    New-Item -ItemType Directory -Path $TargetBrainRoot -Force | Out-Null
    $sessions = Get-ChildItem -Path $BrainArchive -Directory
    $restoredCount = 0
    $sessions | ForEach-Object {
        $dstSession = Join-Path $TargetBrainRoot $_.Name
        if (-not (Test-Path $dstSession)) {
            Copy-Item -LiteralPath $_.FullName -Destination $dstSession -Recurse -Force
            $restoredCount++
        }
    }
    Write-Host "  + Antigravity 대화 세션 확인 완료 (신규 복원: ${restoredCount}개, 전체 아카이브: $($sessions.Count)개)" -ForegroundColor Green
}

$HermesSkillSrc = Join-Path $RepoRoot ".agents\skills\video-editing-automation"
$HermesSkillDst = Join-Path $env:LOCALAPPDATA "hermes\skills\media\video-editing-automation"
if ((Test-Path $HermesSkillSrc) -and (Test-Path (Join-Path $env:LOCALAPPDATA "hermes"))) {
    New-Item -ItemType Directory -Path $HermesSkillDst -Force | Out-Null
    Copy-Item -Path (Join-Path $HermesSkillSrc "*") -Destination $HermesSkillDst -Recurse -Force  # 내용만 복사 (다시 돌려도 폴더가 겹치지 않음)
    Write-Host "  + Hermes video-editing-automation 스킬 동기화 완료" -ForegroundColor Green
}

$MigratedPluginSrc = Join-Path $RepoRoot ".agents\plugins\migrated-settings"
$MigratedPluginDst = Join-Path $env:USERPROFILE ".gemini\config\plugins\migrated-settings"
if (Test-Path $MigratedPluginSrc) {
    New-Item -ItemType Directory -Path $MigratedPluginDst -Force | Out-Null
    Copy-Item -Path (Join-Path $MigratedPluginSrc "*") -Destination $MigratedPluginDst -Recurse -Force
    Write-Host "  + Antigravity migrated-settings 플러그인 동기화 완료" -ForegroundColor Green
}

# 6. 템플릿/텍스트 검증 (ffmpeg와 패키지가 있어야 돈다)
Write-Host "`n[6/7] 템플릿 및 텍스트 검증 실행 중..." -ForegroundColor Yellow
if ($PyOk -and $Ffmpeg) {
    & py "video-automation\work\check_templates.py"
    if ($LASTEXITCODE -ne 0) { $Missing.Add("check_templates.py 실패 (위 출력 참고)") }
    & py "video-automation\work\check_text_outputs.py"
    if ($LASTEXITCODE -ne 0) { $Warnings.Add("check_text_outputs.py가 차이를 보고함: 해당 차를 다시 빌드하면 맞춰짐") }
} else {
    Write-Host "  - Python/ffmpeg가 없어 검증을 건너뜀" -ForegroundColor DarkYellow
}

# 7. 계정 로그인 안내 (zip으로 옮길 수 없음)
Write-Host "`n[7/7] 이 PC에서 직접 해야 하는 로그인" -ForegroundColor Yellow
Write-Host "  * Google Drive: & '$GdriveCmd' auth login  (Drive 폴더 0.옵틱 광각이 보이는 계정)" -ForegroundColor Cyan
Write-Host "  * Antigravity(agy) 로그인, CapCut 로그인 후 한 번 실행, Claude 커넥터 재연결 (HANDOFF.md)" -ForegroundColor Cyan

Write-Host "`n============================================================" -ForegroundColor Cyan
foreach ($w in $Warnings) { Write-Host " [주의] $w" -ForegroundColor DarkYellow }
if ($Missing.Count -gt 0) {
    foreach ($m in $Missing) { Write-Host " [없음] $m" -ForegroundColor Red }
    Write-Host " 필수 항목 $($Missing.Count)개를 설치한 뒤 이 스크립트를 다시 실행하세요 (DISTRIBUTION.md)." -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Cyan
    exit 1
}
Write-Host " [완료] 필수 프로그램과 패키지가 모두 준비되었습니다. run_opticglass.bat 또는 opticglass_gui.exe로 시작하세요." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
exit 0
