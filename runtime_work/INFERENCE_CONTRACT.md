# Voicegaurd model inference contract v0.1

Draft handoff for the current Python runtime. The version identifies this
document. The runtime does not emit a contract version field.

## Audio and entry points

- `VoicegaurdInference.analyze_samples(samples)` accepts one nonempty,
  finite mono waveform already resampled to 16 kHz. Pass normalized PCM
  as floating-point samples. The method converts to float32 and cannot
  infer sample rate from the array. The detector clips values to [-1, 1].
- The path-based `analyze(audio_path)` entry point uses the packaged HPC
  audio loader. It reads metadata with SoundFile, rejects audio longer
  than 120 seconds, averages channels and resamples to 16 kHz. Its audio
  metadata reports the original rate, channel count, output rate,
  duration and decoder. Local path smoke tests passed for stereo WAV and
  FLAC at 8 and 16 kHz. The existing FFmpeg decode fallback requires
  `imageio_ffmpeg` and was outside those smoke tests.
- `open_stream(hop_seconds=1.0)` creates per-session state. Feed 16 kHz
  mono chunks of at most ten seconds. A push returns zero or more complete
  windows with `start_seconds` and the same evidence fields as batch.
  The buffer uses the longest configured detector window and emits
  nothing until it fills. Reset or replace the stream between recordings.
- Invalid sample shape, non-finite data, and invalid buffer settings
  raise `ValueError`. Keep invalid input or model-load failures distinct
  from valid audio that yields an abstention.

## Evidence and decisions

| Output | Meaning |
| --- | --- |
| `evidence.synthetic`, `evidence.replay` | Present only for configured detectors. A scored result has a raw score in [0, 1], checkpoint path, architecture, window duration and `calibrated=false`. |
| `status=no_signal` or `insufficient_audio` | An all-zero waveform or a clip shorter than the detector window. Score is null. Streaming buffers incomplete windows before emitting evidence. |
| `speaker_verification` | The string `unavailable` if speaker verification is unconfigured. A configured verifier returns cosine similarity, cutoff and match when scored. For short or silent audio, similarity and match are null. |
| `RiskEngine.update_from_inference` | An optional heuristic returning `low`, `medium`, `high` or `uncertain`. It requires caller-verified LA or PA scope, the expected checkpoint path and a separate quality judgment. Missing required evidence or unreliable quality resets policy history and returns uncertainty. |

For a downstream result, describe medium/high evidence as suspicious
within the applicable scope. Describe low as no alert in the available
evidence. A genuine claim would require a separately validated operating
policy. An unknown microphone recording can produce diagnostic scores
while its operational decision remains uncertain. The heuristic score is
the percentage of recent usable windows with an alert.

Pin a deployment manifest with checkpoint digest, architecture, preprocessing,
score direction, cutoff and calibration source for each enabled model.
The current policy compares the checkpoint path. Verify digests when
loading assets. Keep speaker cutoffs tied to their protocol and model.
Use one policy history per stream and clear it when starting a new recording.
