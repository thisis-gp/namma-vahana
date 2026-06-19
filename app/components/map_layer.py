import pydeck as pdk


def _prep(df, value_col):
    df = df.copy()
    v = df[value_col].astype(float)
    vmax = v.max() if len(v) and v.max() > 0 else 1.0
    norm = (v / vmax).clip(0, 1)
    df["_elev"] = (norm * 1000).astype(float)
    df["fill_color"] = [[255, int(90 + 130 * (1 - n)), 30, 190] for n in norm]
    return df


def deck(df, value_col="cis_hour", tooltip=None, zoom=11):
    d = _prep(df, value_col)
    layer = pdk.Layer(
        "H3HexagonLayer",
        d,
        get_hexagon="h3",
        get_fill_color="fill_color",
        get_elevation="_elev",
        elevation_scale=20,
        extruded=True,
        coverage=0.9,
        pickable=True,
        auto_highlight=True,
    )
    return pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(
            latitude=12.97, longitude=77.59, zoom=zoom, pitch=50, bearing=10),
        map_style=None,
        tooltip=tooltip or {"text": "Cell: {h3}"},
    )
