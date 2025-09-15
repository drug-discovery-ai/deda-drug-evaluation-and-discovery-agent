"""Tests for API key validation utilities."""

from drug_discovery_agent.key_storage.validation import APIKeyValidator


class TestAPIKeyValidator:
    """Test cases for APIKeyValidator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.validator = APIKeyValidator()

    def test_valid_openai_keys(self) -> None:
        """Test validation of valid OpenAI API keys."""
        valid_keys = [
            "sk-1234567890abcdefghijklmnop",
            "sk-abcdefghijklmnopqrstuvwxyz123456",
            "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
            "sk-123456789012345678901234567890",
        ]

        for key in valid_keys:
            assert self.validator.is_valid_format(key), f"Key should be valid: {key}"
            is_valid, error = self.validator.validate_openai_key(key)
            assert is_valid, f"Key should be valid: {key}, error: {error}"

    def test_invalid_keys(self) -> None:
        """Test validation of invalid API keys."""
        invalid_keys = [
            "",  # Empty
            "short",  # Too short
            "sk-",  # Incomplete OpenAI key
            "sk-short",  # Too short OpenAI key
            "invalid key with spaces",  # Contains spaces
            "invalid@key#with$symbols",  # Invalid characters
            None,  # None value
            123,  # Non-string
            "not-sk-prefix1234567890",  # Wrong prefix
        ]

        for key in invalid_keys:
            assert not self.validator.is_valid_format(key), (
                f"Key should be invalid: {key}"
            )
            if isinstance(key, str):
                is_valid, error = self.validator.validate_openai_key(key)
                assert not is_valid, f"Key should be invalid: {key}"
                assert error is not None, f"Should have error message for: {key}"

    def test_mask_api_key(self) -> None:
        """Test API key masking functionality."""
        # Standard masking
        key = "sk-1234567890abcdefghijklmnop"
        masked = self.validator.mask_api_key(key)
        assert masked.startswith("sk-1")
        assert masked.endswith("mnop")
        assert "*" in masked

        # Short key
        short_key = "short"
        masked_short = self.validator.mask_api_key(short_key)
        assert masked_short == "***invalid***"

        # Custom show_chars
        masked_custom = self.validator.mask_api_key(key, show_chars=2)
        assert masked_custom.startswith("sk")
        assert masked_custom.endswith("op")

    def test_security_recommendations(self) -> None:
        """Test security recommendations."""
        recommendations = self.validator.get_security_recommendations()
        assert len(recommendations) > 0
        assert any("Never share" in rec for rec in recommendations)
        assert any("keychain" in rec for rec in recommendations)

    def test_check_common_issues(self) -> None:
        """Test detection of common API key issues."""
        # Key with quotes
        issues = self.validator.check_common_issues('"sk-1234567890abcdefghijklmnop"')
        assert any("quotes" in issue for issue in issues)

        # Key with spaces
        issues = self.validator.check_common_issues("sk-123 456")
        assert any("spaces" in issue for issue in issues)

        # Key with line breaks
        issues = self.validator.check_common_issues("sk-123\n456")
        assert any("line breaks" in issue for issue in issues)

        # Placeholder key
        issues = self.validator.check_common_issues("your_api_key_here")
        assert any("placeholder" in issue for issue in issues)

        # Valid key should have no issues
        issues = self.validator.check_common_issues("sk-1234567890abcdefghijklmnop")
        assert len(issues) == 0

    def test_validate_for_storage(self) -> None:
        """Test comprehensive validation for storage."""
        # Valid key
        valid, warnings, errors = self.validator.validate_for_storage(
            "sk-1234567890abcdefghijklmnop"
        )
        assert valid
        assert len(errors) == 0

        # Invalid key
        valid, warnings, errors = self.validator.validate_for_storage("invalid")
        assert not valid
        assert len(errors) > 0

        # Key with warnings but still invalid due to quotes
        valid, warnings, errors = self.validator.validate_for_storage(
            '"sk-1234567890abcdefghijklmnop"'
        )
        assert not valid  # Should be invalid due to quotes
        assert len(errors) > 0

    def test_whitespace_handling(self) -> None:
        """Test handling of whitespace in API keys."""
        base_key = "sk-1234567890abcdefghijklmnop"

        # Leading whitespace
        assert not self.validator.is_valid_format(f" {base_key}")

        # Trailing whitespace
        assert not self.validator.is_valid_format(f"{base_key} ")

        # Internal whitespace
        assert not self.validator.is_valid_format("sk-123 456 789")

        # Mixed whitespace
        assert not self.validator.is_valid_format(f" {base_key} ")

    def test_none_and_type_safety(self) -> None:
        """Test handling of None values and type safety."""
        # None input
        assert not self.validator.is_valid_format(None)

        # Non-string input
        assert not self.validator.is_valid_format(123)
        assert not self.validator.is_valid_format([])
        assert not self.validator.is_valid_format({})

        # Boolean input
        assert not self.validator.is_valid_format(True)
        assert not self.validator.is_valid_format(False)

    def test_edge_cases(self) -> None:
        """Test edge cases and boundary conditions."""
        # Minimum length key for OpenAI (sk- + 20 chars = 23 minimum)
        min_key = "sk-12345678901234567890"  # exactly 23 chars
        assert self.validator.is_valid_format(min_key)

        # Just under minimum
        under_min = "sk-1234567890123456789"  # 22 chars
        assert not self.validator.is_valid_format(under_min)

        # Maximum reasonable length
        max_key = "sk-" + "a" * 197  # 200 chars total
        assert self.validator.is_valid_format(max_key)

        # Unicode characters in OpenAI key
        unicode_key = "sk-ñáéíóúüç1234567890"
        # Should be invalid due to special characters not matching pattern
        assert not self.validator.is_valid_format(unicode_key)

        # Mixed case for OpenAI-style key
        mixed_case = "sK-AbCdEfGhIjKlMnOpQrStUv"
        # Should be invalid as OpenAI keys should start with lowercase 'sk-'
        assert not self.validator.is_valid_format(mixed_case)
