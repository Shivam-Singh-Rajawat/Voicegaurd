param(
    [switch]$SmokeTest, [string]$AudioPath, [switch]$PickAudio, [string]$SaveRecording,
    [string]$SpeakerAssets, [string[]]$ReferenceAudio, [switch]$ScanFile,
    [string]$DemoRoot, [switch]$ScanRecording, [switch]$ScanReplay, [string]$OutputJson
)

$ErrorActionPreference = "Stop"
if ($ScanFile -and !($AudioPath -or $PickAudio)) {
    throw "ScanFile requires AudioPath or PickAudio"
}
if ($ScanRecording -and ($AudioPath -or $PickAudio -or $SmokeTest)) {
    throw "ScanRecording requires microphone mode"
}
if ($ScanReplay -and !($ScanFile -or $ScanRecording)) {
    throw "ScanReplay requires ScanFile or ScanRecording"
}
if ($OutputJson) {
    $reportPath = [System.IO.Path]::GetFullPath($OutputJson)
    if ([System.IO.Path]::GetExtension($reportPath) -ine ".json") {
        throw "OutputJson must have a .json extension"
    }
    if (!(Test-Path -LiteralPath ([System.IO.Path]::GetDirectoryName($reportPath)) -PathType Container) -or
        (Test-Path -LiteralPath $reportPath)) {
        throw "Choose a new JSON path in an existing folder"
    }
    $OutputJson = $reportPath
}
if ([bool]$SpeakerAssets -ne [bool]$ReferenceAudio) {
    throw "Provide SpeakerAssets and authorized ReferenceAudio together"
}
if ($SpeakerAssets) {
    if (!(Test-Path -LiteralPath $SpeakerAssets -PathType Container)) {
        throw "Speaker asset directory not found: $SpeakerAssets"
    }
    $SpeakerAssets = (Resolve-Path -LiteralPath $SpeakerAssets).Path
    $ReferenceAudio = foreach ($reference in $ReferenceAudio) {
        if (!(Test-Path -LiteralPath $reference -PathType Leaf)) {
            throw "Reference audio not found: $reference"
        }
        (Resolve-Path -LiteralPath $reference).Path
    }
}
if ($SaveRecording -and ($SmokeTest -or $AudioPath -or $PickAudio)) {
    throw "SaveRecording is only available in microphone mode"
}
if (($SmokeTest -and ($AudioPath -or $PickAudio)) -or ($AudioPath -and $PickAudio)) {
    throw "Choose one input: SmokeTest, AudioPath, or PickAudio"
}
if ($PickAudio) {
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    try {
        $picker.Title = "Voicegaurd - choose audio (minimum 4.0375 seconds; 8+ seconds of clear speech recommended)"
        $picker.Filter = "Audio files (*.wav;*.flac;*.ogg;*.mp3)|*.wav;*.flac;*.ogg;*.mp3"
        if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { return }
        $AudioPath = $picker.FileName
    } finally {
        $picker.Dispose()
    }
}
if ($AudioPath) {
    if (!(Test-Path -LiteralPath $AudioPath -PathType Leaf)) { throw "Audio file not found: $AudioPath" }
    $AudioPath = (Resolve-Path -LiteralPath $AudioPath).Path
}
if (!$DemoRoot) {
    $DemoRoot = Join-Path $env:LOCALAPPDATA "VoicegaurdDemo"
    $codexCacheRoot = Join-Path $env:USERPROFILE "AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/VoicegaurdDemo"
    if (!(Test-Path -LiteralPath (Join-Path $DemoRoot "venv/Scripts/python.exe")) -and
        (Test-Path -LiteralPath (Join-Path $codexCacheRoot "venv/Scripts/python.exe"))) {
        $DemoRoot = $codexCacheRoot
    }
}
$python = Join-Path $demoRoot "venv/Scripts/python.exe"
if (!(Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Voicegaurd Python environment missing at $python. See runtime_work/DEMO_SETUP.md."
}
$demoRoot = (Resolve-Path -LiteralPath $DemoRoot).Path
$python = Join-Path $demoRoot "venv/Scripts/python.exe"
$synthetic = Join-Path $demoRoot "la/best.pt"
$replay = Join-Path $demoRoot "pa/best.pt"
$checkpointHashes = @{
    $synthetic = "5600846905b143a476ec83cd805b44536fae166102fe015ea3ed2b84e026a57b"
    $replay = "21c4f85791204ff215dc88a3944bb53e056c614bb3f675994f33397268ba7b09"
    (Join-Path $demoRoot "assets/wavlm-base-plus/config.json") = "fea6df1c2700a3954fc07e70588aecc9055eeb28db2ff57151a2db0d19180ed4"
    (Join-Path $demoRoot "assets/wavlm-base-plus/model.safetensors") = "1a252e49ddf1897f1f07f0d73c2a7cca86a05b0ad8d0189a6edc0ad3e55f1ae6"
}
foreach ($path in $checkpointHashes.Keys) {
    if (!(Test-Path -LiteralPath $path -PathType Leaf) -or
        (Get-FileHash -LiteralPath $path).Hash -ne $checkpointHashes[$path]) {
        throw "Checkpoint transfer is incomplete or failed verification at $path"
    }
}
$oldPythonPath = $env:PYTHONPATH
$oldOffline = $env:HF_HUB_OFFLINE
try {
    $env:PYTHONPATH = "$PSScriptRoot;$demoRoot/assets"
    $env:HF_HUB_OFFLINE = "1"
    $demoArgs = @("--synthetic", $synthetic, "--replay", $replay,
        "--synthetic-research-cutoff", "0.0061066979542373995")
    if ($SmokeTest) { $demoArgs += "--smoke-test" }
    if ($AudioPath) { $demoArgs += @("--audio", $AudioPath) }
    if ($ScanFile) { $demoArgs += "--scan-file" }
    if ($ScanRecording) { $demoArgs += "--scan-recording" }
    if ($ScanReplay) { $demoArgs += "--scan-replay" }
    if ($OutputJson) { $demoArgs += @("--output-json", $OutputJson) }
    if ($SaveRecording) { $demoArgs += @("--save-recording", $SaveRecording) }
    if ($SpeakerAssets) {
        $demoArgs += @("--speaker-assets", $SpeakerAssets)
        foreach ($reference in $ReferenceAudio) { $demoArgs += @("--reference", $reference) }
    }
    & $python -m voicegaurd_runtime.microphone_demo @demoArgs
    if ($LASTEXITCODE) { throw "Voicegaurd exited with code $LASTEXITCODE" }
} finally {
    $env:PYTHONPATH = $oldPythonPath
    $env:HF_HUB_OFFLINE = $oldOffline
}
