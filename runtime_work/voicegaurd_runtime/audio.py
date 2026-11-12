"""Verified 16kHz mono runtime input. No denoising or amplitude normalization."""
import subprocess
from pathlib import Path
from math import gcd
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

def load_audio(path,target_sr=16000,max_seconds=120):
    if not isinstance(target_sr,int) or target_sr<=0: raise ValueError("Invalid sample rate")
    if not np.isfinite(max_seconds) or max_seconds<=0: raise ValueError("Invalid duration limit")
    path=Path(path)
    if not path.is_file(): raise FileNotFoundError(path)
    info=sf.info(str(path))
    if info.samplerate<=0 or info.channels<1 or not 0<info.duration<=max_seconds: raise ValueError("Invalid or excessive audio duration/metadata")
    decoder="soundfile"
    try:
        # MP3 headers can estimate duration. Bound decoding and use the
        # actual decoded length when it fits within the configured limit.
        read_limit = int(max_seconds * info.samplerate)
        x,sr=sf.read(str(path),frames=read_limit + 1,dtype="float32",always_2d=True)
        if len(x)>read_limit: raise ValueError("Excessive decoded audio duration")
        if sr!=info.samplerate or x.shape[1]!=info.channels or (
            info.format!="MP3" and len(x)!=info.frames
        ): raise ValueError("Decoded frame mismatch")
        decoded_frames = len(x)
        if not np.isfinite(x).all(): raise ValueError("Non-finite audio")
        x=x.mean(axis=1)
        if sr!=target_sr:
            g=gcd(sr,target_sr); x=resample_poly(x,target_sr//g,sr//g)
    except Exception as original:
        import imageio_ffmpeg
        decoder="ffmpeg"
        result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-nostdin","-v","error","-xerror","-i",str(path),"-map","0:a:0","-ac","1","-ar",str(target_sr),"-f","f32le","pipe:1"],capture_output=True,timeout=60)
        if result.returncode or len(result.stdout)%4: raise ValueError("Audio decoding failed: "+result.stderr.decode(errors="replace")[-400:]) from original
        x=np.frombuffer(result.stdout,dtype="<f4").copy()
        decoded_frames = info.frames
    expected=int(round(decoded_frames*target_sr/info.samplerate))
    if abs(len(x)-expected)>1: raise ValueError("Decoded duration mismatch")
    if not x.size or not np.isfinite(x).all(): raise ValueError("Empty or non-finite audio")
    return np.asarray(x,dtype=np.float32),dict(sample_rate=target_sr,original_sample_rate=info.samplerate,original_channels=info.channels,decoder=decoder,duration=len(x)/target_sr)
