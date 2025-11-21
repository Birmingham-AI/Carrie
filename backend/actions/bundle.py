import json
import re
from pathlib import Path
from typing import List, Dict, Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"
BUNDLED_DIR = EMBEDDINGS_DIR / "bundled"

EMBED_FILE_PATTERN = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{1,2})-meeting-embed\.json$")
BUNDLE_FILE_PATTERN = re.compile(r"^bundle-(\d+)\.json$")


def ensure_directories() -> None:
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    BUNDLED_DIR.mkdir(parents=True, exist_ok=True)


def next_bundle_index() -> int:
    existing = [BUNDLE_FILE_PATTERN.match(path.name) for path in BUNDLED_DIR.glob("bundle-*.json")]
    indices = [int(match.group(1)) for match in existing if match]
    return max(indices, default=0) + 1


def load_embeddings() -> List[Dict[str, Any]]:
    combined: List[Dict[str, Any]] = []
    for path in sorted(EMBEDDINGS_DIR.glob("*-meeting-embed.json")):
        if path.parent == BUNDLED_DIR:
            continue

        match = EMBED_FILE_PATTERN.match(path.name)
        if not match:
            continue

        year = int(match.group("year"))
        month = int(match.group("month"))

        with path.open("r", encoding="utf-8") as file:
            records = json.load(file)

        for record in records:
            record["year"] = year
            record["month"] = month
            combined.append(record)

    return combined


def write_bundle(records: List[Dict[str, Any]]) -> Path:
    if not records:
        raise ValueError("No embeddings found to bundle.")

    bundle_idx = next_bundle_index()
    output_path = BUNDLED_DIR / f"bundle-{bundle_idx}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

    return output_path


def main() -> Path:
    ensure_directories()
    records = load_embeddings()
    return write_bundle(records)


if __name__ == "__main__":
    bundle_path = main()
    print(f"Bundled embeddings written to {bundle_path}")
