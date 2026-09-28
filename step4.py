"""
STEP 4 — Merge bidirectional edge pairs into single physical roads.

OSM represents two-way streets as two separate directed edges (u->v and
v->u). For rating purposes, both directions are the same physical road
(unless it's a genuinely divided/dual carriageway, which iRAP treats
separately via the "Carriageway A/B" attribute — not the common case
for ordinary two-way streets). This merges u_v and v_u pairs together
so each physical road gets one combined set of images.

Usage:
    python step4_merge_bidirectional.py
"""

import pandas as pd

EDGES_IN = "graph_edges_final.csv"
EDGES_OUT = "graph_edges_merged.csv"


def main():
    df = pd.read_csv(EDGES_IN)

    # canonical (undirected) key: sorted node pair, so u_v and v_u land together
    df["canonical_key"] = df.apply(
        lambda r: tuple(sorted([r["from_node"], r["to_node"]])), axis=1
    )

    merged_rows = []
    for key, group in df.groupby("canonical_key"):
        u, v = key
        # prefer a real road name over "unnamed road" if either direction has one
        names = [n for n in group["road_name"] if n and n != "unnamed road"]
        road_name = names[0] if names else "unnamed road"

        all_image_ids = ";".join(group["image_ids"].astype(str))
        total_images = group["n_images"].sum()

        merged_rows.append({
            "road_id": f"{u}_{v}",
            "node_a": u,
            "node_b": v,
            "road_name": road_name,
            "n_images": total_images,
            "n_directions_merged": len(group),
            "image_ids": all_image_ids,
        })

    out_df = pd.DataFrame(merged_rows).sort_values("n_images", ascending=False)
    out_df.to_csv(EDGES_OUT, index=False)

    n_merged = (out_df["n_directions_merged"] > 1).sum()
    print(f"Merged {len(df)} directed edges into {len(out_df)} physical roads "
          f"({n_merged} were bidirectional pairs merged into one).")
    print(f"Saved to {EDGES_OUT}\n")
    print(out_df[["road_id", "road_name", "n_images", "n_directions_merged"]].to_string(index=False))
    print("\nThis is your final per-road image grouping — ready for the VQA questionnaire step.")


if __name__ == "__main__":
    main()