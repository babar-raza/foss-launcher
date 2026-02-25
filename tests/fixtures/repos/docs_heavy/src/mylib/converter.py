"""Format conversion utilities."""


def load(path: str):
    """Load a document from path."""
    raise NotImplementedError


def save(doc, path: str) -> None:
    """Save a document to path."""
    raise NotImplementedError


def convert(source: str, target: str) -> None:
    """Convert source file to target format."""
    doc = load(source)
    save(doc, target)
