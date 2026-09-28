"""
STEP 2 (diagnostic version) — Map-match every image onto the real OSM
road network, with a built-in diagnostic pass first.

Before running the full HMM matcher, this script checks the straight-
line distance from every image's GPS point to the NEAREST real road
edge in your graph, using osmnx's own nearest_edges function. This
tells us definitively whether the problem is:

  (a) your OSM export doesn't actually cover the walked area well
      (distances will be large, e.g. >100m), or
  (b) the HMM matcher's parameters just need adjusting
      (distances will be small, e.g. <30m, but HMM still fails)

If the full HMM matcher (leuvenmapmatching) still matches too few
points after this diagnostic, the script automatically falls back to
a simpler nearest-edge-per-point assignment, so you have a usable
result today. This fallback is less robust than proper HMM matching
(it can be fooled by parallel roads/intersections) but is far better
than nothing while we tune the HMM parameters.

Install first:
    pip install leuvenmapmatching rtree osmnx networkx pandas

Usage:
    python step2_map_match.py
"""

import osmnx as ox
import pandas as pd
import numpy as np
import pyproj
from leuvenmapmatching.map.inmem import InMemMap
from leuvenmapmatching.matcher.distance import DistanceMatcher

# ---------------------------------------------------------------
GRAPHML_FILE = "local_road_network.graphml"
COORDS_FILE = "coordinates.csv"
OUTPUT_MATCHED = "matched_coordinates.csv"

MAX_DIST = 100        # meters
OBS_NOISE = 30         # meters
MIN_PROB_NORM = 0.3
# ---------------------------------------------------------------


def build_map_from_osm(G):
    map_con = InMemMap("osm", use_latlon=True, use_rtree=True, index_edges=True)
    for node, data in G.nodes(data=True):
        map_con.add_node(node, (data["y"], data["x"]))
    for u, v, data in G.edges(data=True):
        map_con.add_edge(u, v)
        map_con.add_edge(v, u)
    return map_con


def run_distance_diagnostic(G, df):
    """Check real distance (in meters) from each point to the nearest actual road edge.

    IMPORTANT: osmnx graphs loaded via graph_from_xml are in unprojected
    lat/lon (EPSG:4326). Calling nearest_edges directly on that returns
    distances in DEGREES, not meters (a degree of longitude is ~111km,
    so this silently makes every distance look tiny/fine even when it
    isn't). We project the graph and the query points into a metric CRS
    first so the meter-based thresholds below are actually meaningful.
    """
    print("\n--- DIAGNOSTIC: distance from each image to nearest real road ---")
    try:
        G_proj = ox.project_graph(G)
        transformer = pyproj.Transformer.from_crs(
            "epsg:4326", G_proj.graph["crs"], always_xy=True
        )
        x_proj, y_proj = transformer.transform(df["longitude"].values, df["latitude"].values)
        nearest_edges, dists = ox.distance.nearest_edges(
            G_proj, X=x_proj, Y=y_proj, return_dist=True
        )
    except Exception as e:
        print(f"  Could not run nearest_edges diagnostic: {e}")
        return None

    dists = np.array(dists)
    print(f"  Min distance:    {dists.min():.1f} m")
    print(f"  Mean distance:   {dists.mean():.1f} m")
    print(f"  Median distance: {np.median(dists):.1f} m")
    print(f"  Max distance:    {dists.max():.1f} m")
    n_far = (dists > 50).sum()
    print(f"  Points farther than 50m from any road: {n_far}/{len(dists)}")

    if dists.mean() > 80:
        print("\n  DIAGNOSIS: your images are, on average, VERY far from any road in")
        print("  your OSM export. This points to incomplete OSM coverage for this")
        print("  area, or a bbox mismatch between your export and your data.")
        print("  Fix: re-check the bbox used in your Overpass Turbo query against")
        print("  the bbox printed by step1, and make sure it fully contains your data.")
    elif dists.mean() > 30:
        print("\n  DIAGNOSIS: moderate distances — likely just needs looser HMM")
        print("  parameters (MAX_DIST/OBS_NOISE raised). Proceeding with that.")
    else:
        print("\n  DIAGNOSIS: distances look reasonable. If HMM still fails, it's")
        print("  likely a matcher configuration issue, not a data coverage issue.")

    return nearest_edges, dists


def try_hmm_match(map_con, track):
    matcher = DistanceMatcher(
        map_con, max_dist=MAX_DIST, obs_noise=OBS_NOISE, min_prob_norm=MIN_PROB_NORM
    )
    states, last_idx = matcher.match(track)
    print(f"  HMM matched {len(states)} states, last_idx={last_idx} (of {len(track)-1})")
    return states


def fallback_nearest_edge(G, df):
    """Simple per-point nearest-edge assignment, used only if HMM underperforms."""
    print("\n--- FALLBACK: assigning each image to its nearest road edge directly ---")
    print("  (Simpler than HMM — can be confused near parallel roads/intersections,")
    print("   but gives a usable result now while we tune the HMM matcher.)")
    G_proj = ox.project_graph(G)
    transformer = pyproj.Transformer.from_crs("epsg:4326", G_proj.graph["crs"], always_xy=True)
    x_proj, y_proj = transformer.transform(df["longitude"].values, df["latitude"].values)
    nearest_edges, dists = ox.distance.nearest_edges(G_proj, X=x_proj, Y=y_proj, return_dist=True)
    results = []
    for i, row in df.iterrows():
        u, v, key = nearest_edges[i]
        edge_data = G.get_edge_data(u, v, key)
        road_name = edge_data.get("name") if edge_data else None
        if isinstance(road_name, list):
            road_name = road_name[0]
        results.append({
            "image_id": row["image_id"],
            "filename": row["filename"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "captured_at": row["captured_at"],
            "matched_edge_id": f"{u}_{v}",
            "road_name": road_name,
            "match_distance_m": round(dists[i], 1),
            "match_method": "nearest_edge_fallback",
        })
    return pd.DataFrame(results)


def main():
    print("Loading OSM road graph...")
    G = ox.load_graphml(GRAPHML_FILE)
    print(f"  Graph has {len(G.nodes)} nodes, {len(G.edges)} edges")

    print("Loading captured images...")
    df = pd.read_csv(COORDS_FILE)
    df = df.sort_values("captured_at").reset_index(drop=True)

    # Step A: diagnose actual distances first
    diag = run_distance_diagnostic(G, df)

    # Step B: attempt real HMM map-matching
    map_con = build_map_from_osm(G)
    track = list(zip(df["latitude"], df["longitude"]))
    print(f"\nRunning HMM map-matching on {len(track)} points "
          f"(max_dist={MAX_DIST}, obs_noise={OBS_NOISE})...")
    states = try_hmm_match(map_con, track)

    match_rate = len(states) / len(track) if len(track) else 0

    if match_rate < 0.8:
        print(f"\nHMM only matched {match_rate:.0%} of points — using fallback method instead.")
        out_df = fallback_nearest_edge(G, df)
    else:
        print(f"\nHMM matched {match_rate:.0%} of points — using HMM results.")
        results = []
        for i, row in df.iterrows():
            if i < len(states):
                u, v = states[i]
                edge_data = G.get_edge_data(u, v)
                road_name = None
                if edge_data:
                    first_edge = list(edge_data.values())[0]
                    road_name = first_edge.get("name")
                    if isinstance(road_name, list):
                        road_name = road_name[0]
                edge_id = f"{u}_{v}"
            else:
                edge_id, road_name = None, None
            results.append({
                "image_id": row["image_id"], "filename": row["filename"],
                "latitude": row["latitude"], "longitude": row["longitude"],
                "captured_at": row["captured_at"],
                "matched_edge_id": edge_id, "road_name": road_name,
                "match_method": "hmm",
            })
        out_df = pd.DataFrame(results)

    out_df.to_csv(OUTPUT_MATCHED, index=False)
    n_roads = out_df["matched_edge_id"].nunique()
    print(f"\nDone. {len(out_df)} images matched across {n_roads} distinct road edges.")
    print(f"Saved to {OUTPUT_MATCHED}")
    print("Next: run step3_build_graph_outputs.py")


if __name__ == "__main__":
    main()