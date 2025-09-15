"""OpenAI API key validation utilities."""

import logging
import re
from typing import Any


class APIKeyValidator:
    """Validates  key formats. Currently, only OpenAI keys are supported."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.pattern = re.compile(r"^sk-[a-zA-Z0-9_-]{20,}$")
        self.min_length = 23

    def is_valid_format(self, api_key: Any) -> bool:
        """Check if API key has a valid format.

        Args:
            api_key: The API key to validate

        Returns:
            True if the key format is valid, False otherwise
        """
        if not api_key or not isinstance(api_key, str):
            return False

        # Don't strip whitespace here - that should be an error
        # Check for whitespace first
        if api_key != api_key.strip():
            return False

        # Check minimum length
        if len(api_key) < self.min_length:
            return False

        # Check OpenAI pattern match
        return self.pattern.match(api_key) is not None

    def validate_openai_key(self, api_key: str) -> tuple[bool, str | None]:
        """Validate OpenAI API key.

        Args:
            api_key: The API key to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not api_key or not isinstance(api_key, str):
            return False, "API key must be a non-empty string"

        api_key = api_key.strip()

        if len(api_key) == 0:
            return False, "API key cannot be empty"

        if len(api_key) < self.min_length:
            return False, f"API key is too short (minimum {self.min_length} characters)"

        # Check for common issues
        if api_key.startswith(" ") or api_key.endswith(" "):
            return False, "API key contains leading or trailing whitespace"

        # Check for obviously invalid characters
        if any(char in api_key for char in ["\n", "\r", "\t"]):
            return False, "API key contains invalid characters"

        # Check OpenAI format
        if not self.pattern.match(api_key):
            return (
                False,
                "API key is not in valid OpenAI format (must start with 'sk-')",
            )

        return True, None

    def mask_api_key(self, api_key: str, show_chars: int = 4) -> str:
        """Mask API key for safe display.

        Args:
            api_key: The API key to mask
            show_chars: Number of characters to show at start and end

        Returns:
            Masked API key string
        """
        if not api_key or len(api_key) < (show_chars * 2):
            return "***invalid***"

        if len(api_key) <= show_chars * 2:
            return "*" * len(api_key)

        start = api_key[:show_chars]
        end = api_key[-show_chars:]
        middle_length = len(api_key) - (show_chars * 2)

        # For test compatibility, use exact number of stars for middle
        return f"{start}{'*' * middle_length}{end}"

    def get_security_recommendations(self) -> list[str]:
        """Get security recommendations for OpenAI API keys.

        Returns:
            List of security recommendations
        """
        return [
            "Never share your API key or commit it to version control",
            "Store the key securely using your operating system's keychain",
            "Rotate your API key regularly",
            "Monitor your API usage for unexpected activity",
            "Set usage limits in your OpenAI dashboard",
            "Monitor your OpenAI billing dashboard regularly",
            "Consider creating separate keys for different applications",
        ]

    def check_common_issues(self, api_key: str) -> list[str]:
        """Check for common API key issues.

        Args:
            api_key: The API key to check

        Returns:
            List of identified issues
        """
        issues = []

        if not api_key:
            issues.append("API key is empty")
            return issues

        # Check for common copy-paste issues
        if api_key.startswith('"') and api_key.endswith('"'):
            issues.append("API key appears to have quotes around it")

        if api_key.startswith("'") and api_key.endswith("'"):
            issues.append("API key appears to have quotes around it")

        if " " in api_key:
            issues.append("API key contains spaces")

        if "\n" in api_key or "\r" in api_key:
            issues.append("API key contains line breaks")

        if api_key != api_key.strip():
            issues.append("API key has leading or trailing whitespace")

        # Check for example/placeholder keys
        placeholder_patterns = [
            "your_api_key_here",
            "sk-example",
            "sk-test",
            "placeholder",
            "xxxxxxxx",
        ]

        api_key_lower = api_key.lower()
        for pattern in placeholder_patterns:
            if pattern in api_key_lower:
                issues.append("API key appears to be a placeholder or example")
                break

        return issues

    def validate_for_storage(self, api_key: str) -> tuple[bool, list[str], list[str]]:
        """Comprehensive validation for storing an OpenAI API key.

        Args:
            api_key: The API key to validate

        Returns:
            Tuple of (is_valid, warnings, errors)
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Basic validation
        is_valid, error_msg = self.validate_openai_key(api_key)

        if not is_valid:
            errors.append(error_msg or "Invalid API key format")
            return False, warnings, errors

        # Check for common issues
        issues = self.check_common_issues(api_key)
        if issues:
            warnings.extend(issues)

        # Length checks
        if len(api_key) < 32:
            warnings.append("API key is relatively short - ensure it's complete")

        if len(api_key) > 200:
            warnings.append("API key is unusually long - verify it's correct")

        return True, warnings, errors
