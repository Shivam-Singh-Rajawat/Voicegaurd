# Voicegaurd Version 1 — Local browser application

Voicegaurd is a **local-only research demonstration** backed by two pinned
audio-model checkpoints. It does not upload speech to a cloud server and does
not make deployment-grade human-versus-AI, replay, or speaker identity claims.

## Start on the validated Windows laptop

Open PowerShell in the root of the Voicegaurd repository:

~~~powershell
.\runtime_work\Start-WebDemo.ps1
~~~

Once the models have loaded, open **http://127.0.0.1:8765** in a browser.
The local process is bound to 127.0.0.1 only. Press **Ctrl+C** in the
PowerShell window to stop it.

Before starting the server, you can check model digests and run an offline
real-checkpoint test-tone inference:

~~~powershell
.\runtime_work\Start-WebDemo.ps1 -SmokeTest
~~~

The launcher automatically searches for the existing dedicated
VoicegaurdDemo installation under LOCALAPPDATA, then
the Codex Windows app cache. Use -DemoRoot "C:\path\to\VoicegaurdDemo"
for a different location. It verifies fixed LA, PA and WavLM SHA-256 hashes;
any mismatched file stops startup. It never downloads model files.

Optional speaker comparison uses approved enrollment audio and actual
ECAPA assets (not the Git LFS pointer files):

~~~powershell
.\runtime_work\Start-WebDemo.ps1 -SpeakerAssets "C:\path\to\speaker_assets"
~~~

The speaker asset directory is loaded into an isolated temporary cache.
After startup, the browser allows an authorized enrollment clip to be
uploaded alongside the probe. Unconfigured speaker comparison is displayed
as unavailable. Enrollment/probe from the same session is only an integration
smoke test, not a cross-session verification result.

## Browser workflow

1. Pick a WAV, FLAC, OGG or MP3 file **or** grant microphone permission to
   record approximately 12 seconds using the browser's local audio API.
   Speak continuously for at least 8 seconds; the model itself requires
   a full 4.0375-second window, which may include silence.
2. Optionally enable synthetic and replay window scans. The normal result
   uses a centered window for each detector. Scans cover only full windows,
   including the final overlapping one. Missing/short/silent windows
   have no valid score.
3. Optionally supply a reference clip if the speaker verifier was enabled
   when the server started.
4. Run analysis. The dashboard always displays a separate **model prediction label**:
   **AI-generated**, **Human**, or **Unknown** (for abstentions).
   These labels come from a frozen standalone LA research cutoff, and each
   includes a **PROVISIONAL / NOT VERIFIED** flag. The Human label means only
   that the trained model score was below its diagnostic cutoff; external
   benchmarks demonstrate missed fakes. It is not an authenticity guarantee.
   Inspect the independent raw LA, PA and optional ECAPA evidence.
   The **overall security verdict stays Uncertain** for this input scope.
5. Export the complete JSON result through the browser if needed. Exporting
   requires an explicit button click; scores are not silently persisted.

Uploads are limited to **16 MiB per audio file**, and the existing decoder
has a **120-second duration limit**. Uploaded waveform and reference files are
placed in a temporary directory and removed after analysis; no cloud upload
or background audio retention occurs. The selected browser file remains in
browser memory while the page is open. JSON reports may reveal local
checkpoint paths and speaker similarity: share them with care.

For browser microphone recording, access the exact local address above, and
grant microphone permission when asked. The browser uses mono PCM 16-bit
WAV for transmission. Process only audio you are authorized to analyze.

## Security boundaries

- Local Uvicorn binds to 127.0.0.1, never 0.0.0.0.
- Requests are serialized to avoid concurrent model inference.
- Accepted file extensions and file sizes are bounded before decoding.
- Foreign browser Origin and untrusted Host headers are rejected.
- The app serves only bundled CSS/JS and uses a restrictive CSP.
- Temporary audio is deleted on success or failure.
- This prototype has **no user authentication**, per-user rate limiting,
  or production security review. Do not expose it on the internet, through
  a reverse proxy or on a public Vercel endpoint.

## Testing

From the project root, with Python dependencies installed:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "runtime_work")
py -3.14 -m pytest -q runtime_work/tests
~~~

This tests API upload safety, local HTML, scan behavior, short-recording
abstention, optional speaker enrollment and JSON exports. Run the dedicated
pinned-checkpoint smoke test separately; automated tests are not evidence
of field model accuracy.

## Research limits

Gate 8 (real-world speaker robustness) and Gate 9 (calibrated, aligned
joint-risk assessment) remain **OPEN**. The frozen cutoff performed poorly
in some acoustic conditions. The research status is **7 of 9**, not 9 of 9.
See model_work/MODEL_VALIDATION.md and
model_work/RECORDED_AUDIO_JOINT_PROTOCOL.md. The local browser application
can be a complete **Version 1 demo deliverable** without claiming those
unverified research gates have passed.
