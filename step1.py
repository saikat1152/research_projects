"""
STEP 1 (simplified) — Load the road network graph from a manually
exported OSM file.

This version makes NO live API calls at all, on purpose. OSMnx's live
Overpass fetching has its own internal retry/backoff logic that ignores
external timeouts and mirror-switching, which is what was causing the
indefinite hangs. Since you've already confirmed the query works fine
directly in Overpass Turbo, we use that export instead — this script
either loads it in under a second, or fails immediately with a clear
message. It cannot hang.

Install first:
    pip install osmnx networkx

Usage:
    python step1_fetch_osm_graph.py
"""

import os
import osmnx as ox

# ---------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------
MANUAL_OSM_FILE = "area_export.osm"
OUTPUT_GRAPHML = "local_road_network.graphml"
# ---------------------------------------------------------------


def main():
    print(f"Looking for '{MANUAL_OSM_FILE}' in: {os.getcwd()}")

    if not os.path.exists(MANUAL_OSM_FILE):
        print(f"\nFile not found: {MANUAL_OSM_FILE}")
        print("\nFiles actually present in this folder:")
        for f in os.listdir("."):
            print(" -", f)
        print(f"\nMake sure your Overpass Turbo export is saved as exactly "
              f"'{MANUAL_OSM_FILE}' in this same folder, then re-run.")
        raise FileNotFoundError(MANUAL_OSM_FILE)

    print(f"Found it. Loading (this is instant, no network call)...")
    G = ox.graph_from_xml(MANUAL_OSM_FILE)

    print("\nLoaded graph:")
    print(f"  Real intersections (nodes): {len(G.nodes)}")
    print(f"  Real road segments (edges): {len(G.edges)}")

    ox.save_graphml(G, OUTPUT_GRAPHML)
    print(f"\nSaved to {OUTPUT_GRAPHML}")
    print("Next: run step2_map_match.py")


if __name__ == "__main__":
    main()


# =================================================================
# How to produce area_export.osm (you've already confirmed this
# query works in your browser):
# =================================================================
#
# 1. Go to https://overpass-turbo.eu
# 2. Paste this query:
#
#    [out:xml][timeout:60];
#    (
#      way["highway"](23.726725,90.414579,23.730342,90.418258);
#      >;
#    );
#    out;
#
# 3. Click "Run" — you should see roads highlighted (you've confirmed
#    this part already works).
# 4. Click "Export" (top menu bar) -> "download as raw OSM data" (.osm)
# 5. Move/rename the downloaded file so it is EXACTLY "area_export.osm"
#    sitting in the SAME folder as this script (D:\Research_2026\VQA).
#    Windows sometimes hides file extensions, so double check in
#    File Explorer: View -> Show -> File name extensions -> ON,
#    to confirm it isn't actually "area_export.osm.xml" or similar.
# 6. Run: python step1_fetch_osm_graph.py
# =================================================================