import pandas as pd
import osmnx as ox
from src.config import INTERIM, ARTIFACTS, BBOX

CACHE = INTERIM / "osm_roads.parquet"

ROAD_WEIGHT = {"motorway": 1.0, "trunk": 1.0, "primary": 0.9, "secondary": 0.7,
               "tertiary": 0.5, "unclassified": 0.3, "residential": 0.3,
               "living_street": 0.2, "service": 0.2}


def _hwy_to_weight(h):
    if isinstance(h, list):
        h = h[0] if h else "residential"
    cls = h if isinstance(h, str) else "unknown"
    return cls, ROAD_WEIGHT.get(cls, 0.4)


def load_cached() -> dict | None:
    if not CACHE.exists():
        return None
    d = pd.read_parquet(CACHE)
    return {r.h3: (r.road_class, r.f_road) for r in d.itertuples()}


def build(force: bool = False) -> dict:
    if CACHE.exists() and not force:
        return load_cached()
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")
    bbox = (BBOX["min_lon"], BBOX["min_lat"], BBOX["max_lon"], BBOX["max_lat"])
    print("Downloading Bengaluru drive network (one-time)...")
    G = ox.graph_from_bbox(bbox=bbox, network_type="drive")
    edges = ox.graph_to_gdfs(G, nodes=False)
    lons = cis["lon"].to_numpy()
    lats = cis["lat"].to_numpy()
    ne = ox.distance.nearest_edges(G, lons, lats)
    rows = []
    for h3id, key in zip(cis["h3"], ne):
        try:
            hwy = edges.loc[tuple(key), "highway"]
        except Exception:
            hwy = "residential"
        cls, w = _hwy_to_weight(hwy)
        rows.append([h3id, cls, w])
    d = pd.DataFrame(rows, columns=["h3", "road_class", "f_road"])
    d.to_parquet(CACHE)
    print(f"OSM road classes cached for {len(d):,} cells. "
          f"Top classes: {d['road_class'].value_counts().head(5).to_dict()}")
    return {r.h3: (r.road_class, r.f_road) for r in d.itertuples()}


if __name__ == "__main__":
    build()
