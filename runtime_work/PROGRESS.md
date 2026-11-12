# Pending HPC integration

Prepared a CPU adapter for existing Voicegaurd v3 checkpoints. It preserves
center cropping, repeated short audio, score orientation, and amplitude clipping.
Model outputs are explicitly uncalibrated. Speaker verification is unavailable.

Pending: transfer, tests in the existing HPC environment, and allocated CPU model
inference pilots against saved development scores. Do not claim model validation
from unit tests alone. Existing remote source and checkpoints remain authoritative.

Local verification: 5 adapter unit tests passed with runtime_work on PYTHONPATH.
SSH repeatedly failed before authentication during this session. No adapter files
have been transferred. Remote last verified: recovery 113640/113640 complete,
760889 indexed paths with no missing paths, expanded suite 18 passed.

An active Codex thread heartbeat, continue-voicegaurd-engineering, was created
to resume every 30 minutes. Reconcile actual files and scheduler state on each run.
Do not submit duplicate work. Preserve the existing remote runtime modules.

Latest verified: adapter and tests were transferred with matching hashes. Remote
suite 45980 passed 23 tests. CPU pilot 45981 completed four development samples
across LA/PA; PA score max difference from saved scores was 0.00002926.
Streaming buffer and 6 tests transferred; local adapter/buffer suite 11 passed.
Expanded remote test job 45982 submitted. FastAPI, Uvicorn, SpeechBrain and HTTPX
are absent from the current HPC environment. Next: inspect 45982; create isolated
runtime dependencies without replacing research PyTorch; implement backend and
speaker adapter with real enrollment/evaluation, preserving unknown readiness.

Heartbeat 2026-11-08 23:57 IST: three bounded SSH attempts rejected before login;
runtime setup job 45984 result could not be checked. Earlier verified suite45982
passed29 tests. Prepared local api.py and test_runtime_api.py: loopback-only upload
API factory, 16MiB size limit, serialized inference, temporary-file cleanup,
explicit unavailable-model state. Python compilation passes; API behavioral tests
are NOT executed yet. Transfer only these new files after reconnect; install/use
isolated runtime dependencies from45984, run API tests and real inference tests.
Do not treat skeleton API as complete streaming or calibrated security service.

Model-only runtime update: 46059 confirmed short repeat-padded bona fide clips
trigger the LA detector. Inference now abstains per detector until its full
window is available. A per-session stream buffers complete windows before
inference. Local focused suite: 13 passed. Source and tests deployed under the
HPC lock with backup. HPC job 46060 will test real checkpoints, CPU timing and
memory. Reconcile job exit and report before claiming live validation.

46060 passed 31 HPC tests and real-checkpoint stream/batch parity. Added the
model-only `SpeakerVerifier` module and local regression test. CPU 46066 checks
enrollment and cosine-score parity against the saved LA development evaluation.

46066 passed all 32 HPC tests and the four speaker parity cases. Optional
speaker evidence is now wired to the common model interface with full-window
and silence abstention. 15 focused local tests passed. 46071 verifies full
real-asset integration on CPU. Fused attack probability is not calibrated.

Packaged the existing HPC voicegaurd_runtime/audio.py in the local runtime.
SHA-256 matched HPC at 9194bc44c90ce8158f9bcf3ad6759b516fefdef34bd594eaff81d57946a79e74.
Local path smoke checks with a stub detector passed stereo WAV and FLAC
at 8 and 16 kHz, plus short-input abstention. Local runtime pytest passed
26 tests with one existing Starlette test-client deprecation warning.
INFERENCE_CONTRACT.md documents the tested formats and the untested fallback.

## Local microphone pilot

The separate demo entry point records one clip after an interactive
prompt and uses the existing inference adapter. In a model environment
with the project loader and the pinned LA and PA checkpoint files, install
`sounddevice` in the isolated environment and run from the workspace:

```powershell
$env:PYTHONPATH = "runtime_work"
python -m voicegaurd_runtime.microphone_demo --synthetic <LA-checkpoint> --replay <PA-checkpoint>
```

Replace the placeholders with actual paths. Use the checkpoint identities
in the validation report. Optional `--speaker-assets` and repeatable
`--reference` flags enable speaker evidence with authorized enrollment audio.
The pilot reports raw evidence and an uncertain decision for microphone
acquisition. The command help and 26 existing local tests passed. Live
recording with real checkpoints remains unverified.

The local staging directory is `%LOCALAPPDATA%/VoicegaurdDemo`. The
authorized HPC connection confirmed both checkpoints, the model loader
and the WavLM backbone. The loader copy points to the staged local
backbone, with the original source backed up alongside it. Dependency
installation was started in a dedicated venv that reuses the existing
CPU PyTorch installation. The initial asset copy had not completed at
the launcher check. `Start-MicrophoneDemo.ps1` rejects missing or
incomplete detector checkpoints using their pinned SHA-256 values.
After staging completes, verify backbone integrity and imports, then
run the launcher and capture an authorized spoken sample. The pilot
prints cold detector load time, analysis time and uncalibrated scores.

Staging completed in the Codex Windows app cache. The launcher resolves
that location from regular PowerShell and verified both checkpoint and
both backbone file hashes. The isolated venv imported sounddevice
0.5.6, transformers 4.57.6 and the shared CPU PyTorch 2.13.0. The
launcher smoke test decoded a five-second 16 kHz tone and ran both
trained checkpoints offline. Detector load took 12.097 seconds and
analysis took 1.819 seconds. Raw LA and PA scores were 0.001384 and
0.999579. These are tone responses. The Realtek microphone was detected.
Next run the launcher interactively to measure genuine speech.

Live microphone smoke test completed in the user's Windows PowerShell.
The pasted output shows 5.0 s of mono capture at 44.1 kHz, resampled to
16 kHz. Both pinned detectors scored the clip. Raw LA was 0.121848 and
raw PA was 0.618336. Cold load took 14.484 s and analysis took 1.605 s.
No error appeared in the output. Speaker verification was unavailable
for this run and the microphone decision remained uncertain.

The Windows launcher now accepts `-AudioPath` for existing audio files.
Verified both pinned detectors using a five-second WAV with spaces in
its path. Output identified file input and reported 55.898 s model load
and 2.316 s analysis. This was a test waveform. File and microphone
verdicts remain uncertain pending acquisition-specific validation.

Verified live SaveRecording and file round-trip on November 11 IST.
The saved five-second WAV produced exactly the same scores via
-AudioPath: synthetic 0.029927933588624, replay 0.8230652809143066.
Analysis took 1.397 s live and 1.352 s from file. Both returned uncertain.
Speaker verification was unavailable. No calibration claim.

User also confirmed the Windows -PickAudio path with the saved five-second
microphone WAV: identical LA and PA scores, 1.284 s analysis, and uncertain.
No repeat smoke test is needed.

Windows launcher accepts optional SpeakerAssets and ReferenceAudio for mic
and supplied-file modes. SpeechBrain 1.0.3 failed with the installed
TorchAudio, and 1.1.2 needed copy mode on Windows to avoid a symlink
privilege error. With 1.1.2 and copy mode, the saved WAV launcher smoke
test returned LA, PA and ECAPA evidence and an uncertain decision.
ECAPA cosine was 1.0 because the smoke test used the same clip for
enrollment and probe. This checks wiring only. Speaker-enabled live
capture has not been run. Existing runtime suite: 26 passed.
See DEMO_SETUP.md for reproduction.

Live three-model Windows smoke test passed on November 11 IST using a
saved enrollment clip and a fresh five-second microphone probe. The
launcher resampled mono 44.1 kHz audio to 16 kHz and returned LA 0.034628,
PA 0.846225, and ECAPA cosine 0.960968 (match at cutoff 0.4769288897514343).
Detector loading took 6.315 s and analysis took 1.574 s. The joint verdict
was uncertain as expected. This single run verifies live integration.

Windows MP3 decoding and the optional -ScanFile synthetic diagnostic passed
on the user's 60.94-second local MP3. All 16 windows covered the recording
through its final sample. Zero scores reached the LA research cutoff.
The voice-origin and joint verdicts remain uncertain for this input.

## Version 1 verification

All 27 runtime tests passed. The pinned models ran offline on a
12-second test tone and the existing MP3 file with a 16-window scan.
A one-second WAV returned an insufficient-audio reason, null LA and PA
scores, and zero scan windows. The new capture duration still needs
a physical microphone check. Use DEMO_SETUP.md for commands and
standalone LA validation results.

The user completed three live 12-second microphone runs and supplied
the labels in order: original human speech, AI with music, and AI
without music. The centered-window LA scores were 0.0000012321008853,
0.0000005325985057, and 0.895207464695. At the diagnostic cutoff of
0.0061066979542373995, the run flagged the AI clip without music, missed
the AI clip with music, and did not flag the human clip. PA scores were
0.9999973774, 0.9999989271, and 0.9999989271. This confirms the live
capture workflow. Three user-labeled clips cannot establish accuracy
or isolate music as the cause of the miss. The verdict stays uncertain.
