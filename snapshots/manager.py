"""Snapshot Manager for handling API response snapshots."""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse


class SnapshotManager:
    """Manages loading, saving, and organizing API response snapshots."""

    def __init__(self, base_dir: str = "snapshots"):
        """Initialize the snapshot manager.

        Args:
            base_dir: Base directory for storing snapshots
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

        # Create subdirectories for each API
        self._ensure_api_directories()

        # Load or create metadata file
        self.metadata_file = self.base_dir / "metadata.json"
        self.metadata = self._load_metadata()

    def _ensure_api_directories(self) -> None:
        """Create subdirectories for each API service."""
        api_dirs = ["ebi", "opentargets", "uniprot", "pdb", "misc"]
        for api_dir in api_dirs:
            (self.base_dir / api_dir).mkdir(exist_ok=True)

    def _load_metadata(self) -> dict[str, Any]:
        """Load snapshot metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, encoding="utf-8") as f:
                    return json.load(f)  # type: ignore[no-any-return]
            except (OSError, json.JSONDecodeError):
                pass

        # Return default metadata structure
        return {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "snapshots": {},
        }

    def _save_metadata(self) -> None:
        """Save metadata to file."""
        self.metadata["updated_at"] = datetime.utcnow().isoformat()
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

    def generate_key(
        self, url: str, method: str = "GET", params: dict | None = None
    ) -> str:
        """Generate a consistent key for a request.

        Args:
            url: The API endpoint URL
            method: HTTP method (GET, POST, etc.)
            params: Request parameters

        Returns:
            A unique key for this request
        """
        if params is None:
            params = {}

        # Parse URL to extract API service
        parsed_url = urlparse(url)

        # Determine API service from URL
        api_service = "misc"
        if "ebi.ac.uk" in parsed_url.netloc:
            api_service = "ebi"
        elif "opentargets.org" in parsed_url.netloc:
            api_service = "opentargets"
        elif "uniprot.org" in parsed_url.netloc:
            api_service = "uniprot"
        elif "rcsb.org" in parsed_url.netloc:
            api_service = "pdb"

        # Create a consistent string representation
        key_parts = [
            method.upper(),
            parsed_url.path,
            urlencode(sorted(params.items())) if params else "",
        ]
        key_string = "|".join(key_parts)

        # Create hash for filename
        key_hash = hashlib.md5(key_string.encode("utf-8")).hexdigest()[:16]

        # Create descriptive filename
        path_parts = parsed_url.path.strip("/").split("/")
        if path_parts and path_parts[0]:
            desc = "_".join(path_parts[-2:]) if len(path_parts) > 1 else path_parts[0]
        else:
            desc = "root"

        # Add parameter hint if present
        if params:
            param_hint = "_".join(str(v)[:10] for v in params.values())[:20]
            desc = f"{desc}_{param_hint}"

        # Clean filename
        desc = "".join(c for c in desc if c.isalnum() or c in "_-")[:50]

        return f"{api_service}_{desc}_{key_hash}"

    def load_snapshot(self, key: str) -> dict[str, Any] | None:
        """Load a snapshot by key.

        Args:
            key: The snapshot key

        Returns:
            Snapshot data if found, None otherwise
        """
        # Try to find the snapshot file
        snapshot_file = self._find_snapshot_file(key)
        if not snapshot_file:
            return None

        try:
            with open(snapshot_file, encoding="utf-8") as f:
                return json.load(f)  # type: ignore[no-any-return]
        except (OSError, json.JSONDecodeError):
            return None

    def save_snapshot(
        self, key: str, data: dict[str, Any], metadata: dict[str, Any]
    ) -> None:
        """Save a snapshot with metadata.

        Args:
            key: The snapshot key
            data: The API response data
            metadata: Request/response metadata
        """
        # Determine API service from key
        api_service = key.split("_")[0] if "_" in key else "misc"

        # Create snapshot structure
        snapshot = {
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "key": key,
                **metadata,
            },
            "response": data,
        }

        # Calculate checksum
        content_str = json.dumps(data, sort_keys=True)
        snapshot["metadata"]["checksum"] = hashlib.sha256(
            content_str.encode("utf-8")
        ).hexdigest()

        # Determine file extension based on content type
        content_type = metadata.get("content_type", "application/json")
        if "json" in content_type:
            ext = ".json"
        elif "text" in content_type or "fasta" in content_type:
            ext = ".txt"
        else:
            ext = ".json"  # Default to JSON

        # Save to appropriate directory
        snapshot_dir = self.base_dir / api_service
        snapshot_file = snapshot_dir / f"{key}{ext}"

        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        # Update global metadata
        self.metadata["snapshots"][key] = {
            "file": str(snapshot_file.relative_to(self.base_dir)),
            "created_at": snapshot["metadata"]["created_at"],
            "api_service": api_service,
            "url": metadata.get("url", ""),
            "checksum": snapshot["metadata"]["checksum"],
        }
        self._save_metadata()

    def get_snapshot_age(self, key: str) -> timedelta | None:
        """Get the age of a snapshot.

        Args:
            key: The snapshot key

        Returns:
            Age of the snapshot or None if not found
        """
        if key not in self.metadata["snapshots"]:
            return None

        created_at_str = self.metadata["snapshots"][key]["created_at"]
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            return datetime.utcnow().replace(tzinfo=created_at.tzinfo) - created_at
        except (ValueError, KeyError):
            return None

    def _find_snapshot_file(self, key: str) -> Path | None:
        """Find the snapshot file for a given key."""
        if key in self.metadata["snapshots"]:
            file_path = self.base_dir / self.metadata["snapshots"][key]["file"]
            if file_path.exists():
                return file_path  # type: ignore[no-any-return]

        # Fallback: search all directories - prefer .json files over .txt files
        for api_dir in self.base_dir.iterdir():
            if api_dir.is_dir() and api_dir.name != "__pycache__":
                # First try .json files (successful responses)
                json_file = api_dir / f"{key}.json"
                if json_file.exists():
                    return json_file

                # Then try .txt files (error responses or text content)
                txt_file = api_dir / f"{key}.txt"
                if txt_file.exists():
                    return txt_file

        return None

    def list_snapshots(
        self, api_service: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """List all snapshots, optionally filtered by API service.

        Args:
            api_service: Filter by API service (ebi, opentargets, uniprot, pdb)

        Returns:
            Dictionary of snapshot metadata
        """
        snapshots = self.metadata["snapshots"]
        if api_service:
            return {
                key: data
                for key, data in snapshots.items()
                if data.get("api_service") == api_service
            }
        return snapshots.copy()  # type: ignore[no-any-return]

    def delete_snapshot(self, key: str) -> bool:
        """Delete a snapshot.

        Args:
            key: The snapshot key

        Returns:
            True if deleted, False if not found
        """
        snapshot_file = self._find_snapshot_file(key)
        if snapshot_file and snapshot_file.exists():
            snapshot_file.unlink()

            # Remove from metadata
            if key in self.metadata["snapshots"]:
                del self.metadata["snapshots"][key]
                self._save_metadata()

            return True
        return False

    def cleanup_old_snapshots(self, max_age_days: int = 30) -> None:
        """Remove snapshots older than specified days.

        Args:
            max_age_days: Maximum age in days before deletion
        """
        max_age = timedelta(days=max_age_days)
        to_delete = []

        for key in self.metadata["snapshots"]:
            age = self.get_snapshot_age(key)
            if age and age > max_age:
                to_delete.append(key)

        for key in to_delete:
            self.delete_snapshot(key)
