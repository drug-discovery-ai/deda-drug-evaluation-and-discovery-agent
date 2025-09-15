"""FastAPI endpoints for API key management."""

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from drug_discovery_agent.key_storage.key_manager import APIKeyManager, StorageMethod
from drug_discovery_agent.key_storage.validation import APIKeyValidator
from drug_discovery_agent.settings.api_key.models import (
    DeleteKeyResponse,
    KeyStatusResponse,
    StoreKeyRequest,
    StoreKeyResponse,
    ValidateKeyRequest,
    ValidateKeyResponse,
)


class APIKeySettingsHandler:
    """Handles API key management endpoints."""

    def __init__(self) -> None:
        self.key_manager = APIKeyManager()
        self.validator = APIKeyValidator()
        self.logger = logging.getLogger(__name__)

    async def store_api_key(self, request: Request) -> JSONResponse:
        """Store an API key with validation.

        POST /api_key/api_key-key
        """
        try:
            body = await request.json()
            store_request = StoreKeyRequest(**body)

            # Validate the API key before storing
            is_valid, warnings, errors = self.validator.validate_for_storage(
                store_request.api_key
            )

            if not is_valid:
                return JSONResponse(
                    {
                        "success": False,
                        "message": f"Invalid API key: {'; '.join(errors)}",
                        "warnings": warnings,
                    },
                    status_code=400,
                )

            # Parse preferred method
            preferred_method = None
            if store_request.preferred_method:
                try:
                    preferred_method = StorageMethod(
                        store_request.preferred_method.lower()
                    )
                except ValueError:
                    return JSONResponse(
                        {
                            "success": False,
                            "message": f"Invalid storage method: {store_request.preferred_method}",
                        },
                        status_code=400,
                    )

            # Store the key
            success, method_used, error_msg = self.key_manager.store_api_key(
                store_request.api_key, preferred_method
            )

            if success:
                response = StoreKeyResponse(
                    success=True,
                    method_used=method_used.value,
                    message=f"API key stored successfully using {method_used.value}",
                    warnings=warnings if warnings else None,
                )
                self.logger.info(
                    f"API key stored successfully using {method_used.value}"
                )
            else:
                response = StoreKeyResponse(
                    success=False,
                    method_used="none",
                    message=error_msg or "Failed to store API key",
                )

            return JSONResponse(
                response.model_dump(), status_code=200 if success else 500
            )

        except Exception as e:
            self.logger.error(f"Error storing API key: {e}")
            return JSONResponse(
                {"success": False, "message": f"Internal error: {str(e)}"},
                status_code=500,
            )

    async def get_key_status(self, request: Request) -> JSONResponse:
        """Get API key status and storage information.

        GET /api_key/api_key-key/status
        """
        try:
            current_key, current_method = self.key_manager.get_api_key()
            storage_status = self.key_manager.get_storage_status()

            masked_key = None
            if current_key:
                masked_key = self.validator.mask_api_key(current_key)

            response = KeyStatusResponse(
                has_key=current_key is not None,
                source=current_method.value,
                masked_key=masked_key,
                storage_status=storage_status,
            )

            return JSONResponse(response.model_dump())

        except Exception as e:
            self.logger.error(f"Error getting key status: {e}")
            return JSONResponse({"error": f"Internal error: {str(e)}"}, status_code=500)

    async def delete_api_key(self, request: Request) -> JSONResponse:
        """Delete stored API key from all storage locations.

        DELETE /api_key/api_key-key
        """
        try:
            # Delete from all storage methods
            success, message = self.key_manager.delete_api_key()

            response = DeleteKeyResponse(success=success, message=message)

            if success:
                self.logger.info("API key deleted successfully")

            return JSONResponse(response.model_dump())

        except Exception as e:
            self.logger.error(f"Error deleting API key: {e}")
            return JSONResponse(
                {"success": False, "message": f"Internal error: {str(e)}"},
                status_code=500,
            )

    async def validate_api_key(self, request: Request) -> JSONResponse:
        """Validate an API key format without storing it.

        POST /api_key/api_key-key/validate
        """
        try:
            body = await request.json()
            validate_request = ValidateKeyRequest(**body)

            is_valid, warnings, errors = self.validator.validate_for_storage(
                validate_request.api_key
            )

            recommendations = []
            if is_valid:
                recommendations = self.validator.get_security_recommendations()

            response = ValidateKeyResponse(
                valid=is_valid,
                format_type="openai" if is_valid else "unknown",
                error_message="; ".join(errors) if errors else None,
                warnings=warnings if warnings else None,
                recommendations=recommendations if recommendations else None,
            )

            return JSONResponse(response.model_dump())

        except Exception as e:
            self.logger.error(f"Error validating API key: {e}")
            return JSONResponse({"error": f"Internal error: {str(e)}"}, status_code=500)

    async def update_api_key(self, request: Request) -> JSONResponse:
        """Update existing API key with a new one.

        PUT /api_key/api_key-key
        """
        try:
            body = await request.json()
            store_request = StoreKeyRequest(**body)

            # Validate the new API key
            is_valid, warnings, errors = self.validator.validate_for_storage(
                store_request.api_key
            )

            if not is_valid:
                return JSONResponse(
                    {
                        "success": False,
                        "message": f"Invalid API key: {'; '.join(errors)}",
                        "warnings": warnings,
                    },
                    status_code=400,
                )

            # Parse preferred method
            preferred_method = None
            if store_request.preferred_method:
                try:
                    preferred_method = StorageMethod(
                        store_request.preferred_method.lower()
                    )
                except ValueError:
                    return JSONResponse(
                        {
                            "success": False,
                            "message": f"Invalid storage method: {store_request.preferred_method}",
                        },
                        status_code=400,
                    )

            # Update the key
            success, method_used, error_msg = self.key_manager.update_api_key(
                store_request.api_key, preferred_method
            )

            if success:
                response = StoreKeyResponse(
                    success=True,
                    method_used=method_used.value,
                    message=f"API key updated successfully using {method_used.value}",
                    warnings=warnings if warnings else None,
                )
                self.logger.info(
                    f"API key updated successfully using {method_used.value}"
                )
            else:
                response = StoreKeyResponse(
                    success=False,
                    method_used="none",
                    message=error_msg or "Failed to update API key",
                )

            return JSONResponse(
                response.model_dump(), status_code=200 if success else 500
            )

        except Exception as e:
            self.logger.error(f"Error updating API key: {e}")
            return JSONResponse(
                {"success": False, "message": f"Internal error: {str(e)}"},
                status_code=500,
            )


def create_api_key_routes() -> list[Route]:
    """Create API key management routes.

    Returns:
        List of Route objects for API key management
    """
    handler = APIKeySettingsHandler()

    return [
        Route("/api/key", handler.store_api_key, methods=["POST"]),
        Route("/api/key", handler.update_api_key, methods=["PUT"]),
        Route("/api/key", handler.delete_api_key, methods=["DELETE"]),
        Route("/api/key/status", handler.get_key_status, methods=["GET"]),
        Route("/api/key/validate", handler.validate_api_key, methods=["POST"]),
    ]
