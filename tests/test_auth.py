"""
Test Suite — Authentication System
Tests for JWT tokens, API keys, password security, and multi-auth flows.
"""
import pytest
import hashlib
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from jose import jwt

# Add brain to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'brain'))

from core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    generate_api_key,
    verify_api_key,
    CurrentUser,
)
from core.config import settings


class TestTokenCreation:
    """Test JWT access and refresh token creation"""

    def test_access_token_creation(self):
        """Verify access token contains correct claims"""
        user_id = "test_user_123"
        role = "admin"
        org_id = "org_456"

        token = create_access_token(user_id, role, org_id)

        # Decode without verification for testing
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        assert payload["sub"] == user_id
        assert payload["role"] == role
        assert payload["org_id"] == org_id
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_refresh_token_creation(self):
        """Verify refresh token has longer expiry and JTI"""
        user_id = "test_user_123"

        token = create_refresh_token(user_id)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "jti" in payload  # JWT ID for refresh token rotation
        assert "exp" in payload

        # Verify expiry is in the future (refresh tokens last longer)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp_time > now + timedelta(days=1)

    def test_token_decode_success(self):
        """Test successful token decoding"""
        user_id = "test_user_123"
        role = "user"

        token = create_access_token(user_id, role)
        payload = decode_token(token)

        assert payload["sub"] == user_id
        assert payload["role"] == role

    def test_token_decode_invalid(self):
        """Test decoding invalid token raises HTTPException"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid_token_string")

        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)

    def test_token_decode_expired(self):
        """Test decoding expired token raises HTTPException"""
        from fastapi import HTTPException

        # Create token that expired 1 hour ago
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": "test_user",
            "role": "user",
            "type": "access",
            "exp": expire,
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)

        assert exc_info.value.status_code == 401


class TestPasswordSecurity:
    """Test password hashing and verification with bcrypt"""

    def test_password_hashing(self):
        """Verify password is hashed correctly"""
        password = "MySecureP@ssw0rd123"
        hashed = hash_password(password)

        # Hashed should be different from plaintext
        assert hashed != password
        # BCrypt hashes start with $2b$
        assert hashed.startswith("$2b$")
        # Hashed length should be consistent
        assert len(hashed) == 60

    def test_password_verification_success(self):
        """Test correct password verification"""
        password = "MySecureP@ssw0rd123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_password_verification_failure(self):
        """Test incorrect password verification"""
        password = "MySecureP@ssw0rd123"
        wrong_password = "WrongPassword123"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_password_hash_uniqueness(self):
        """Test that same password generates different hashes (salt)"""
        password = "MySecureP@ssw0rd123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Different hashes due to random salt
        assert hash1 != hash2
        # But both should verify the same password
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_timing_attack_resistance(self):
        """Test that verification time is consistent (timing attack prevention)"""
        password = "MySecureP@ssw0rd123"
        hashed = hash_password(password)

        # Time correct password
        start = time.perf_counter()
        verify_password(password, hashed)
        time_correct = time.perf_counter() - start

        # Time incorrect password
        start = time.perf_counter()
        verify_password("WrongPassword123", hashed)
        time_incorrect = time.perf_counter() - start

        # Times should be similar (within 50ms) to prevent timing attacks
        # Note: bcrypt inherently provides timing attack resistance
        assert abs(time_correct - time_incorrect) < 0.05


class TestAPIKeys:
    """Test API key generation and verification"""

    @patch('core.auth.get_database_client')
    def test_api_key_generation(self, mock_get_db):
        """Test API key generation returns correct format"""
        mock_db = Mock()
        mock_db.insert.return_value = Mock(success=True)
        mock_get_db.return_value = mock_db

        org_id = "org_123"
        name = "Production API Key"
        scopes = ["read", "write"]

        plain_key, key_hash = generate_api_key(org_id, name, scopes)

        # Key should start with ml_ prefix
        assert plain_key.startswith("ml_")
        # Key should be sufficiently long
        assert len(plain_key) > 30
        # Hash should be SHA256 (64 hex chars)
        assert len(key_hash) == 64

        # Verify hash matches
        expected_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        assert key_hash == expected_hash

    @patch('core.auth.get_database_client')
    def test_api_key_verification_success(self, mock_get_db):
        """Test successful API key verification"""
        plain_key = "ml_test_key_12345"
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()

        # Mock database response
        mock_db = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = [{
            "id": "key_1",
            "org_id": "org_123",
            "name": "Test Key",
            "key_hash": key_hash,
            "scopes": ["read", "write"],
            "is_active": True
        }]
        mock_db.select.return_value = mock_result
        mock_db.update.return_value = Mock(success=True)
        mock_get_db.return_value = mock_db

        result = verify_api_key(plain_key)

        assert result is not None
        assert result["org_id"] == "org_123"
        assert "read" in result["scopes"]

    @patch('core.auth.get_database_client')
    def test_api_key_verification_failure(self, mock_get_db):
        """Test API key verification with invalid key"""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = []  # No matching key
        mock_db.select.return_value = mock_result
        mock_get_db.return_value = mock_db

        result = verify_api_key("ml_invalid_key")

        assert result is None


class TestMultiAuthFlow:
    """Test CurrentUser class and multi-auth scenarios"""

    def test_current_user_creation_jwt(self):
        """Test CurrentUser object creation from JWT"""
        user = CurrentUser(
            user_id="user_123",
            role="admin",
            org_id="org_456",
            via="jwt"
        )

        assert user.user_id == "user_123"
        assert user.role == "admin"
        assert user.org_id == "org_456"
        assert user.via == "jwt"
        assert user.is_admin is True

    def test_current_user_creation_api_key(self):
        """Test CurrentUser object creation from API key"""
        user = CurrentUser(
            user_id="api_key_789",
            role="user",
            org_id="org_456",
            via="api_key"
        )

        assert user.user_id == "api_key_789"
        assert user.via == "api_key"
        assert user.is_admin is False

    def test_current_user_admin_check(self):
        """Test admin role detection"""
        admin = CurrentUser(user_id="u1", role="admin", org_id="org1")
        super_admin = CurrentUser(user_id="u2", role="super_admin", org_id="org1")
        regular_user = CurrentUser(user_id="u3", role="user", org_id="org1")

        assert admin.is_admin is True
        assert super_admin.is_admin is True
        assert regular_user.is_admin is False

    def test_current_user_no_org(self):
        """Test CurrentUser without org_id (system users)"""
        user = CurrentUser(
            user_id="system_bot",
            role="agent",
            org_id=None,
            via="brain_key"
        )

        assert user.org_id is None
        assert user.via == "brain_key"
