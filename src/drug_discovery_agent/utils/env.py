"""Environment variable loading utilities for bundled and development environments."""

import sys
from pathlib import Path

from dotenv import load_dotenv


def load_env_for_bundle() -> None:
    """Load environment variables from .env file.

    For bundled applications (PyInstaller), searches in the executable directory
    and Resources directory. For development, uses standard dotenv loading.
    """
    if getattr(sys, "frozen", False):
        # Running in a PyInstaller bundle
        bundle_dir = Path(sys.executable).parent
        possible_env_paths = [
            bundle_dir / ".env",
            bundle_dir.parent / ".env",  # Parent directory (for Electron app structure)
            bundle_dir.parent / "Resources" / ".env",  # For macOS app bundles
            bundle_dir.parent.parent
            / "Resources"
            / ".env",  # For nested python-backend structure
        ]
        for env_path in possible_env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                print(f"Loaded environment from: {env_path}")  # Debug info
                break
        else:
            print(
                f"No .env file found. Searched paths: {[str(p) for p in possible_env_paths]}"
            )
    else:
        # Running in development
        load_dotenv()
