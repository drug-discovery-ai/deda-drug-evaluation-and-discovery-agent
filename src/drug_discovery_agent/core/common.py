import hashlib


def make_hash(value: str) -> str:
    """Create a short hash from ontology ID or other string."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]
