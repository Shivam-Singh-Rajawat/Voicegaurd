# Voicegaurd — Voice Evidence Lab

Voicegaurd V1 is an **offline-first Windows audio security research demo**:
record from a microphone or analyze a local file, inspect synthetic-speech
(LA) and replay (PA) evidence, and optionally compare a voice against an
authorized speaker reference (ECAPA). It uses pinned existing checkpoints
and preserves their uncalibrated scores.

**Important:** A raw detector score is not a probability that audio is human,
synthetic or replayed. The joint and voice-origin verdicts remain **Uncertain**
on arbitrary microphone and file inputs. Version 1 is a functioning
demonstration, not production identity verification.

## Start the browser dashboard (Windows)

From the project root in PowerShell with a staged VoicegaurdDemo environment:

~~~powershell
.\runtime_work\Start-WebDemo.ps1
~~~

Open **http://127.0.0.1:8765** on the same computer after both pinned
models load. Select an audio file or record approximately 12 seconds from
your microphone, enable optional window scans, review results and export JSON.
The service binds only to 127.0.0.1 and deletes temporary uploads.

For the real-checkpoint sine-wave smoke test without starting a server:

~~~powershell
.\runtime_work\Start-WebDemo.ps1 -SmokeTest
~~~

For optional speaker enrollment, supply actual authorized ECAPA model assets:

~~~powershell
.\runtime_work\Start-WebDemo.ps1 -SpeakerAssets "C:\path\to\speaker_assets"
~~~

See [the full browser demo instructions](runtime_work/WEB_DEMO.md)
for requirements, privacy boundaries, model hash validation, optional
speaker comparison and troubleshooting. Model assets and licensed datasets
are not bundled with this GitHub repository.

## Existing PowerShell CLI

~~~powershell
.\runtime_work\Start-MicrophoneDemo.ps1 -ScanRecording
.\runtime_work\Start-MicrophoneDemo.ps1 -PickAudio -ScanFile -ScanReplay -OutputJson .\voicegaurd-evidence.json
~~~

The CLI and browser both use the same pinned LA/PA model adapters. The
browser has a 16 MiB upload limit; the runtime decodes recordings up to
120 seconds, and detectors require at least 4.0375 seconds of audio.
Window scans use complete windows and do not repeat-pad short clips.

## Development and validation

Run the local regression suite from the repository root:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "runtime_work")
py -3.14 -m pytest -q runtime_work/tests
~~~

Run the live local HTTP smoke test only after starting the browser server:

~~~powershell
$demoRoot = Join-Path $env:LOCALAPPDATA "VoicegaurdDemo"
$python = Join-Path $demoRoot "venv/Scripts/python.exe"
& $python .\runtime_work\smoke_web_http.py
~~~

If the dedicated environment lives in the Windows Codex app cache, supply
that existing Python executable instead. The test uses generated tone
audio, not personal recordings, and reports uncalibrated evidence only.

The [model validation report](model_work/MODEL_VALIDATION.md) records
reproducible independent benchmarks, checkpoint provenance and the two
remaining scientific gates: realistic cross-session speaker robustness and
calibrated multi-evidence security decisions. The model research record
currently remains **7 of 9 gates verified**. See also the
[aligned trial collection protocol](model_work/RECORDED_AUDIO_JOINT_PROTOCOL.md)
and the [ungated dataset review](model_work/ALTERNATIVE_DATASETS_20261117.md).
The original HPC scripts under model_work require the authorized cluster
or adaptation to another research system. Do not deploy the local API
to the public internet without a separate security and model validation review.
