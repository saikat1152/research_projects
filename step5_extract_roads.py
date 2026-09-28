"""
STEP 5 (WORKSTEPS Step 7) — Extract each physical road from the final
road graph as a standalone, independently addressable unit.

This is a light re-shaping/validation pass over graph_edges_merged.csv +
graph_nodes_final.csv (Steps 4/3): every later stage (sorting, batching,
the VQ questionnaire) operates on one road at a time, so this formalizes
that unit once with its endpoint coordinates attached.

Usage:
    python step5_extract_roads.py
"""

import pandas as pd

NODES_FILE = "graph_nodes_final.csv"
EDGES_FILE = "graph_edges_merged.csv"
OUTPUT_ROADS = "roads_extracted.csv"


def main():
    nodes_df = pd.read_csv(NODES_FILE).set_index("node_id")
    edges_df = pd.read_csv(EDGES_FILE)

    rows = []
    for _, row in edges_df.iterrows():
        a, b = int(row["node_a"]), int(row["node_b"])
        node_a = nodes_df.loc[a]
        node_b = nodes_df.loc[b]
        rows.append({
            "road_id": row["road_id"],
            "road_name": row["road_name"],
            "node_a": a,
            "node_b": b,
            "lat_a": node_a["latitude"],
            "lon_a": node_a["longitude"],
            "lat_b": node_b["latitude"],
            "lon_b": node_b["longitude"],
            "n_images": row["n_images"],
            "image_ids": row["image_ids"],
        })

    roads_df = pd.DataFrame(rows)
    roads_df.to_csv(OUTPUT_ROADS, index=False)

    print(f"Extracted {len(roads_df)} roads from {EDGES_FILE}.")
    print(f"Saved to {OUTPUT_ROADS}")
    print("\nRoads:")
    print(roads_df[["road_id", "road_name", "n_images"]].to_string(index=False))
    print("\nNext: run step6_sort_images.py")


if __name__ == "__main__":
    main()
