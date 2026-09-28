"""Helper for recording Claude's in-session Step 10 answers.

Each answer script in this folder calls `append_batch(...)` once per batch.
Run from anywhere: paths resolve relative to the project root. Idempotent —
a batch already present in batch_ratings.csv is skipped, never duplicated.
"""

import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_FILE = os.path.join(ROOT, "VQA_questionnaire_final_overview.csv")
OUT_FILE = os.path.join(ROOT, "batch_ratings.csv")
HEADER = ["batch_id", "road_id", "road_name", "q_id", "col_id", "attribute",
          "answer_code", "answer_label", "confidence", "note"]

SCHEMA = {}
LABELS = {}  # q_id -> {code(int): label}
with open(SCHEMA_FILE, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["status"] != "defined":
            continue
        q = int(r["q_id"])
        SCHEMA[q] = (r["col_id"], r["attribute"])
        LABELS[q] = {int(c): l.strip() for c, l in
                     (p.split("=", 1) for p in r["class_labels"].split(" | "))}


def append_batch(batch_id, road_id, road_name, answers):
    """answers: dict q_id -> (code, confidence, note) — or the legacy
    (code, label, confidence, note). The label is always filled in from the
    schema; a code not in the schema raises. Use code '' for UNCLASSIFIABLE."""
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, newline="", encoding="utf-8") as f:
            if any(r["batch_id"] == batch_id for r in csv.DictReader(f)):
                print(f"{batch_id}: already in batch_ratings.csv, skipped")
                return
    rows = []
    for q_id in range(1, 42):
        col_id, attribute = SCHEMA[q_id]
        a = answers.get(q_id, ("", "low", "not answered"))
        code, conf, note = (a[0], a[-2], a[-1])
        label = "UNCLASSIFIABLE"
        if code != "":
            if code not in LABELS[q_id]:
                raise ValueError(f"q{q_id} {attribute}: invalid code {code}")
            label = LABELS[q_id][code]
        rows.append([batch_id, road_id, road_name, q_id, col_id, attribute,
                     code, label, conf, note])
    new_file = not os.path.exists(OUT_FILE)
    with open(OUT_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(HEADER)
        w.writerows(rows)
    print(f"{batch_id}: appended {len(rows)} rows")
