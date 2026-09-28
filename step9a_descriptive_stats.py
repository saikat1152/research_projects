"""
Step 11a - Assumption-free descriptive statistics of the VQ ratings.

No risk values, weights or thresholds are used here: only counts and shares of
the answers already in batch_ratings.csv / road_ratings.csv. A scored rating
(iRAP Star Rating Score) needs the published iRAP risk factors and equations
and is deliberately NOT computed here.

Outputs
  road_attribute_matrix.csv  one row per road, one column per attribute
                             (answer labels) - the "wide" view of road_ratings.csv
  attribute_summary.csv      one row per attribute: distinct answers, modal
                             answer and its share across roads, mean vote
                             agreement, share of low-confidence batch answers,
                             share of unclassifiable batch answers
"""

import os

import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    roads = pd.read_csv(os.path.join(ROOT, "road_ratings.csv"), dtype={"answer_code": str})
    batches = pd.read_csv(os.path.join(ROOT, "batch_ratings.csv"), dtype={"answer_code": str})

    # wide matrix: rows = roads, columns = "q<id> <attribute>"
    roads["col"] = "q" + roads.q_id.astype(str).str.zfill(2) + " " + roads.attribute
    wide = roads.pivot(index=["road_id", "road_name", "n_images"], columns="col", values="answer_label")
    wide.reset_index().to_csv(os.path.join(ROOT, "road_attribute_matrix.csv"), index=False, encoding="utf-8")

    rows = []
    for (q, attr), g in roads.groupby(["q_id", "attribute"]):
        counts = g.answer_label.value_counts()
        b = batches[batches.q_id == q]
        rows.append({
            "q_id": q,
            "attribute": attr,
            "distinct_answers_across_roads": g.answer_label.nunique(),
            "varies_between_roads": g.answer_label.nunique() > 1,
            "modal_answer": counts.index[0],
            "modal_share_of_roads": round(counts.iloc[0] / len(g), 2),
            "answer_counts": "; ".join(f"{k} x{v}" for k, v in counts.items()),
            "mean_vote_agreement": round(g.agreement.mean(), 2),
            "batch_low_confidence_share": round((b.confidence == "low").mean(), 2),
            "batch_unclassifiable_share": round((b.answer_code.isna() | (b.answer_code == "")).mean(), 2),
        })
    summ = pd.DataFrame(rows)
    summ.to_csv(os.path.join(ROOT, "attribute_summary.csv"), index=False, encoding="utf-8")

    n_var = int(summ.varies_between_roads.sum())
    print(f"road_attribute_matrix.csv : {wide.shape[0]} roads x {wide.shape[1]} attributes")
    print(f"attribute_summary.csv     : {len(summ)} attributes, {n_var} vary between roads, "
          f"{len(summ) - n_var} identical on every road")


if __name__ == "__main__":
    main()
