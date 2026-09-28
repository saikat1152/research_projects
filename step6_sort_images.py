"""
STEP 6 (WORKSTEPS Step 8) — Sort the images for each road.

Orders each road's image list into a coherent sequence, using
captured_at (chronological capture order) as the default sort key. For a
single walked/driven pass this approximates travel order along the road.
If a road was captured in multiple passes/directions and the result
looks visibly out of order on review, revisit this to sort spatially
instead (project each image onto the road edge and sort by distance-
along-edge).

Usage:
    python step6_sort_images.py
"""

import pandas as pd

ROADS_FILE = "roads_extracted.csv"
COORDS_FILE = "coordinates.csv"
OUTPUT_ROADS = "roads_sorted.csv"


def main():
    roads_df = pd.read_csv(ROADS_FILE)
    coords_df = pd.read_csv(COORDS_FILE).set_index("image_id")

    for i, row in roads_df.iterrows():
        image_ids = [int(x) for x in str(row["image_ids"]).split(";") if x]
        image_ids.sort(key=lambda img_id: coords_df.loc[img_id, "captured_at"])
        roads_df.at[i, "image_ids"] = ";".join(str(x) for x in image_ids)

    roads_df.to_csv(OUTPUT_ROADS, index=False)

    print(f"Sorted images (by captured_at) for {len(roads_df)} roads.")
    print(f"Saved to {OUTPUT_ROADS}")
    print("\nNext: run step7_batch_images.py")


if __name__ == "__main__":
    main()
