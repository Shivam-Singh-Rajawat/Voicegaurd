"""Loopback-only Voicegaurd V1 HTTP API and offline browser dashboard.

No uploads are retained. All model verdicts are explicitly uncertain outside
representative, independently validated acquisition-specific trials.
"""
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

_MAX_UPLOAD = 16 * 1024 * 1024
_ALLOWED = {".wav", ".flac", ".ogg", ".mp3"}
_ASSETS = Path(__file__).with_name("web")


def create_app(engine=None, *, speaker_verifier=None):
    from fastapi import FastAPI, File, HTTPException, Request, UploadFile
    from fastapi.responses import FileResponse
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    app = FastAPI(title="Voicegaurd local demo", version="1.0.0",
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware,
                       allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    gate = asyncio.Semaphore(1)

    @app.middleware("http")
    async def local_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "microphone=(self)"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; media-src 'self' blob:; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'self'"
        )
        return response

    @app.get("/")
    def index():
        return FileResponse(_ASSETS / "index.html", media_type="text/html")

    @app.get("/static/{filename}")
    def static_file(filename: str):
        if filename not in {"app.js", "styles.css"}:
            raise HTTPException(404, "Not found")
        return FileResponse(_ASSETS / filename)

    @app.get("/health")
    def health():
        return {"status": "ready" if engine is not None else "models_unavailable",
                "speaker_verification": "ready" if speaker_verifier is not None
                else "unavailable", "model_decision": "uncertain",
                "offline": True}

    async def save_upload(upload: UploadFile, folder: Path, name: str):
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in _ALLOWED:
            raise HTTPException(415, "Upload WAV, FLAC, OGG or MP3 audio")
        path = folder / (name + suffix)
        size = 0
        try:
            with path.open("xb") as destination:
                while True:
                    chunk = await upload.read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > _MAX_UPLOAD:
                        raise HTTPException(413, "Audio upload exceeds 16 MiB")
                    destination.write(chunk)
            if size == 0:
                raise HTTPException(422, "Audio upload is empty")
            return path
        finally:
            await upload.close()

    def analyze_file(path, reference_path, scan, scan_replay):
        active = engine
        if reference_path is not None:
            if speaker_verifier is None or not hasattr(engine, "detectors"):
                raise ValueError("Speaker model is not configured")
            from .audio import load_audio
            from .inference import VoicegaurdInference
            enrollment, _ = load_audio(reference_path)
            template = speaker_verifier.enroll([enrollment])
            active = VoicegaurdInference(
                engine.detectors, speaker_verifier=speaker_verifier,
                speaker_template=template)
        if scan:
            if not hasattr(active, "detectors") or "synthetic" not in active.detectors:
                raise ValueError("Window scanning needs a configured detector")
            from .audio import load_audio
            from .microphone_demo import scan_synthetic_windows
            samples, metadata = load_audio(path)
            result = dict(audio=metadata, **active.analyze_samples(samples))
            result["synthetic_file_scan"] = {
                "windows": scan_synthetic_windows(
                    samples, metadata["sample_rate"], active.detectors["synthetic"]),
                "calibrated": False,
            }
            if scan_replay:
                if "replay" not in active.detectors:
                    raise ValueError("Replay scanning needs a replay detector")
                result["replay_file_scan"] = {
                    "windows": scan_synthetic_windows(
                        samples, metadata["sample_rate"], active.detectors["replay"]),
                    "calibrated": False,
                }
        else:
            result = active.analyze(path)

        return {"decision": "uncertain",
                "reason": "No validated joint policy for arbitrary microphone or file audio.",
                "calibrated": False,
                "input_source": "uploaded_audio",
                **result}

    @app.post("/analyze")
    async def analyze(request: Request, file: UploadFile = File(...),
                      reference: UploadFile | None = File(None),
                      scan: bool = False, scan_replay: bool = False):
        if engine is None:
            raise HTTPException(503, "Models have not been loaded")
        origin = request.headers.get("origin")
        if origin and origin not in {
            str(request.base_url).rstrip("/"),
            "http://127.0.0.1:8765", "http://localhost:8765",
        }:
            raise HTTPException(403, "Cross-origin requests are disabled")
        if scan_replay and not scan:
            raise HTTPException(422, "Replay scan requires scan=true")
        if reference is not None and speaker_verifier is None:
            raise HTTPException(422, "Speaker model is unavailable")
        async with gate:
            with TemporaryDirectory(prefix="voicegaurd-upload-") as directory:
                folder = Path(directory)
                audio = await save_upload(file, folder, "audio")
                enrolled = (await save_upload(reference, folder, "reference")
                            if reference is not None else None)
                try:
                    return await asyncio.to_thread(
                        analyze_file, audio, enrolled, scan, scan_replay
                    )
                except (ValueError, RuntimeError, OSError) as exc:
                    raise HTTPException(422, "Audio could not be analyzed") from exc

    return app
