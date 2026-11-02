<#
.SYNOPSIS
  Re-prepares ALL THREE real GymBeam posts (Phase 7G) from the archived material of this package. Local and free: no OpenAI, Anthropic, fal.ai or any other API call, no API key.

.DESCRIPTION
  Post 1  Creatine Hero V5            approved final PNG copied from the package (hash-checked) + POST.md.  A hero is an AI image; it is NOT regenerated here.
  Post 2  BeastPink carousel (6)      slides 1, 2, 4 copied (hash-checked); slide 3 video RE-ASSEMBLED by slide3_final_v3.py; slide 5 video RE-ASSEMBLED by
                                      slide5_final_v4.py; slide 6 RE-RETOUCHED by slide6_cleanup.py; contact sheet v4 rebuilt; POST.md (caption) copied.
  Post 3  Wafer Reel FINAL V8         whole Reel RE-ASSEMBLED (video + synthesised foley audio) by assemble_reel_v8_candidate.py from the archived Kling clips;
                                      audio track exported; cover B rebuilt by cover_wrapper_fix.py; POST.md (caption) copied.
  Everything goes into a NEW folder with three sub-folders. The package and the workspace deliverables are never modified.
  Each result is compared with the delivered final: SHA-256 first; if the bytes differ, decoded pixels / decoded frames / decoded audio.
  Ends with a clear success message, or reports the real error and returns a non-zero exit code.

  An "offline guard" (tools\offline_guard\sitecustomize.py) is put on PYTHONPATH: any attempt of any step to reach the Internet stops with an error.

.PARAMETER PackageDir
  The extracted "submission" folder of the ZIP (default: the parent of this script's folder).
.PARAMETER Workspace
  The bootstrap workspace (output of tools\bootstrap_workspace.py) in which the Python 3.12 virtual environment (.venv, installed with ".[dev,media]") exists.
.PARAMETER OutDir
  NEW (or empty) output folder. It must not be inside the package.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\work\pkg\submission\tools\REPRODUCE_SVE_TRI_OBJAVE_7F.ps1 -Workspace C:\work\ws -OutDir C:\work\tri_objave
#>
[CmdletBinding()]
param(
    [string]$PackageDir = '',
    [Parameter(Mandatory = $true)][string]$Workspace,
    [Parameter(Mandatory = $true)][string]$OutDir
)
$ErrorActionPreference = 'Stop'
$t0 = Get-Date
$script:Failed = 0

function Say([string]$m, [string]$c = 'Gray') { Write-Host $m -ForegroundColor $c }
function Step([string]$m) { Write-Host ""; Write-Host ("=== " + $m) -ForegroundColor Cyan }
function Die([string]$m) { Write-Host ""; Write-Host ("ERROR: " + $m) -ForegroundColor Red; exit 2 }

try {
    # ---------------------------------------------------------------- 0. inputs, environment, guards
    Step "0. Checking inputs"
    if (-not $PackageDir) { $PackageDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
    $Pkg = (Resolve-Path -LiteralPath $PackageDir).Path
    if (-not (Test-Path -LiteralPath (Join-Path $Pkg 'SUBMISSION_MANIFEST.json'))) { Die "$Pkg is not the extracted 'submission' folder (no SUBMISSION_MANIFEST.json). Use -PackageDir." }
    if (-not (Test-Path -LiteralPath $Workspace)) { Die "Workspace $Workspace does not exist. Create it first: py tools\bootstrap_workspace.py --target $Workspace" }
    $WS = (Resolve-Path -LiteralPath $Workspace).Path
    $Py = Join-Path $WS '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $Py)) { Die "No virtual environment at $Py. Create it: cd $WS; py -3.12 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e `".[dev,media]`"" }
    $ver = (& $Py -c "import sys;print('%d.%d.%d'%sys.version_info[:3])")
    if ($LASTEXITCODE -ne 0) { Die "The virtual environment Python does not start." }
    if (-not $ver.StartsWith('3.12')) { Say "WARNING: venv Python is $ver (tested: 3.12.x; 3.14 also passed the smoke tests)." Yellow }
    & $Py -c "import numpy, PIL, cv2, imageio_ffmpeg" 2>$null
    if ($LASTEXITCODE -ne 0) { Die "The venv lacks the media packages. Run: cd $WS; .\.venv\Scripts\python.exe -m pip install -e `".[dev,media]`"" }
    $ffn = (& $Py -c "import imageio_ffmpeg, os; print(os.path.basename(imageio_ffmpeg.get_ffmpeg_exe()))")
    if ($ffn -notmatch '7\.1') {
        Say "WARNING: the venv has ffmpeg build '$ffn', not the pinned 7.1 (imageio-ffmpeg 0.7.0) with which the delivered files were made." Yellow
        Say "         Decoded video frames will still be compared exactly, but video BYTES and the AAC audio can differ. For byte-identical output:" Yellow
        Say "         cd $WS; .\.venv\Scripts\python.exe -m pip install -e `".[dev,media]`" -c constraints-media-7G.txt" Yellow
    }
    foreach ($rel in 'runs\colla-pink\slide3_video\kling_raw.mp4', 'runs\colla-pink\slide5_video\kling_raw_v2.mp4', 'runs\colla-pink\carousel_final\slide6_odaberi_svoj_okus_FINAL.png',
                     'runs\gymbeam-wafer-reel\video_clips\S03B_kling_raw.mp4', 'runs\gymbeam-wafer-reel\keyframes\S01_raw.png', 'runs\colla-pink\font\Montserrat.ttf',
                     'plans\gymbeam_hr\phase5\slide3_final_v3.py', 'plans\gymbeam_hr\phase5\slide5_final_v4.py', 'plans\gymbeam_hr\phase5\slide6_cleanup.py',
                     'plans\gymbeam_hr\phase6\reel\assemble_reel_v8_candidate.py', 'plans\gymbeam_hr\phase6\reel\cover_wrapper_fix.py') {
        if (-not (Test-Path -LiteralPath (Join-Path $WS $rel))) { Die "Workspace is incomplete, missing $rel. Re-run tools\bootstrap_workspace.py into a NEW folder." }
    }
    $Out = [System.IO.Path]::GetFullPath($OutDir)
    if ($Out.StartsWith($Pkg, [System.StringComparison]::OrdinalIgnoreCase)) { Die "-OutDir must be outside the package folder." }
    if ($Out.StartsWith($WS, [System.StringComparison]::OrdinalIgnoreCase)) { Die "-OutDir must be outside the workspace folder." }
    if ((Test-Path -LiteralPath $Out) -and (Get-ChildItem -LiteralPath $Out -Force | Select-Object -First 1)) { Die "-OutDir $Out is not empty. Choose a NEW folder (the rebuild scripts refuse to overwrite files)." }
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
    $P1 = Join-Path $Out '01_post_creatine_hero'; $P2 = Join-Path $Out '02_post_beastpink_carousel'; $P3 = Join-Path $Out '03_post_gymbeam_wafer_reel'; $WK = Join-Path $Out '_work'
    New-Item -ItemType Directory -Force -Path $P1, $P2, $P3, $WK | Out-Null
    $Helper = Join-Path $Pkg 'tools\repro_helper.py'
    if (-not (Test-Path -LiteralPath $Helper)) { Die "Missing $Helper" }

    # free and offline: no key can be read, no host can be reached
    foreach ($v in 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'FAL_KEY', 'APIFY_TOKEN') { Remove-Item "Env:$v" -ErrorAction SilentlyContinue }
    $env:STUDIO_NO_DOTENV = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'   # never write __pycache__ into the package
    $env:PYTHONPATH = (Join-Path $Pkg 'tools\offline_guard')
    Say "Package   : $Pkg"; Say "Workspace : $WS (Python $ver)"; Say "Output    : $Out"
    $probe = & $Py -c "import socket
try:
    socket.create_connection(('api.openai.com', 443), 3); print('REACHED')
except OSError as e:
    print('BLOCKED' if 'OFFLINE GUARD' in str(e) else 'OTHER: ' + str(e))"
    if ($probe -ne 'BLOCKED') { Die "Offline guard self-test failed (got: $probe)." }
    Say "Offline guard active: a connection attempt to api.openai.com is refused. API keys removed from this process." Green

    function Chk {   # run a helper sub-command; a failed CHECK is counted (all checks run), a crashed helper aborts
        & $Py $Helper @args --out $Out
        if ($LASTEXITCODE -ne 0) { $script:Failed++ }
    }
    function Run([string]$title, [string[]]$a) {   # run one shipped production script; a non-zero exit code is a real error
        Say ("`$ python " + ($a -join ' ')) DarkGray
        & $Py @a
        if ($LASTEXITCODE -ne 0) { throw "$title failed with exit code $LASTEXITCODE" }
    }

    Step "0b. Package integrity (SHA256SUMS.txt)"
    & $Py (Join-Path $Pkg 'tools\verify_hashes.py') --package $Pkg
    if ($LASTEXITCODE -ne 0) { Die "Package hash verification failed: the extracted files differ from SHA256SUMS.txt. Re-extract the ZIP." }

    # ---------------------------------------------------------------- Post 1
    Step "POST 1  Creatine Hero V5  (approved final copied from the package; AI image, not regenerated)"
    Chk copy --name "P1 hero V5 image" --rel posts/post_01_creatine_hero/hero_FINAL_v5_1080x1350.png --dst (Join-Path $P1 'hero_FINAL_v5_1080x1350.png')
    Chk copy --name "P1 POST.md (caption)" --rel posts/post_01_creatine_hero/POST.md --dst (Join-Path $P1 'POST.md')
    Chk media --name "P1 hero V5 is a real 1080x1350 image" --file (Join-Path $P1 'hero_FINAL_v5_1080x1350.png') --size 1080x1350 --ws $WS

    # ---------------------------------------------------------------- Post 2
    Step "POST 2  BeastPink Colla Pink carousel - slides 1, 2, 4 (approved static finals copied)"
    $c = 'posts/post_02_beastpink_carousel'
    Chk copy --name "P2 slide 1 cover" --rel "$c/slide_1_cover_FROZEN_1080x1350.png" --dst (Join-Path $P2 'slide_1_cover_FROZEN_1080x1350.png')
    Chk copy --name "P2 slide 2 sto je unutra" --rel "$c/slide_2_sto_je_unutra_NO_FOOTER_1080x1350.png" --dst (Join-Path $P2 'slide_2_sto_je_unutra_NO_FOOTER_1080x1350.png')
    Chk copy --name "P2 slide 4 kako pripremiti" --rel "$c/slide_4_kako_pripremiti_1080x1350.png" --dst (Join-Path $P2 'slide_4_kako_pripremiti_1080x1350.png')
    Chk copy --name "P2 POST.md (caption)" --rel "$c/POST.md" --dst (Join-Path $P2 'POST.md')

    Step "POST 2  slide 3 video 'PRIPREMA:' - RE-ASSEMBLED by slide3_final_v3.py from the archived Kling clip"
    $S3 = Join-Path $WK 'slide3'
    Run 'slide3_final_v3.py' @((Join-Path $WS 'plans\gymbeam_hr\phase5\slide3_final_v3.py'), '--out', $S3)
    Copy-Item -LiteralPath (Join-Path $S3 'slide3_priprema_FINAL_v3_1080x1350.mp4') -Destination (Join-Path $P2 'slide_3_PRIPREMA_video_v3_1080x1350.mp4')
    Chk compare --name "P2 slide 3 video (rebuilt) = delivered" --gen (Join-Path $P2 'slide_3_PRIPREMA_video_v3_1080x1350.mp4') --ref "$c/slide_3_PRIPREMA_video_v3_1080x1350.mp4" --kind video:1080x1350 --ws $WS
    Chk media --name "P2 slide 3 video: 1080x1350, 24 fps, 121 frames, 5.04 s, no audio" --file (Join-Path $P2 'slide_3_PRIPREMA_video_v3_1080x1350.mp4') --size 1080x1350 --duration 5.04 --frames 121 --ws $WS

    Step "POST 2  slide 5 video 'Napitak za ljepotu' - RE-ASSEMBLED by slide5_final_v4.py (+ per-frame QA)"
    $S5 = Join-Path $WK 'slide5'
    Run 'slide5_final_v4.py' @((Join-Path $WS 'plans\gymbeam_hr\phase5\slide5_final_v4.py'), '--out', $S5, '--qa')
    Copy-Item -LiteralPath (Join-Path $S5 'slide5_napitak_za_ljepotu_FINAL_v4_1080x1350.mp4') -Destination (Join-Path $P2 'slide_5_napitak_za_ljepotu_video_v4_1080x1350.mp4')
    Chk compare --name "P2 slide 5 video (rebuilt) = delivered" --gen (Join-Path $P2 'slide_5_napitak_za_ljepotu_video_v4_1080x1350.mp4') --ref "$c/slide_5_napitak_za_ljepotu_video_v4_1080x1350.mp4" --kind video:1080x1350 --ws $WS
    Chk media --name "P2 slide 5 video: 1080x1350, 24 fps, 121 frames, 5.04 s, no audio" --file (Join-Path $P2 'slide_5_napitak_za_ljepotu_video_v4_1080x1350.mp4') --size 1080x1350 --duration 5.04 --frames 121 --ws $WS

    Step "POST 2  slide 6 'Odaberi svoj okus' - RE-RETOUCHED by slide6_cleanup.py from the frozen original"
    $S6 = Join-Path $WK 'slide6'
    Run 'slide6_cleanup.py' @((Join-Path $WS 'plans\gymbeam_hr\phase5\slide6_cleanup.py'), '--out', $S6)
    Copy-Item -LiteralPath (Join-Path $S6 'slide6_odaberi_svoj_okus_FINAL_v2_1080x1350.png') -Destination (Join-Path $P2 'slide_6_odaberi_svoj_okus_FINAL_v2_1080x1350.png')
    Chk compare --name "P2 slide 6 (re-retouched) = delivered" --gen (Join-Path $P2 'slide_6_odaberi_svoj_okus_FINAL_v2_1080x1350.png') --ref "$c/slide_6_odaberi_svoj_okus_FINAL_v2_1080x1350.png" --kind png --ws $WS
    Chk media --name "P2 slide 6 is a real 1080x1350 image" --file (Join-Path $P2 'slide_6_odaberi_svoj_okus_FINAL_v2_1080x1350.png') --size 1080x1350 --ws $WS

    Step "POST 2  contact sheet v4 (six panels of the slides produced above)"
    Chk contact --name "P2 contact sheet v4 (rebuilt) = delivered" --dir $P2 --dst (Join-Path $P2 'BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v4.png') --ref "$c/BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v4.png" --ws $WS
    foreach ($f in 'slide_1_cover_FROZEN_1080x1350.png', 'slide_2_sto_je_unutra_NO_FOOTER_1080x1350.png', 'slide_4_kako_pripremiti_1080x1350.png') {
        Chk media --name "P2 $f is a real 1080x1350 image" --file (Join-Path $P2 $f) --size 1080x1350 --ws $WS
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $P2 'qa') | Out-Null
    Copy-Item -LiteralPath (Join-Path $S3 'slide3_v3_QA.json'), (Join-Path $S5 'slide5_v4_QA.json'), (Join-Path $S6 'slide6_cleanup_QA.json') -Destination (Join-Path $P2 'qa')

    # ---------------------------------------------------------------- Post 3
    Step "POST 3  Wafer Reel FINAL V8 - WHOLE REEL RE-ASSEMBLED by assemble_reel_v8_candidate.py (video + audio), takes 1-3 minutes"
    $R = Join-Path $P3 'GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4'
    Chk reel-v8 --name "P3 Reel FINAL V8 (re-assembled with audio) = delivered" --ws $WS --dst $R --wav (Join-Path $P3 'audio\V8_foley_only_mix.wav') --ref posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4
    Chk media --name "P3 Reel: 1080x1920, 24 fps, 212 frames, 8.83 s, WITH AUDIO" --file $R --size 1080x1920 --duration 8.83 --frames 212 --audio --ws $WS
    Chk audio --name "P3 Reel audio track exported" --mp4 $R --m4a (Join-Path $P3 'audio\REEL_FINAL_V8_audio_track.m4a') --wav (Join-Path $P3 'audio\REEL_FINAL_V8_audio_track.wav')

    Step "POST 3  cover B (selected) - rebuilt by cover_wrapper_fix.py"
    Chk cover-b --name "P3 cover B (rebuilt) = delivered" --ws $WS --dst (Join-Path $P3 'GYMBEAM_WAFER_REEL_SELECTED_COVER_B_1080x1920.png') --ref posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_REEL_SELECTED_COVER_B_1080x1920.png
    Chk media --name "P3 cover B is a real 1080x1920 image" --file (Join-Path $P3 'GYMBEAM_WAFER_REEL_SELECTED_COVER_B_1080x1920.png') --size 1080x1920 --ws $WS
    Chk copy --name "P3 cover B 4x5 grid preview" --rel posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_REEL_SELECTED_COVER_B_4x5_grid_preview_1080x1350.png --dst (Join-Path $P3 'GYMBEAM_WAFER_REEL_SELECTED_COVER_B_4x5_grid_preview_1080x1350.png')
    Chk copy --name "P3 POST.md (caption)" --rel posts/post_03_gymbeam_wafer_reel/POST.md --dst (Join-Path $P3 'POST.md')

    # ---------------------------------------------------------------- report
    Step "REPORT"
    & $Py $Helper summary --out $Out
    $sumExit = $LASTEXITCODE
    $secs = [int]((Get-Date) - $t0).TotalSeconds
    Write-Host ""
    if ($sumExit -eq 0 -and $script:Failed -eq 0) {
        Write-Host "SUCCESS: all three posts are prepared in $Out  ($secs s)" -ForegroundColor Green
        Write-Host "  01_post_creatine_hero            hero V5 (stored approved final, hash-verified) + POST.md" -ForegroundColor Green
        Write-Host "  02_post_beastpink_carousel       6 slides (slides 3, 5, 6 re-built locally) + contact sheet v4 + POST.md" -ForegroundColor Green
        Write-Host "  03_post_gymbeam_wafer_reel       Reel FINAL V8 re-assembled WITH AUDIO + audio files + cover B + POST.md" -ForegroundColor Green
        Write-Host "  Report: $Out\REPRODUCE_REPORT.txt   (no API call was made; the originals in the package were not touched)" -ForegroundColor Green
        exit 0
    }
    Write-Host "FAILED: $script:Failed check(s) did not pass. See $Out\REPRODUCE_REPORT.txt" -ForegroundColor Red
    exit 1
}
catch {
    Write-Host ""
    Write-Host ("ERROR: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkRed
    exit 3
}
