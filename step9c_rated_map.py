"""
Step 11c - Network-level rating file and rated map.

Reads road_condition_index.csv (from step9b_relative_condition_index.py) and
writes:
  final_graph_rating.csv   network-level relative index under three road
                           weightings (equal / by images / by straight-line
                           length), plus the scored attribute set
  final_rated_map.html     interactive map, roads coloured by the index
  final_rated_plot.png     static version (no tiles, no internet)

The index is a RELATIVE ranking of these roads (0 = best rank, 1 = worst rank
among the roads), not an iRAP Star Rating. Colours are scaled min-max over the
roads present, so they only compare roads within this dataset.
"""

import os

import folium
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX_COL = "M1_mean_rank"
CMAP = cm.get_cmap("RdYlGn_r") if hasattr(cm, "get_cmap") else plt.get_cmap("RdYlGn_r")


def main():
    idx = pd.read_csv(os.path.join(ROOT, "road_condition_index.csv"))
    ex = pd.read_csv(os.path.join(ROOT, "roads_extracted.csv"))
    roads = ex.merge(idx[["road_id", INDEX_COL, "M2_mean_level", "M3_share_worse",
                          "length_m_straight_line"]], on="road_id")

    # ---- network-level file ----
    lev_cols = [c for c in idx.columns if c.startswith("level_q")]
    attrs = ";".join(c.replace("level_", "") for c in lev_cols)
    rows = []
    for name, w in [("equal", pd.Series(1.0, index=roads.index)),
                    ("by_images", roads.n_images.astype(float)),
                    ("by_length", roads.length_m_straight_line)]:
        row = {"weighting": name, "n_roads": len(roads), "scored_attributes": attrs}
        for col in [INDEX_COL, "M2_mean_level", "M3_share_worse"]:
            row[f"network_{col}"] = round(float((w * roads[col]).sum() / w.sum()), 3)
        rows.append(row)
    pd.DataFrame(rows).to_csv(os.path.join(ROOT, "final_graph_rating.csv"), index=False)

    # ---- maps ----
    lo, hi = roads[INDEX_COL].min(), roads[INDEX_COL].max()
    norm = mcolors.Normalize(vmin=lo, vmax=hi)

    def colour(v):
        return mcolors.to_hex(CMAP(norm(v)))

    m = folium.Map(location=[roads[["lat_a", "lat_b"]].values.mean(),
                             roads[["lon_a", "lon_b"]].values.mean()], zoom_start=18, tiles=None)
    for _, r in roads.iterrows():
        folium.PolyLine(
            [(r.lat_a, r.lon_a), (r.lat_b, r.lon_b)], color=colour(r[INDEX_COL]),
            weight=3 + 7 * (r.n_images / roads.n_images.max()), opacity=0.9,
            tooltip=(f"{r.road_name} ({r.road_id}) | relative index {r[INDEX_COL]:.2f} "
                     f"(higher = worse rank) | {r.n_images} images"),
        ).add_to(m)
    m.get_root().html.add_child(folium.Element(
        "<div style='position:fixed;bottom:20px;left:20px;z-index:9999;background:white;"
        "padding:8px 10px;border:1px solid #888;font:12px sans-serif'>"
        "Relative condition index<br>green = better rank, red = worse rank<br>"
        "<i>Not an iRAP Star Rating. Line width = image count.</i></div>"))
    m.save(os.path.join(ROOT, "final_rated_map.html"))

    fig, ax = plt.subplots(figsize=(9, 9))
    for _, r in roads.iterrows():
        ax.plot([r.lon_a, r.lon_b], [r.lat_a, r.lat_b], color=colour(r[INDEX_COL]),
                linewidth=2 + 8 * (r.n_images / roads.n_images.max()), solid_capstyle="round")
        ax.annotate(f"{r[INDEX_COL]:.2f}", ((r.lon_a + r.lon_b) / 2, (r.lat_a + r.lat_b) / 2),
                    fontsize=8, ha="center", va="bottom")
    sm = cm.ScalarMappable(norm=norm, cmap=CMAP)
    fig.colorbar(sm, ax=ax, shrink=0.6, label="relative index (higher = worse rank among these roads)")
    ax.set_title("Relative road-condition index (not an iRAP Star Rating)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")
    plt.tight_layout()
    plt.savefig(os.path.join(ROOT, "final_rated_plot.png"), dpi=150)

    print(pd.read_csv(os.path.join(ROOT, "final_graph_rating.csv")).drop(columns="scored_attributes").to_string(index=False))
    print("scored attributes:", attrs)
    print("wrote final_graph_rating.csv, final_rated_map.html, final_rated_plot.png")


if __name__ == "__main__":
    main()
