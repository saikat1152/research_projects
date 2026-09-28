"""
STEP 7 (WORKSTEPS Step 9) — Batch each road's sorted images into groups
of up to 10.

This is the unit of work the VQ questionnaire step (Step 10) will be run
against: one AI call per batch, with that batch's images shown together.
A road with fewer than 10 images gets a single partial batch. Roads with
0 images cannot occur here since only touched edges make it into the
graph.

Usage:
    python step7_batch_images.py
"""

import math
import pandas as pd

BATCH_SIZE = 10
ROADS_FILE = "roads_sorted.csv"
OUTPUT_BATCHES = "image_batches.csv"


def main():
    roads_df = pd.read_csv(ROADS_FILE)

    rows = []
    for _, row in roads_df.iterrows():
        image_ids = [x for x in str(row["image_ids"]).split(";") if x]
        n_batches = math.ceil(len(image_ids) / BATCH_SIZE)
        for b in range(n_batches):
            batch_images = image_ids[b * BATCH_SIZE:(b + 1) * BATCH_SIZE]
            rows.append({
                "road_id": row["road_id"],
                "road_name": row["road_name"],
                "batch_id": f"{row['road_id']}_b{b + 1}",
                "batch_index": b + 1,
                "batch_size": len(batch_images),
                "image_ids": ";".join(batch_images),
            })

    batches_df = pd.DataFrame(rows)
    batches_df.to_csv(OUTPUT_BATCHES, index=False)

    n_partial = (batches_df["batch_size"] < BATCH_SIZE).sum()
    print(f"Built {len(batches_df)} batches across {roads_df.shape[0]} roads "
          f"({n_partial} partial batches with < {BATCH_SIZE} images).")
    print(f"Saved to {OUTPUT_BATCHES}")
    print("\nBatches per road:")
    print(batches_df.groupby(["road_id", "road_name"]).size()
          .rename("n_batches").reset_index().to_string(index=False))
    print("\nNext: run step8_vq_questionnaire.py")


if __name__ == "__main__":
    main()
