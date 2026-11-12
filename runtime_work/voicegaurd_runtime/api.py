"""Local inference API. Launch only on loopback until access controls exist."""
import asyncio
from pathlib import Path
import tempfile


def create_app(engine=None):
    from fastapi import FastAPI, File, HTTPException, UploadFile
    app = FastAPI(title="Voicegaurd", version="0.1.0")
    gate = asyncio.Semaphore(1)

    @app.get("/health")
    async def health():
        return {"status": "ready" if engine else "models_unavailable",
                "speaker_verification": "unavailable"}

    @app.post("/analyze")
    async def analyze(file: UploadFile = File(...)):
        if engine is None:
            raise HTTPException(503, "Models have not been loaded")
        suffix = Path(file.filename or "audio.wav").suffix.lower()
        if suffix not in {".wav", ".flac", ".ogg"}:
            raise HTTPException(415, "Upload WAV, FLAC or OGG audio")
        async with gate:
            path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp:
                    path = Path(temp.name)
                    total = 0
                    while True:
                        chunk = await file.read(65536)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > 16 * 1024 * 1024:
                            raise HTTPException(413, "Audio upload exceeds 16 MiB")
                        temp.write(chunk)
                if not total:
                    raise HTTPException(422, "Audio upload is empty")
                try:
                    return await asyncio.to_thread(engine.analyze, path)
                except (ValueError, RuntimeError) as error:
                    raise HTTPException(422, "Audio could not be analyzed") from error
            finally:
                await file.close()
                if path is not None:
                    path.unlink(missing_ok=True)

    return app
