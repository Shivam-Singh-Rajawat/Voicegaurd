# Voicegaurd

Voicegaurd is a Windows prototype for inspecting audio for synthetic speech
and replay signals. It supports microphone capture and local audio files,
with optional speaker comparison against a supplied reference.

From the project folder in PowerShell:

```powershell
.\runtime_work\Start-MicrophoneDemo.ps1 -ScanRecording
.\runtime_work\Start-MicrophoneDemo.ps1 -PickAudio -ScanFile
```

See the [Version 1 setup guide](runtime_work/DEMO_SETUP.md) for the required
Python environment, LA and PA checkpoints, and WavLM assets. The demo reports
raw detector evidence. Voice-origin and joint verdicts remain uncertain for
the current input scopes.

The [model validation report](model_work/MODEL_VALIDATION.md) documents
benchmarks, limitations, and reproduction details. The cluster scripts
in `model_work` require access to the original HPC environment or adaptation
to your own cluster.
