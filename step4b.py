"""
STEP 4b — Build and visualize the final area road-network graph.

Combines graph_nodes_final.csv + graph_edges_merged.csv (from Steps 3-4)
into one proper graph object, and produces:

  1. final_area_graph.graphml  — a real, reusable graph file (nodes =
     confirmed real intersections, edges = merged physical roads with
     their image counts) that you can reopen with networkx/Gephi/etc.
  2. final_area_map.html       — an interactive map (open in any browser)
     showing the actual road network: each road colored/thickened by
     how many images cover it, with a popup showing its name and count.

This is the concrete "graph" checkpoint before running the VQA step —
a good sanity check and a presentable artifact on its own.

Install first:
    pip install networkx folium pandas

Usage:
    python step4b_build_final_graph.py
"""

import pandas as pd
import networkx as nx
import folium

NODES_FILE = "graph_nodes_final.csv"
EDGES_FILE = "graph_edges_merged.csv"
GRAPHML_OUT = "final_area_graph.graphml"
MAP_OUT = "final_area_map.html"


def main():
    nodes_df = pd.read_csv(NODES_FILE)
    edges_df = pd.read_csv(EDGES_FILE)

    # --- Build the networkx graph object ---
    G = nx.Graph()
    for _, row in nodes_df.iterrows():
        G.add_node(int(row["node_id"]), lat=row["latitude"], lon=row["longitude"])

    for _, row in edges_df.iterrows():
        G.add_edge(
            int(row["node_a"]), int(row["node_b"]),
            road_id=row["road_id"],
            road_name=row["road_name"],
            n_images=int(row["n_images"]),
        )

    print(f"Graph assembled: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    nx.write_graphml(G, GRAPHML_OUT)
    print(f"Saved graph object to {GRAPHML_OUT}")

    # --- Build an interactive map ---
    center_lat = nodes_df["latitude"].mean()
    center_lon = nodes_df["longitude"].mean()
    # NOTE: both the default OpenStreetMap tiles AND CartoDB tiles now
    # require registration/API keys or enforce bot-blocking that breaks in
    # this kind of automated/offline usage. Rather than chase another
    # provider, we skip the background map tile entirely (tiles=None) —
    # the roads and nodes still render perfectly on a plain background,
    # with zero dependency on any external tile service.
    m = folium.Map(location=[center_lat, center_lon], zoom_start=18, tiles=None)

    max_images = edges_df["n_images"].max()

    for _, row in edges_df.iterrows():
        a = G.nodes[int(row["node_a"])]
        b = G.nodes[int(row["node_b"])]
        weight = 2 + 8 * (row["n_images"] / max_images)  # thicker line = more images
        folium.PolyLine(
            locations=[(a["lat"], a["lon"]), (b["lat"], b["lon"])],
            color="#2E74B5",
            weight=weight,
            opacity=0.8,
            tooltip=f"{row['road_name']} — {row['n_images']} images",
        ).add_to(m)

    for node_id, data in G.nodes(data=True):
        folium.CircleMarker(
            location=(data["lat"], data["lon"]),
            radius=5,
            color="#F2B705",
            fill=True,
            fill_color="#F2B705",
            fill_opacity=1,
            tooltip=f"Node {node_id}",
        ).add_to(m)

    m.save(MAP_OUT)
    print(f"Saved interactive map to {MAP_OUT} — open it in a browser to inspect.")

    # --- Offline backup: a static plot needing NO internet/tile server at all ---
    build_offline_plot(G, nodes_df, edges_df)

    print("\nRoads in this graph:")
    print(edges_df[["road_id", "road_name", "n_images"]].sort_values("n_images", ascending=False).to_string(index=False))


def build_offline_plot(G, nodes_df, edges_df):
    """Guaranteed-to-work static visualization — no tile server, no internet
    needed at all. Use this if the interactive map's tiles are ever blocked."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 9))
    max_images = edges_df["n_images"].max()

    for _, row in edges_df.iterrows():
        a = G.nodes[int(row["node_a"])]
        b = G.nodes[int(row["node_b"])]
        lw = 1 + 6 * (row["n_images"] / max_images)
        ax.plot([a["lon"], b["lon"]], [a["lat"], b["lat"]], color="#2E74B5", linewidth=lw, zorder=1)
        mid_lon = (a["lon"] + b["lon"]) / 2
        mid_lat = (a["lat"] + b["lat"]) / 2
        ax.annotate(f"{row['road_name']}\n({row['n_images']} imgs)",
                    (mid_lon, mid_lat), fontsize=7, ha="center", color="#333333")

    for node_id, data in G.nodes(data=True):
        ax.scatter(data["lon"], data["lat"], color="#F2B705", edgecolor="#8a6d00", s=80, zorder=2)

    ax.set_title("Area Road Network (offline plot — no map tiles)", fontsize=13)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")
    plt.tight_layout()
    plt.savefig("final_area_plot.png", dpi=150)
    print("Saved offline static plot to final_area_plot.png (works with zero internet access)")


if __name__ == "__main__":
    main()