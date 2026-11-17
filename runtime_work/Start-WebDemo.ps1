param(
    [string]$DemoRoot,
    [int]$Port = 8765,
    [switch]$SmokeTest,
    [string]$SpeakerAssets
)

$ErrorActionPreference = "Stop"

if (!$DemoRoot) {
    $DemoRoot = Join-Path $env:LOCALAPPDATA "VoicegaurdDemo"
    $codexCacheRoot = Join-Path $env:USERPROFILE "AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/VoicegaurdDemo"
    if (!(Test-Path -LiteralPath (Join-Path $DemoRoot "venv/Scripts/python.exe")) -and
        (Test-Path -LiteralPath (Join-Path $codexCacheRoot "venv/Scripts/python.exe"))) {
        $DemoRoot = $codexCacheRoot
    }
}
if (!(Test-Path -LiteralPath $DemoRoot -PathType Container)) {
    throw "Demo assets are missing; see runtime_work/DEMO_SETUP.md."
}
$DemoRoot = (Resolve-Path -LiteralPath $DemoRoot).Path
$python = Join-Path $DemoRoot "venv/Scripts/python.exe"
if (!(Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python environment is missing at $python."
}
if ($Port -lt 1024 -or $Port -gt 65535) { throw "Port must be between 1024 and 65535" }
if ($SpeakerAssets) {
    if (!(Test-Path -LiteralPath $SpeakerAssets -PathType Container)) {
        throw "Speaker asset directory not found: $SpeakerAssets"
    }
    $SpeakerAssets = (Resolve-Path -LiteralPath $SpeakerAssets).Path
}

$oldPythonPath = $env:PYTHONPATH
$oldOffline = $env:HF_HUB_OFFLINE
$oldTransformers = $env:TRANSFORMERS_OFFLINE
try {
    $env:PYTHONPATH = "$PSScriptRoot;$DemoRoot/assets"
    $env:HF_HUB_OFFLINE = "1"
    $env:TRANSFORMERS_OFFLINE = "1"
    $demoArgs = @("-m", "voicegaurd_runtime.web_demo", "--demo-root", $DemoRoot, "--port", "$Port")
    if ($SmokeTest) { $demoArgs += "--smoke-test" }
    if ($SpeakerAssets -and !$SmokeTest) { $demoArgs += @("--speaker-assets", $SpeakerAssets) }
    Write-Host "Voicegaurd V1 local dashboard"
    if (!$SmokeTest) {
        Write-Host "Open http://127.0.0.1:$Port after the models load. Use Ctrl+C to stop."
        Write-Host "This server listens on your laptop only, never on the public internet."
    }
    & $python @demoArgs
    if ($LASTEXITCODE -ne 0) { throw "Voicegaurd web demo exited with code $LASTEXITCODE" }
} finally {
    $env:PYTHONPATH = $oldPythonPath
    $env:HF_HUB_OFFLINE = $oldOffline
    $env:TRANSFORMERS_OFFLINE = $oldTransformers
}
