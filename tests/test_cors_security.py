"""
Test CORS Security Configuration
WS-03: Ensure production CORS is strict and rejects wildcards
"""
import sys
import pytest
import os
from pydantic import ValidationError

# Add brain to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'brain'))


# ── Shared fixture ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear lru_cache on get_settings before and after every test."""
    # Clear the module-level lru_cache so each test gets a fresh Settings instance
    try:
        import core.config as cfg
        cfg.get_settings.cache_clear()
    except Exception:
        pass
    yield
    try:
        import core.config as cfg
        cfg.get_settings.cache_clear()
    except Exception:
        pass


_COMMON_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test_key",
    "JWT_SECRET": "test_secret_key_min_32_chars_long_xx",
    "BRAIN_SECRET": "test_brain_secret_key",
}


class TestCORSValidation:
    """Test CORS origin validation in config"""

    def test_production_rejects_wildcard_cors(self, monkeypatch):
        """Production must reject CORS_ORIGINS='*'"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "CORS_ORIGINS='*' is not allowed in production" in str(exc_info.value)

    def test_production_rejects_wildcard_in_origin(self, monkeypatch):
        """Production must reject origins containing '*'"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://*.example.com")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "contains wildcard '*'" in str(exc_info.value)

    def test_production_rejects_empty_cors(self, monkeypatch):
        """Production must reject empty CORS_ORIGINS"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "cannot be empty in production" in str(exc_info.value)

    def test_production_rejects_whitespace_only_cors(self, monkeypatch):
        """Production must reject whitespace-only CORS_ORIGINS"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "   ")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "cannot be empty in production" in str(exc_info.value)

    def test_production_rejects_origins_without_protocol(self, monkeypatch):
        """Production must reject origins without http:// or https://"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "app.example.com")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "must start with http:// or https://" in str(exc_info.value)

    def test_production_rejects_origin_with_path(self, monkeypatch):
        """Production must reject origins that include a path component"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com/api")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "must not contain a path" in str(exc_info.value)

    def test_production_rejects_bare_scheme(self, monkeypatch):
        """Production must reject bare scheme with no host"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "has no host" in str(exc_info.value)

    def test_production_accepts_explicit_single_origin(self, monkeypatch):
        """Production should accept explicit single origin"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        from core.config import Settings
        s = Settings()
        assert s.CORS_ORIGINS == "https://app.example.com"
        assert s.ENVIRONMENT == "production"

    def test_production_accepts_explicit_multiple_origins(self, monkeypatch):
        """Production should accept multiple explicit origins"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com,https://ops.example.com")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        from core.config import Settings
        s = Settings()
        assert s.CORS_ORIGINS == "https://app.example.com,https://ops.example.com"
        assert s.ENVIRONMENT == "production"

    def test_development_allows_wildcard(self, monkeypatch):
        """Development/test environments should allow wildcard"""
        monkeypatch.setenv("ENV", "development")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        from core.config import Settings
        s = Settings()
        assert s.CORS_ORIGINS == "*"
        assert s.ENVIRONMENT == "development"

    def test_test_env_allows_wildcard(self, monkeypatch):
        """Test environment should allow wildcard"""
        monkeypatch.setenv("ENV", "test")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        from core.config import Settings
        s = Settings()
        assert s.CORS_ORIGINS == "*"
        assert s.ENVIRONMENT == "test"

    def test_dev_rejects_mixed_wildcard_and_origins(self, monkeypatch):
        """Even in development, '*' mixed with explicit origins must be rejected"""
        monkeypatch.setenv("ENV", "development")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*,https://app.example.com")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "cannot mix '*' with explicit origins" in str(exc_info.value)


class TestCORSSecurityScenarios:
    """Test real-world security scenarios"""

    def test_production_with_https_wildcard_fails(self, monkeypatch):
        """Production must reject https://*"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://*")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "contains wildcard '*'" in str(exc_info.value)

    def test_production_mixed_valid_and_wildcard_fails(self, monkeypatch):
        """Production must reject even if only one origin has wildcard"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com,https://*.example.com")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        with pytest.raises(ValidationError) as exc_info:
            from core.config import Settings
            Settings()

        assert "contains wildcard '*'" in str(exc_info.value)

    def test_production_http_localhost_is_allowed_for_testing(self, monkeypatch):
        """Production can accept http://localhost for local testing if needed"""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)

        from core.config import Settings
        s = Settings()
        assert s.CORS_ORIGINS == "http://localhost:3000"


class TestCORSMiddleware:
    """Test the actually-registered CORSMiddleware in brain.main"""

    def _build_app(self, monkeypatch, cors_origins: str, env: str = "development"):
        """Return a freshly-built FastAPI app with given CORS config."""
        monkeypatch.setenv("ENV", env)
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", cors_origins)
        for k, v in _COMMON_ENV.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("DB_BACKEND", "sqlite")
        monkeypatch.setenv("BRAIN_DATA_DIR", "/tmp/test_brain_data")

        # Force reload of config and main so our env vars take effect
        for mod in list(sys.modules.keys()):
            if mod.startswith("core.") or mod in ("core", "main") or mod.startswith("brain."):
                del sys.modules[mod]

        import core.config as cfg
        cfg.get_settings.cache_clear()

        from unittest.mock import Mock, patch
        mock_sb = Mock()

        with patch("supabase.create_client", return_value=mock_sb):
            import main as brain_main
        return brain_main.app

    def _get_cors_middleware(self, app):
        from starlette.middleware.cors import CORSMiddleware as StarletteCorsMW
        from fastapi.middleware.cors import CORSMiddleware
        for mw in app.user_middleware:
            if mw.cls in (CORSMiddleware, StarletteCorsMW):
                return mw
        return None

    def test_wildcard_cors_disables_credentials(self, monkeypatch):
        """When CORS_ORIGINS='*', allow_credentials must be False"""
        app = self._build_app(monkeypatch, "*", env="development")
        mw = self._get_cors_middleware(app)
        assert mw is not None, "CORSMiddleware not registered"
        assert mw.kwargs.get("allow_credentials") is False
        assert "*" in mw.kwargs.get("allow_origins", [])

    def test_explicit_origins_enable_credentials(self, monkeypatch):
        """When CORS_ORIGINS are explicit, allow_credentials must be True"""
        app = self._build_app(monkeypatch, "https://app.example.com", env="production")
        mw = self._get_cors_middleware(app)
        assert mw is not None, "CORSMiddleware not registered"
        assert mw.kwargs.get("allow_credentials") is True
        assert mw.kwargs.get("allow_origins") == ["https://app.example.com"]

    def test_allowed_headers_include_x_brain_key(self, monkeypatch):
        """CORSMiddleware must include X-Brain-Key in allow_headers"""
        app = self._build_app(monkeypatch, "https://app.example.com", env="production")
        mw = self._get_cors_middleware(app)
        assert mw is not None, "CORSMiddleware not registered"
        headers = mw.kwargs.get("allow_headers", [])
        assert "X-Brain-Key" in headers, f"X-Brain-Key missing from allow_headers: {headers}"

    def test_allowed_headers_no_wildcard(self, monkeypatch):
        """CORSMiddleware must not use wildcard allow_headers"""
        app = self._build_app(monkeypatch, "https://app.example.com", env="production")
        mw = self._get_cors_middleware(app)
        assert mw is not None, "CORSMiddleware not registered"
        headers = mw.kwargs.get("allow_headers", [])
        assert "*" not in headers, "Wildcard '*' found in allow_headers"
        assert "Authorization" in headers
        assert "Content-Type" in headers

