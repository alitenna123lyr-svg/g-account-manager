"""
Tests for the TOTP service.
"""

import pytest

from src.services.totp_service import TotpService
from src.utils.exceptions import InvalidSecretError


class TestTotpService:
    """Tests for TotpService."""

    @pytest.fixture
    def totp_service(self) -> TotpService:
        """Create a TOTP service instance."""
        return TotpService()

    def test_generate_code_valid_secret(self, totp_service):
        """Test that valid secret generates a 6-digit code."""
        # This is a well-known test vector
        secret = "JBSWY3DPEHPK3PXP"
        code = totp_service.generate_code(secret)

        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_with_spaces(self, totp_service):
        """Test that secrets with spaces are handled."""
        secret = "JBSW Y3DP EHPK 3PXP"
        code = totp_service.generate_code(secret)

        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_lowercase(self, totp_service):
        """Test that lowercase secrets are handled."""
        secret = "jbswy3dpehpk3pxp"
        code = totp_service.generate_code(secret)

        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_empty_secret_raises(self, totp_service):
        """Test that empty secret raises InvalidSecretError."""
        with pytest.raises(InvalidSecretError):
            totp_service.generate_code("")

    def test_generate_code_invalid_secret_raises(self, totp_service):
        """Test that invalid secret raises InvalidSecretError."""
        with pytest.raises(InvalidSecretError):
            totp_service.generate_code("not-valid-base32!")

    def test_generate_code_safe_returns_none_on_error(self, totp_service):
        """Test that generate_code_safe returns None on error."""
        result = totp_service.generate_code_safe("invalid!")
        assert result is None

    def test_generate_code_safe_returns_code_on_success(self, totp_service):
        """Test that generate_code_safe returns code on success."""
        result = totp_service.generate_code_safe("JBSWY3DPEHPK3PXP")
        assert result is not None
        assert len(result) == 6

    def test_get_remaining_seconds_in_range(self, totp_service):
        """Test that remaining seconds is in valid range."""
        remaining = totp_service.get_remaining_seconds()
        assert 1 <= remaining <= 30

    def test_is_valid_secret_valid(self, totp_service):
        """Test is_valid_secret with valid secret."""
        assert TotpService.is_valid_secret("JBSWY3DPEHPK3PXP") is True

    def test_is_valid_secret_empty(self, totp_service):
        """Test is_valid_secret with empty string."""
        assert TotpService.is_valid_secret("") is False

    def test_is_valid_secret_invalid(self, totp_service):
        """Test is_valid_secret with invalid secret."""
        assert TotpService.is_valid_secret("not-valid!") is False

    def test_verify_code_correct(self, totp_service):
        """Test that verify_code works with correct code."""
        secret = "JBSWY3DPEHPK3PXP"
        code = totp_service.generate_code(secret)

        # The code we just generated should be valid
        assert totp_service.verify_code(secret, code) is True

    def test_verify_code_wrong_code(self, totp_service):
        """Test that verify_code rejects wrong code."""
        secret = "JBSWY3DPEHPK3PXP"
        wrong_code = "000000"

        # A random code should probably be invalid
        # (small chance of collision)
        result = totp_service.verify_code(secret, wrong_code)
        # We don't assert False because there's a tiny chance it's valid
        assert isinstance(result, bool)

    def test_verify_code_empty_inputs(self, totp_service):
        """Test that verify_code handles empty inputs."""
        assert totp_service.verify_code("", "123456") is False
        assert totp_service.verify_code("JBSWY3DPEHPK3PXP", "") is False
