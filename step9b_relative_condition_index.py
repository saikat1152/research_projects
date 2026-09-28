"""
Step 11b - Relative road-condition index from the attributes we actually have.

This is NOT an iRAP Star Rating (that needs speed, AADT etc., see docs/irap/
input_coverage.csv). It ranks the 10 roads against each other using only the
questionnaire attributes that pass four stated rules, with the minimum number
of modelling choices:

 Selection rules (an attribute is scored only if it passes all four)
  R1 varies      : after collapsing categories that iRAP gives the same risk
                   tier, the answer differs between at least two roads
  R2 observable  : share of batch answers marked low-confidence <= LOWCONF_MAX
  R3 iRAP-backed : the attribute has a risk factor in iRAP model v3.10 and the
                   guide documents the direction of its effect
  R4 not flagged : iRAP itself does not call it unobservable from video

 Direction of effect (which answer is worse) is taken from the iRAP
 Methodology Reference Guide v3.10 (docs/irap/), cited per attribute below.
 Only the ORDER of categories is used, never iRAP's numeric risk factors.

 Aggregation (three variants; agreement between them is reported)
  M1 mean rank   : per attribute rank the roads (ties averaged), average the
                   ranks. Uses order only - no spacing, no scaling.
  M2 mean level  : per attribute level / max level, averaged (assumes equal
                   spacing between categories).
  M3 share worse : share of scored attributes not in their best state.
 All variants weight attributes equally (no evidence for other weights in this
 setting). Robustness: leave-one-attribute-out and alternative R2 thresholds.

 Outputs: road_condition_index.csv, index_sensitivity.csv
"""

import math
import os

import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
LOWCONF_MAX = 0.50

# answer_code -> ordinal level (0 = best ... higher = worse), and the evidence
LEVELS = {
    13: ({17: 0, 16: 1, 13: 1, 14: 1, 11: 1, 12: 1, 10: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 15: 1,
          1: 1, 2: 1, 3: 1, 4: 1},
         "Roadside severity object: 'None' is the lowest-severity category; trees, poles, rigid "
         "structures/buildings and low rigid objects share one severity tier (Guide PDF p.63)"),
    22: ({1: 0, 2: 1, 3: 2, 4: 3},
         "Curvature: straight < moderate < sharp < very sharp (Guide PDF p.50)"),
    25: ({1: 0, 2: 1, 3: 2},
         "Road condition: good < medium < poor (Guide PDF p.55)"),
    26: ({1: 0, 2: 1},
         "Delineation: adequate < poor (Guide PDF p.46)"),
    33: ({1: 0, 2: 1, 3: 2},
         "Vehicle parking: none < one side < two sides (Guide PDF p.58)"),
    34: ({1: 0, 2: 1, 3: 2, 4: 3, 6: 4, 7: 4, 5: 5},
         "Sidewalk: barrier < >=3 m < 1-3 m < 0-1 m from road < informal path (= iRAP poor/medium "
         "quality sidewalk, Coding Manual p.95) < none (Guide PDF p.96)"),
    35: ({1: 0, 2: 1, 3: 2, 4: 3, 6: 4, 7: 4, 5: 5}, "as q34 (passenger side)"),
}
# attributes with no v3.10 risk factor or flagged as hard to see in video
EXCLUDED_BY_IRAP = {
    31: "Pedestrian fencing: risk factor removed in v3.10 (Guide PDF p.96)",
    36: "Service road: no contribution to the SRS in v3.10 (Guide PDF p.62)",
    23: "Quality of curve: iRAP notes it is 'difficult to detect from video alone' (Guide PDF p.52)",
}


def spearman(a, b):
    return a.rank().corr(b.rank())


def build(roads, lowconf, thr, drop=()):
    cols = {}
    for q, (mapping, _) in LEVELS.items():
        if q in drop or lowconf[q] > thr:
            continue
        d = roads[roads.q_id == q].set_index("road_id").answer_code
        lv = d.map(lambda c: mapping.get(int(c)) if c not in ("", None) and not pd.isna(c) else None)
        if lv.isna().any() or lv.nunique() < 2:
            continue
        cols[q] = lv.astype(float)
    lev = pd.DataFrame(cols)
    if lev.empty:
        return lev, None
    res = pd.DataFrame(index=lev.index)
    n = len(lev)
    res["M1_mean_rank"] = (lev.rank(method="average") / n).mean(axis=1)
    res["M2_mean_level"] = (lev / lev.max()).mean(axis=1)
    res["M3_share_worse"] = (lev > 0).mean(axis=1)
    return lev, res


def main():
    roads = pd.read_csv(os.path.join(ROOT, "road_ratings.csv"), dtype={"answer_code": str})
    summ = pd.read_csv(os.path.join(ROOT, "attribute_summary.csv")).set_index("q_id")
    lowconf = summ.batch_low_confidence_share.to_dict()

    # ---- selection table (documented, reproducible) ----
    rows = []
    for q in summ.index:
        r1 = r2 = r3 = r4 = None
        why = ""
        if q in LEVELS:
            mp = LEVELS[q][0]
            d = roads[roads.q_id == q].answer_code.map(lambda c: mp.get(int(c)) if c not in ("", None) and not pd.isna(c) else None)
            r1 = bool(d.notna().all() and d.nunique() > 1)
            r2 = lowconf[q] <= LOWCONF_MAX
            r3 = True
            r4 = True
            why = LEVELS[q][1]
        else:
            r1 = bool(summ.loc[q, "varies_between_roads"])
            r2 = lowconf[q] <= LOWCONF_MAX
            r3 = q not in EXCLUDED_BY_IRAP and None
            r4 = q not in EXCLUDED_BY_IRAP
            why = EXCLUDED_BY_IRAP.get(q, "no documented ordering used / not a condition attribute")
        keep = bool(q in LEVELS and r1 and r2 and r3 and r4)
        rows.append({"q_id": q, "attribute": summ.loc[q, "attribute"], "R1_varies": r1,
                     "R2_low_conf_share": lowconf[q], "R2_pass": r2, "scored": keep, "basis": why})
    sel = pd.DataFrame(rows)

    # ---- index ----
    lev, res = build(roads, lowconf, LOWCONF_MAX)
    info = roads.drop_duplicates("road_id").set_index("road_id")[["road_name", "n_images"]]
    out = info.join(res).join(lev.add_prefix("level_q"))
    # straight-line length between the road's two end nodes
    ex = pd.read_csv(os.path.join(ROOT, "roads_extracted.csv")).set_index("road_id")

    def hav(r):
        p1, p2 = math.radians(r.lat_a), math.radians(r.lat_b)
        dl, dp = math.radians(r.lon_b - r.lon_a), p2 - p1
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * 6371000 * math.asin(math.sqrt(a))

    out["length_m_straight_line"] = ex.apply(hav, axis=1)
    out = out.sort_values("M1_mean_rank", ascending=False)
    out.to_csv(os.path.join(ROOT, "road_condition_index.csv"), encoding="utf-8")

    # ---- sensitivity ----
    base = res.M1_mean_rank
    rows = [{"variant": "M2 vs M1", "n_attr": lev.shape[1], "spearman_with_M1": round(spearman(res.M2_mean_level, base), 2)},
            {"variant": "M3 vs M1", "n_attr": lev.shape[1], "spearman_with_M1": round(spearman(res.M3_share_worse, base), 2)}]
    for q in lev.columns:
        _, r = build(roads, lowconf, LOWCONF_MAX, drop=(q,))
        rows.append({"variant": f"drop q{q} {summ.loc[q, 'attribute']}", "n_attr": lev.shape[1] - 1,
                     "spearman_with_M1": round(spearman(r.M1_mean_rank, base), 2) if r is not None else None})
    for thr in (0.30, 0.60, 0.80):
        l2, r = build(roads, lowconf, thr)
        rows.append({"variant": f"low-confidence threshold <= {thr}", "n_attr": l2.shape[1],
                     "spearman_with_M1": round(spearman(r.M1_mean_rank, base), 2) if r is not None else None})
    sens = pd.DataFrame(rows)
    sens.to_csv(os.path.join(ROOT, "index_sensitivity.csv"), index=False, encoding="utf-8")

    # ---- network level ----
    net = {}
    for name, w in [("equal", pd.Series(1.0, index=out.index)), ("by images", out.n_images.astype(float)),
                    ("by length", out.length_m_straight_line)]:
        net[name] = round((w * out.M1_mean_rank).sum() / w.sum(), 3)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 90)
    print(sel.to_string(index=False))
    print("\nscored attributes:", list(lev.columns))
    print(out[["road_name", "n_images", "length_m_straight_line", "M1_mean_rank", "M2_mean_level", "M3_share_worse"]].round(2).to_string())
    print("\n", sens.to_string(index=False))
    print("\nnetwork mean of M1 by weighting:", net)


if __name__ == "__main__":
    main()
