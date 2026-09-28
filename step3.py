"""
STEP 3 — Build the final graph outputs from the map-matched results.

Produces the same style of graph_nodes.csv / graph_edges.csv as before,
but now grounded in the REAL OpenStreetMap road network instead of
statistically guessed corners:

  - graph_nodes_final.csv : real intersections actually touched by your data
  - graph_edges_final.csv : real road edges, each listing which image_ids
                            belong to that road (this is your automatic
                            "which images belong to the same road" answer)

Install first:
    pip install osmnx networkx pandas

Usage:
    python step3_build_graph_outputs.py
"""

import osmnx as ox
import pandas as pd

# ---------------------------------------------------------------
GRAPHML_FILE = "local_road_network.graphml"
MATCHED_FILE = "matched_coordinates.csv"
NODES_OUT = "graph_nodes_final.csv"
EDGES_OUT = "graph_edges_final.csv"
# ---------------------------------------------------------------


def main():
    G = ox.load_graphml(GRAPHML_FILE)
    df = pd.read_csv(MATCHED_FILE)
    df = df.dropna(subset=["matched_edge_id"])

    if len(df) == 0:
        raise RuntimeError(
            f"No matched images found in {MATCHED_FILE} (matched_edge_id is empty "
            f"for every row). This means step2 failed to match anything — re-check "
            f"step2's output/diagnostic before re-running this script."
        )

    # --- Build edges: group images by matched_edge_id ---
    edge_rows = []
    for edge_id, group in df.groupby("matched_edge_id"):
        u_str, v_str = edge_id.split("_")
        u, v = int(u_str), int(v_str)
        road_name = group["road_name"].iloc[0] if group["road_name"].notna().any() else "unnamed road"

        group_sorted = group.sort_values("captured_at")
        edge_rows.append({
            "edge_id": edge_id,
            "from_node": u,
            "to_node": v,
            "road_name": road_name,
            "n_images": len(group),
            "image_ids": ";".join(group_sorted["image_id"].astype(str)),
        })

    edges_df = pd.DataFrame(edge_rows)
    edges_df.to_csv(EDGES_OUT, index=False)

    # --- Build nodes: only the real intersections actually touched ---
    touched_nodes = set(edges_df["from_node"]).union(set(edges_df["to_node"]))
    node_rows = []
    for n in touched_nodes:
        data = G.nodes[n]
        node_rows.append({
            "node_id": n,
            "latitude": data["y"],
            "longitude": data["x"],
        })
    nodes_df = pd.DataFrame(node_rows)
    nodes_df.to_csv(NODES_OUT, index=False)

    print(f"Final graph built from real OSM road network:")
    print(f"  Nodes (real intersections touched by your data): {len(nodes_df)}")
    print(f"  Edges (real roads with your images assigned): {len(edges_df)}")
    print(f"\nSaved: {NODES_OUT}, {EDGES_OUT}")
    print("\nPer-road image counts:")
    print(edges_df[["edge_id", "road_name", "n_images"]].to_string(index=False))
    print("\nNext: feed each edge's image_ids into the VQA questionnaire step.")


if __name__ == "__main__":
    main()