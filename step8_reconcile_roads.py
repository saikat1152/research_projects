"""
Step 10b - Reconcile batch-level answers into road-level ratings.

Input : batch_ratings.csv   (one row per batch x question, from the in-session
                             Claude answers; see vqa_answers/)
        image_batches.csv   (batch_size, used as the vote weight)
Output: road_ratings.csv    (one row per road x question)

Rule (v1, default proposed in .agents/TODO.md): per road and question, each
batch votes for its answer code with weight = batch_size (number of images the
answer is based on). UNCLASSIFIABLE batches (empty code) abstain. The winning
code is the one with the largest total weight; ties are broken by total
confidence weight (high=3, medium=2, low=1), then by the lowest code. If every
batch abstains, the road answer is UNCLASSIFIABLE. `agreement` is the winner's
share of the total vote weight, so low-agreement rows are easy to review.
"""

import csv
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
CONF_W = {"high": 3, "medium": 2, "low": 1}


def main():
    with open(os.path.join(ROOT, "image_batches.csv"), newline="", encoding="utf-8") as f:
        batch_size = {r["batch_id"]: int(r["batch_size"]) for r in csv.DictReader(f)}
    with open(os.path.join(ROOT, "batch_ratings.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    groups = defaultdict(list)  # (road_id, q_id) -> rows
    for r in rows:
        groups[(r["road_id"], int(r["q_id"]))].append(r)

    out = []
    for (road_id, q_id), rs in sorted(groups.items()):
        votes = defaultdict(lambda: [0, 0])  # code -> [image weight, confidence weight]
        labels = {}
        n_images = sum(batch_size[r["batch_id"]] for r in rs)
        for r in rs:
            if r["answer_code"] == "":
                continue
            code = int(r["answer_code"])
            votes[code][0] += batch_size[r["batch_id"]]
            votes[code][1] += CONF_W[r["confidence"]]
            labels[code] = r["answer_label"]
        head = rs[0]
        if votes:
            code = min(votes, key=lambda c: (-votes[c][0], -votes[c][1], c))
            voted = sum(v[0] for v in votes.values())
            agreement = round(votes[code][0] / voted, 2)
            answer = (code, labels[code])
        else:
            agreement, answer = 0, ("", "UNCLASSIFIABLE")
        out.append({
            "road_id": road_id, "road_name": head["road_name"], "q_id": q_id,
            "col_id": head["col_id"], "attribute": head["attribute"],
            "answer_code": answer[0], "answer_label": answer[1],
            "agreement": agreement, "n_batches": len(rs), "n_images": n_images,
        })

    path = os.path.join(ROOT, "road_ratings.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    roads = {o["road_id"] for o in out}
    split = sum(1 for o in out if o["agreement"] < 1 and o["n_batches"] > 1)
    print(f"road_ratings.csv: {len(out)} rows = {len(roads)} roads x 41 questions")
    print(f"{split} road-question pairs where batches disagreed (agreement < 1)")


if __name__ == "__main__":
    main()
