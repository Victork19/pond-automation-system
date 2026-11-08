from fastapi.testclient import TestClient
from app.main import app

def test_health_and_settings():
    with TestClient(app) as client:
        assert client.get('/api/health').status_code == 200
        settings = client.get('/api/settings')
        assert settings.status_code == 200
        assert settings.json()['warm_signal_threshold'] == 6.0

def test_call_event_is_idempotent():
    payload = {'event_id':'calendar-test-001','account':'Acme','ends_at':'2026-11-07T10:00:00+00:00'}
    with TestClient(app) as client:
        first = client.post('/api/call-events', json=payload).json()
        second = client.post('/api/call-events', json=payload).json()
        assert first['id'] == second['id']
        assert second['idempotent'] is True
