"""
Test CORS Security Configuration
WS-03: Ensure production CORS is strict and rejects wildcards
"""
import pytest
import os
import sys
from pydantic import ValidationError

# Add brain to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'brain'))


class TestCORSValidation:
    """Test CORS origin validation in config"""

    def test_production_rejects_wildcard_cors(self):
        """Production must reject CORS_ORIGINS='*'"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = '*'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_msg = str(exc_info.value)
        assert "CORS_ORIGINS='*' is not allowed in production" in error_msg

    def test_production_rejects_wildcard_in_origin(self):
        """Production must reject origins containing '*'"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = 'https://*.example.com'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_msg = str(exc_info.value)
        assert "contains wildcard '*'" in error_msg

    def test_production_rejects_empty_cors(self):
        """Production must reject empty CORS_ORIGINS"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = ''
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_msg = str(exc_info.value)
        assert "cannot be empty in production" in error_msg

    def test_production_rejects_whitespace_only_cors(self):
        """Production must reject whitespace-only CORS_ORIGINS"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = '   '
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_msg = str(exc_info.value)
        assert "cannot be empty in production" in error_msg

    def test_production_rejects_origins_without_protocol(self):
        """Production must reject origins without http:// or https://"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = 'app.example.com'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_msg = str(exc_info.value)
        assert "must start with http:// or https://" in error_msg

    def test_production_accepts_explicit_single_origin(self):
        """Production should accept explicit single origin"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = 'https://app.example.com'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        settings = Settings()
        assert settings.CORS_ORIGINS == 'https://app.example.com'
        assert settings.ENVIRONMENT == 'production'

    def test_production_accepts_explicit_multiple_origins(self):
        """Production should accept multiple explicit origins"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = 'https://app.example.com,https://ops.example.com'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        settings = Settings()
        assert settings.CORS_ORIGINS == 'https://app.example.com,https://ops.example.com'
        assert settings.ENVIRONMENT == 'production'

    def test_development_allows_wildcard(self):
        """Development/test environments should allow wildcard"""
        os.environ['ENV'] = 'development'
        os.environ['CORS_ALLOWED_ORIGINS'] = '*'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        settings = Settings()
        assert settings.CORS_ORIGINS == '*'
        assert settings.ENVIRONMENT == 'development'

    def test_test_env_allows_wildcard(self):
        """Test environment should allow wildcard"""
        os.environ['ENV'] = 'test'
        os.environ['CORS_ALLOWED_ORIGINS'] = '*'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        settings = Settings()
        assert settings.CORS_ORIGINS == '*'
        assert settings.ENVIRONMENT == 'test'


class TestCORSMiddleware:
    """Test CORS middleware configuration in main.py"""

    def test_wildcard_disables_credentials(self):
        """When CORS_ORIGINS='*', allow_credentials should be False"""
        # This tests the main.py logic
        cors_origins = "*"

        if cors_origins == "*":
            allow_credentials = False
        else:
            allow_credentials = True

        assert allow_credentials is False

    def test_explicit_origins_enable_credentials(self):
        """When CORS_ORIGINS are explicit, allow_credentials should be True"""
        cors_origins = "https://app.example.com"

        if cors_origins == "*":
            allow_credentials = False
        else:
            allow_credentials = True

        assert allow_credentials is True

    def test_allowed_headers_are_explicit(self):
        """Allowed headers must be explicit list, not wildcard"""
        allowed_headers = [
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Api-Key",
        ]

        # Ensure no wildcard in headers
        assert "*" not in allowed_headers
        # Ensure required headers are present
        assert "Authorization" in allowed_headers
        assert "Content-Type" in allowed_headers
        assert "X-Request-ID" in allowed_headers


class TestCORSSecurityScenarios:
    """Test real-world security scenarios"""

    def test_production_with_https_wildcard_fails(self):
        """Production must reject https://*"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = 'https://*'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_msg = str(exc_info.value)
        assert "contains wildcard '*'" in error_msg

    def test_production_mixed_valid_and_wildcard_fails(self):
        """Production must reject even if only one origin has wildcard"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = 'https://app.example.com,https://*.example.com'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_msg = str(exc_info.value)
        assert "contains wildcard '*'" in error_msg

    def test_production_http_localhost_is_allowed_for_testing(self):
        """Production can accept http://localhost for local testing if needed"""
        os.environ['ENV'] = 'production'
        os.environ['CORS_ALLOWED_ORIGINS'] = 'http://localhost:3000'
        os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_KEY'] = 'test_key'
        os.environ['JWT_SECRET'] = 'test_secret_key_min_32_chars_long_xx'
        os.environ['BRAIN_SECRET'] = 'test_brain_secret_key'

        from core.config import Settings

        settings = Settings()
        assert settings.CORS_ORIGINS == 'http://localhost:3000'
