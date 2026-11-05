"""BigQuery source query loading. SQL is kept beside its source adapter."""
from pathlib import Path

QUERY_DIR = Path(__file__).resolve().parent / "queries"


def load_query(name: str, **parameters: str) -> str:
    """Load a checked-in SQL template and substitute named values."""
    path = QUERY_DIR / f"{name}.sql"
    if path.parent != QUERY_DIR or not path.is_file():
        raise FileNotFoundError(f"BigQuery query not found: {name}")
    query = path.read_text(encoding="utf-8-sig")
    for key, value in parameters.items():
        query = query.replace("{{" + key + "}}", value)
    if "{{" in query:
        raise ValueError(f"Unresolved parameter in BigQuery query: {name}")
    return query
