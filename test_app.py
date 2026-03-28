"""
Unit tests for MedBridge AI Triage Application
Run with: python -m pytest test_app.py -v
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from app import app, ALLOWED_LANGUAGES


@pytest.fixture
def client():
    """Create a test client with testing mode enabled."""
    app.config['TESTING'] = True
    app.config['RATELIMIT_ENABLED'] = False  # Disable rate limiting in tests
    with app.test_client() as c:
        yield c


# ── Health Check ──────────────────────────────────────────────────────────────
class TestHealthEndpoint:
    def test_health_ok(self, client):
        """GET /api/health should return 200 with status=ok."""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert data['service'] == 'medbridge-ai'

    def test_health_has_version(self, client):
        """Health endpoint should expose a version string."""
        response = client.get('/api/health')
        data = json.loads(response.data)
        assert 'version' in data


# ── Input Validation ──────────────────────────────────────────────────────────
class TestInputValidation:
    def test_missing_input_returns_400(self, client):
        """POST /api/analyze without input should return 400."""
        response = client.post('/api/analyze',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 400

    def test_text_too_long_returns_400(self, client):
        """Text exceeding 5000 chars should be rejected."""
        response = client.post('/api/analyze',
                               data=json.dumps({'text': 'a' * 5001}),
                               content_type='application/json')
        assert response.status_code == 400

    def test_invalid_language_falls_back_to_english(self, client):
        """An invalid target_language should be silently replaced with English."""
        with patch('app.get_client') as mock_client:
            mock_client.return_value = None  # Force demo mode
            response = client.post('/api/analyze',
                                   data=json.dumps({
                                       'text': 'I have a headache',
                                       'target_language': 'Klingon'
                                   }),
                                   content_type='application/json')
            # Should still succeed (falls back to demo mode)
            assert response.status_code == 200


# ── Language Whitelist ────────────────────────────────────────────────────────
class TestAllowedLanguages:
    def test_english_is_allowed(self):
        assert 'English' in ALLOWED_LANGUAGES

    def test_all_major_indian_languages_included(self):
        indian = ['Hindi', 'Bengali', 'Telugu', 'Marathi', 'Tamil',
                  'Urdu', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi']
        for lang in indian:
            assert lang in ALLOWED_LANGUAGES, f"{lang} is missing from ALLOWED_LANGUAGES"

    def test_invalid_language_not_in_whitelist(self):
        assert 'Klingon' not in ALLOWED_LANGUAGES
        assert '' not in ALLOWED_LANGUAGES


# ── Demo Mode ─────────────────────────────────────────────────────────────────
class TestDemoMode:
    def test_demo_mode_when_no_api_key(self, client):
        """When no API key configured, should return valid demo triage data."""
        with patch('app.get_client', return_value=None):
            response = client.post('/api/analyze',
                                   data=json.dumps({'text': 'I have chest pain'}),
                                   content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'diagnosis_priority' in data
            assert 'referral' in data
            assert 'symptom_checklist' in data

    def test_demo_response_has_correct_schema(self, client):
        """Demo mode response should include all expected fields."""
        with patch('app.get_client', return_value=None):
            response = client.post('/api/analyze',
                                   data=json.dumps({'text': 'test'}),
                                   content_type='application/json')
            data = json.loads(response.data)
            required_fields = ['diagnosis_priority', 'referral', 'symptom_checklist',
                               'nearest_er', 'pre_fill_form', 'language_detected']
            for field in required_fields:
                assert field in data, f"Field '{field}' missing from demo response"


# ── Security Headers ──────────────────────────────────────────────────────────
class TestSecurityHeaders:
    def test_xss_protection_header(self, client):
        response = client.get('/')
        assert 'X-XSS-Protection' in response.headers

    def test_content_type_options_header(self, client):
        response = client.get('/')
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_frame_options_header(self, client):
        response = client.get('/')
        assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'


# ── Index Route ───────────────────────────────────────────────────────────────
class TestIndexRoute:
    def test_index_returns_200(self, client):
        """Home page should load successfully."""
        response = client.get('/')
        assert response.status_code == 200

    def test_index_returns_html(self, client):
        """Home page should return HTML content."""
        response = client.get('/')
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
