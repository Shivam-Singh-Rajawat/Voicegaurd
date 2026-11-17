# Voicegaurd Version 1 for Windows

Run these commands from the project folder in PowerShell. The launcher
uses the Python environment and pinned LA, PA and WavLM files staged in
the VoicegaurdDemo cache. It checks the detector and backbone digests
before loading and runs offline. See [runtime progress](PROGRESS.md) for
the cache layout and tested environment and the [model handoff](../model_work/MODEL_VALIDATION.md)
for checkpoint provenance and HPC reproduction.

```powershell
# Record a 12-second microphone clip. Speak continuously for at least 8 seconds.
.\runtime_work\Start-MicrophoneDemo.ps1

# Select an existing WAV, FLAC, OGG or MP3 (processed locally)
.\runtime_work\Start-MicrophoneDemo.ps1 -PickAudio
```

The detector needs one complete 4.0375-second window after conversion to
16 kHz mono. Use a recording with at least 8 seconds of clear speech to
leave room for pauses and silence at the ends. Short recordings return
`uncertain` with a duration message. The duration check measures the audio
file, and does not measure how much of it is speech.

Use `-AudioPath` with a file path to bypass the picker. Use
`-SaveRecording` with a new WAV path to keep the microphone recording.
Add `-ScanFile` to either file input mode to see raw synthetic-voice scores
and timestamps across the recording. This adds a final overlapping window
when needed to cover the end. Silent windows carry a null score, and
short recordings can have no full windows. The scan supplies diagnostic
evidence while the verdict remains uncertain. The scan uses complete windows
from the existing checkpoint and does not combine their scores. The normal
LA result uses one centered window. LA and PA scores are raw model scores.
Speaker verification, when enabled, reports cosine similarity separately.
For a live capture, use `-ScanRecording` to see the same timestamped scores
under `synthetic_microphone_scan.windows`. Record each comparison clip
separately, and use the same utterance and playback setup when comparing
an AI clip with and without music.

## Export a Version 1 evidence report

To save the existing detector evidence as JSON, use `-OutputJson` with a new
`.json` path. It will not overwrite an existing file and does **not** save
the waveform. Use `-SaveRecording` separately when you have permission
to retain microphone audio. Files may contain local checkpoint paths and
speaker comparison scores; keep them private when they contain sensitive data.

```powershell
.\runtime_work\Start-MicrophoneDemo.ps1 -PickAudio -ScanFile -ScanReplay -OutputJson .\voicegaurd-evidence.json
.\runtime_work\Start-MicrophoneDemo.ps1 -ScanRecording -ScanReplay -OutputJson .\voicegaurd-microphone-evidence.json
```

`-ScanReplay` adds `replay_file_scan.windows` or
`replay_microphone_scan.windows` to the existing synthetic-voice scan.
Each detector uses its own full trained window; no short-window padding
is introduced. Scan windows have timestamps and a raw score or null for
silence. Longer clips require additional inference time. The centered
LA/PA scores and speaker score remain unchanged. **Neither scan is a
calibrated replay or human-versus-AI verdict**. The overall decision
remains `uncertain`.

## Setup on another Windows machine

Use the staged installation if available. For a fresh installation, copy
the authorized assets from a working installation, preserving this layout
under a new directory. The patched project loader resolves the WavLM
files relative to itself.

```text
VoicegaurdDemo/
  la/best.pt
  pa/best.pt
  assets/voicegaurd_v3/
  assets/wavlm-base-plus/config.json
  assets/wavlm-base-plus/model.safetensors
```

Use Windows x64 Python 3.14 and create a fresh environment in that
directory. These dependency versions match the staged runtime. The launcher
verifies the checkpoints and backbone before inference.

```powershell
$demoRoot = Join-Path $env:LOCALAPPDATA 'VoicegaurdDemo'
py -3.14 -m venv "$demoRoot\venv"
$python = Join-Path $demoRoot 'venv\Scripts\python.exe'
& $python -m pip install torch==2.13.0 numpy==2.5.2 scipy==1.18.1 soundfile==0.14.0 sounddevice==0.5.6 transformers==4.57.6
.\runtime_work\Start-MicrophoneDemo.ps1 -DemoRoot $demoRoot -SmokeTest
```

Set `$demoRoot` to the directory holding the copied assets if it differs.
The tone smoke test exercises loading and inference and prints both raw
detector scores. To check the physical microphone, run the launcher
without `-SmokeTest` and check for `input_source: microphone` and a
12-second recording.

## Standalone voice-origin evidence

The frozen LA cutoff is diagnostic for microphone and arbitrary file inputs.
The external benchmarks below use the pinned model and a complete centered
window. Coverage is scored divided by total, and FP and FN count errors
among scored recordings at the frozen cutoff.

| Benchmark | Genuine scored / total | Synthetic scored / total | Coverage | FP | FN |
|---|---:|---:|---:|---:|---:|
| CoSG, PBS 46063 | 636 / 866 | 736 / 931 | 76.35% | 3 / 636 | 615 / 736 |
| J-SpAW LA, PBS 46570 | 1 / 800 | 62 / 1,600 | 2.63% | 1 / 1 | 2 / 62 |

CoSG tests codec-generated synthetic speech and misses most scored attacks
at this cutoff. J-SpAW has only one scored genuine example. The published
demo therefore displays Uncertain for voice origin. Human and AI-generated
verdicts require validation on representative microphone or file inputs.
The open speaker robustness and joint LA/PA/ECAPA gates are research work
outside the Version 1 delivery criteria. SITW remains on hold.

To include speaker evidence, supply the pinned ECAPA asset directory and
authorized enrollment clips from a separate session. The Windows demo
environment uses SpeechBrain 1.1.2. On another installation, use the same
model assets and verified Python environment, and install
`speechbrain==1.1.2` with that environment's `python -m pip`.

```powershell
.\runtime_work\Start-MicrophoneDemo.ps1 -PickAudio -SpeakerAssets .\model_work\speaker_assets -ReferenceAudio 'C:\recordings\enrollment.wav'
```

Replace the enrollment path with an actual file. Omit `-PickAudio` for
microphone input. Multiple reference paths can be passed as a PowerShell
array. Speaker matching uses the frozen research cutoff. The prototype
returns diagnostic scores and an uncertain joint verdict. See the
[joint validation and collection protocol](../model_work/RECORDED_AUDIO_JOINT_PROTOCOL.md)
for the data needed to validate that verdict.

To verify all three models with live microphone input on this Windows
installation, use the previously saved enrollment clip and speak a new
clip when prompted:

```powershell
$reference = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Voicegaurd-20261111-020705.wav'
.\runtime_work\Start-MicrophoneDemo.ps1 -SpeakerAssets .\model_work\speaker_assets -ReferenceAudio $reference
```

Check for `input_source: microphone`, both detector scores, a numeric
speaker similarity, and `decision: uncertain`. This is a live integration
check. Speaker robustness and joint decision accuracy require separate
assessment trials.

Run the existing regression suite from the project root using the staged
environment with `runtime_work` and the staged `assets` directory on
`PYTHONPATH`, then run `python -m pytest -q runtime_work/tests`.

