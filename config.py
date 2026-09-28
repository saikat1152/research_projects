"""Shared config helpers: secrets from the environment, coordinates.csv merging.

The Mapillary token is read from the MAPILLARY_ACCESS_TOKEN environment
variable, or from a gitignored `.env` file in the project root containing a
line `MAPILLARY_ACCESS_TOKEN=...` (see `.env.example`).
"""

import csv
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
COORDS_FILE = os.path.join(ROOT, "coordinates.csv")
COORDS_FIELDS = [
    "image_id", "filename", "latitude", "longitude",
    "computed_latitude", "computed_longitude",
    "compass_angle", "captured_at",
]


def _load_dotenv(path=os.path.join(ROOT, ".env")):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def get_access_token():
    _load_dotenv()
    token = os.environ.get("MAPILLARY_ACCESS_TOKEN")
    if not token:
        raise SystemExit(
            "MAPILLARY_ACCESS_TOKEN is not set. Export it, or put it in a "
            ".env file in the project root (see .env.example)."
        )
    return token


def merge_coordinates(new_rows, path=COORDS_FILE):
    """Merge `new_rows` (list of dicts keyed by COORDS_FIELDS) into the
    coordinates CSV, deduplicating by image_id. New rows win over existing
    ones. Returns (rows_before, rows_after)."""
    merged = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                merged[row["image_id"]] = row
    before = len(merged)
    for row in new_rows:
        merged[str(row["image_id"])] = {k: row.get(k) for k in COORDS_FIELDS}
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COORDS_FIELDS)
        writer.writeheader()
        writer.writerows(merged.values())
    return before, len(merged)
