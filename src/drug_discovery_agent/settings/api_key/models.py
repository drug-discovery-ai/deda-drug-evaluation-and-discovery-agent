"""Pydantic models for API key management."""

from pydantic import BaseModel, Field


class StoreKeyRequest(BaseModel):
    """Request model for storing an API key."""

    api_key: str = Field(..., min_length=1, description="The API key to store")
    preferred_method: str | None = Field(
        None, description="Preferred storage method: 'keychain' or 'encrypted_file'"
    )


class StoreKeyResponse(BaseModel):
    """Response model for store key operation."""

    success: bool
    method_used: str
    message: str
    warnings: list[str] | None = None


class KeyStatusResponse(BaseModel):
    """Response model for key status check."""

    has_key: bool
    source: str
    masked_key: str | None = None
    storage_status: dict


class DeleteKeyResponse(BaseModel):
    """Response model for delete key operation."""

    success: bool
    message: str


class ValidateKeyRequest(BaseModel):
    """Request model for key validation."""

    api_key: str = Field(..., min_length=1, description="The API key to validate")


class ValidateKeyResponse(BaseModel):
    """Response model for key validation."""

    valid: bool
    format_type: str
    error_message: str | None = None
    warnings: list[str] | None = None
    recommendations: list[str] | None = None
