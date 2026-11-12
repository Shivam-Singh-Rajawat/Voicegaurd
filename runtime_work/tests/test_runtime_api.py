from fastapi.testclient import TestClient
from voicegaurd_runtime.api import create_app


class Engine:
    def analyze(self, path):
        assert path.read_bytes() == b"example"
        return {"evidence": {}, "calibrated": False}


def test_unloaded_service_reports_unavailable():
    client = TestClient(create_app())
    assert client.get('/health').json()['status'] == 'models_unavailable'
    assert client.post('/analyze', files={'file': ('a.wav', b'example')}).status_code == 503


def test_upload_passes_to_engine():
    client = TestClient(create_app(Engine()))
    response = client.post('/analyze', files={'file': ('../../a.wav', b'example')})
    assert response.status_code == 200 and response.json()['calibrated'] is False


def test_upload_validation():
    client = TestClient(create_app(Engine()))
    assert client.post('/analyze', files={'file': ('a.exe', b'x')}).status_code == 415
    assert client.post('/analyze', files={'file': ('a.wav', b'')}).status_code == 422
    assert client.post('/analyze', files={'file': ('a.wav', b'x' * (16 * 1024 * 1024 + 1))}).status_code == 413
