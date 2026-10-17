"""Load the crawler corpus while preferring its cleaned structured files."""

from pathlib import Path


def _is_citation_or_metadata_file(file_path):
    """Return True for crawler artifacts that are not knowledge documents."""
    stem = file_path.stem.lower()
    return (
        "citation" in stem
        or "crawler_metadata" in stem
        or "crawl_metadata" in stem
    )


def should_load_file(file_path):
    """Apply the corpus selection policy to one .txt file."""
    if _is_citation_or_metadata_file(file_path):
        return False

    stem = file_path.stem
    if not stem.endswith("_structured"):
        structured_version = file_path.with_name(f"{stem}_structured.txt")
        if structured_version.exists():
            return False
    return True


def load_documents(data_dir="scraped_data"):
    """Return selected crawler documents with source and category metadata."""
    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"Scraped data directory not found: {root}")

    documents = []
    for file_path in sorted(root.rglob("*.txt")):
        if not should_load_file(file_path):
            continue

        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        documents.append({
            "content": content,
            "source": str(file_path),
            "category": file_path.parent.name,
            "document_name": file_path.name,
        })
    return documents


if __name__ == "__main__":
    print(f"Documents selected: {len(load_documents())}")
