"""
Tests for authentication and security functionality
"""
import pytest
import time
from unittest.mock import patch, MagicMock
import sys
import os

# Import auth modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth.auth_service import AuthService, User
from app.auth.session_manager import SessionManager
from app.security.rate_limiter import RateLimiter
from app.security.input_validator import InputValidator
from app.security.csrf_protection import CSRFProtection

class TestAuthService:
    """Test cases for AuthService"""

    @pytest.fixture
    def auth_service(self):
        """Create auth service for testing"""
        config = {
            'SECRET_KEY': 'test-secret-key',
            'SESSION_TIMEOUT': 3600
        }
        return AuthService(config)

    def test_create_user(self, auth_service):
        """Test user creation"""
        user = auth_service.create_user(
            username="testuser",
            email="test@example.com",
            password="secure_password123",
            role="user"
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.password_hash != "secure_password123"  # Should be hashed

    def test_create_user_duplicate_username(self, auth_service):
        """Test creating user with duplicate username"""
        auth_service.create_user("testuser", "test1@example.com", "password123")

        with pytest.raises(ValueError, match="Username already exists"):
            auth_service.create_user("testuser", "test2@example.com", "password456")

    def test_authenticate_user_success(self, auth_service):
        """Test successful user authentication"""
        auth_service.create_user("testuser", "test@example.com", "password123")

        user = auth_service.authenticate_user("testuser", "password123")
        assert user is not None
        assert user.username == "testuser"

    def test_authenticate_user_wrong_password(self, auth_service):
        """Test authentication with wrong password"""
        auth_service.create_user("testuser", "test@example.com", "password123")

        user = auth_service.authenticate_user("testuser", "wrongpassword")
        assert user is None

    def test_authenticate_user_nonexistent(self, auth_service):
        """Test authentication with non-existent user"""
        user = auth_service.authenticate_user("nonexistent", "password")
        assert user is None

    def test_get_user_by_id(self, auth_service):
        """Test getting user by ID"""
        created_user = auth_service.create_user("testuser", "test@example.com", "password123")

        retrieved_user = auth_service.get_user_by_id(created_user.user_id)
        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"

    def test_update_user_last_login(self, auth_service):
        """Test updating user's last login"""
        user = auth_service.create_user("testuser", "test@example.com", "password123")
        original_last_login = user.last_login

        time.sleep(0.1)  # Ensure time difference
        auth_service.update_last_login(user.user_id)

        updated_user = auth_service.get_user_by_id(user.user_id)
        assert updated_user.last_login > original_last_login

    def test_change_password(self, auth_service):
        """Test changing user password"""
        user = auth_service.create_user("testuser", "test@example.com", "oldpassword")

        success = auth_service.change_password(user.user_id, "oldpassword", "newpassword123")
        assert success

        # Verify old password no longer works
        auth_result = auth_service.authenticate_user("testuser", "oldpassword")
        assert auth_result is None

        # Verify new password works
        auth_result = auth_service.authenticate_user("testuser", "newpassword123")
        assert auth_result is not None

class TestSessionManager:
    """Test cases for SessionManager"""

    @pytest.fixture
    def session_manager(self):
        """Create session manager for testing"""
        config = {
            'SECRET_KEY': 'test-secret-key',
            'SESSION_TIMEOUT': 3600
        }
        return SessionManager(config)

    def test_create_session(self, session_manager):
        """Test session creation"""
        session_id = session_manager.create_session("test_user_id", {"role": "user"})

        assert session_id is not None
        assert len(session_id) > 0

        # Verify session exists
        session_data = session_manager.get_session(session_id)
        assert session_data is not None
        assert session_data['user_id'] == "test_user_id"

    def test_get_nonexistent_session(self, session_manager):
        """Test getting non-existent session"""
        session_data = session_manager.get_session("nonexistent_session_id")
        assert session_data is None

    def test_session_timeout(self, session_manager):
        """Test session timeout"""
        # Create session manager with very short timeout
        short_timeout_manager = SessionManager({
            'SECRET_KEY': 'test-secret-key',
            'SESSION_TIMEOUT': 1  # 1 second
        })

        session_id = short_timeout_manager.create_session("test_user_id")

        # Session should exist immediately
        session_data = short_timeout_manager.get_session(session_id)
        assert session_data is not None

        # Wait for timeout
        time.sleep(1.1)

        # Session should be expired
        session_data = short_timeout_manager.get_session(session_id)
        assert session_data is None

    def test_invalidate_session(self, session_manager):
        """Test session invalidation"""
        session_id = session_manager.create_session("test_user_id")

        # Verify session exists
        assert session_manager.get_session(session_id) is not None

        # Invalidate session
        session_manager.invalidate_session(session_id)

        # Verify session is gone
        assert session_manager.get_session(session_id) is None

    def test_refresh_session(self, session_manager):
        """Test session refresh"""
        session_id = session_manager.create_session("test_user_id")

        # Get original expiry
        original_session = session_manager.sessions[session_id]
        original_expiry = original_session['expires_at']

        time.sleep(0.1)  # Small delay
        session_manager.refresh_session(session_id)

        # Verify expiry was updated
        refreshed_session = session_manager.sessions[session_id]
        assert refreshed_session['expires_at'] > original_expiry

class TestRateLimiter:
    """Test cases for RateLimiter"""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing"""
        return RateLimiter(max_requests=5, time_window=60)

    def test_allow_request_under_limit(self, rate_limiter):
        """Test allowing requests under the limit"""
        client_id = "test_client"

        for i in range(5):
            assert rate_limiter.is_allowed(client_id)

    def test_block_request_over_limit(self, rate_limiter):
        """Test blocking requests over the limit"""
        client_id = "test_client"

        # Use up the allowed requests
        for i in range(5):
            assert rate_limiter.is_allowed(client_id)

        # Next request should be blocked
        assert not rate_limiter.is_allowed(client_id)

    def test_different_clients_separate_limits(self, rate_limiter):
        """Test that different clients have separate limits"""
        client1 = "client_1"
        client2 = "client_2"

        # Use up limit for client1
        for i in range(5):
            assert rate_limiter.is_allowed(client1)

        # client1 should be blocked
        assert not rate_limiter.is_allowed(client1)

        # client2 should still be allowed
        assert rate_limiter.is_allowed(client2)

    def test_window_reset(self, rate_limiter):
        """Test that rate limit resets after time window"""
        # Create rate limiter with very short window
        short_limiter = RateLimiter(max_requests=2, time_window=1)
        client_id = "test_client"

        # Use up the limit
        assert short_limiter.is_allowed(client_id)
        assert short_limiter.is_allowed(client_id)
        assert not short_limiter.is_allowed(client_id)

        # Wait for window to reset
        time.sleep(1.1)

        # Should be allowed again
        assert short_limiter.is_allowed(client_id)

class TestInputValidator:
    """Test cases for InputValidator"""

    @pytest.fixture
    def validator(self):
        """Create input validator for testing"""
        return InputValidator()

    def test_validate_email_valid(self, validator):
        """Test validating valid email addresses"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "123@test-domain.org"
        ]

        for email in valid_emails:
            assert validator.validate_email(email)

    def test_validate_email_invalid(self, validator):
        """Test validating invalid email addresses"""
        invalid_emails = [
            "not_an_email",
            "@domain.com",
            "user@",
            "user name@domain.com",
            ""
        ]

        for email in invalid_emails:
            assert not validator.validate_email(email)

    def test_validate_password_strong(self, validator):
        """Test validating strong passwords"""
        strong_passwords = [
            "StrongPass123!",
            "MySecure_Password1",
            "Complex#Pass987"
        ]

        for password in strong_passwords:
            result = validator.validate_password(password)
            assert result['valid']

    def test_validate_password_weak(self, validator):
        """Test validating weak passwords"""
        weak_passwords = [
            "weak",
            "12345678",
            "password",
            "PASSWORD",
            "Pass1"  # Too short
        ]

        for password in weak_passwords:
            result = validator.validate_password(password)
            assert not result['valid']
            assert len(result['errors']) > 0

    def test_sanitize_input(self, validator):
        """Test input sanitization"""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "<img src=x onerror=alert(1)>"
        ]

        for input_text in malicious_inputs:
            sanitized = validator.sanitize_input(input_text)
            assert '<script>' not in sanitized.lower()
            assert 'drop table' not in sanitized.lower()
            assert 'onerror' not in sanitized.lower()

    def test_validate_filename(self, validator):
        """Test filename validation"""
        valid_filenames = [
            "document.pdf",
            "file_name.txt",
            "Report-2024.docx"
        ]

        invalid_filenames = [
            "../../../etc/passwd",
            "file\\with\\backslashes",
            "file<with>special|chars",
            ""
        ]

        for filename in valid_filenames:
            assert validator.validate_filename(filename)

        for filename in invalid_filenames:
            assert not validator.validate_filename(filename)

class TestCSRFProtection:
    """Test cases for CSRFProtection"""

    @pytest.fixture
    def csrf_protection(self):
        """Create CSRF protection for testing"""
        return CSRFProtection('test-secret-key')

    def test_generate_token(self, csrf_protection):
        """Test CSRF token generation"""
        token = csrf_protection.generate_token()
        assert token is not None
        assert len(token) > 0

    def test_validate_token_valid(self, csrf_protection):
        """Test validating valid CSRF token"""
        token = csrf_protection.generate_token()
        assert csrf_protection.validate_token(token)

    def test_validate_token_invalid(self, csrf_protection):
        """Test validating invalid CSRF token"""
        assert not csrf_protection.validate_token("invalid_token")
        assert not csrf_protection.validate_token("")
        assert not csrf_protection.validate_token(None)

    def test_token_expiry(self, csrf_protection):
        """Test that CSRF tokens expire"""
        # Create CSRF protection with short expiry
        short_expiry_csrf = CSRFProtection('test-secret', token_expiry=1)

        token = short_expiry_csrf.generate_token()
        assert short_expiry_csrf.validate_token(token)

        # Wait for expiry
        time.sleep(1.1)

        # Token should be invalid
        assert not short_expiry_csrf.validate_token(token)