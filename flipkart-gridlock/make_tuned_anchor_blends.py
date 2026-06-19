from pathlib import Path

import numpy as np
import pandas as pd


SUB = Path("submissions")
ANCHOR = SUB / "sub_improved_notebook_exact.csv"
CANDIDATES = [
    SUB / "sub_imp_tuned_d4_lr025_2500.csv",
    SUB / "sub_imp_tuned_d4_smooth_2492.csv",
    SUB / "sub_imp_tuned_d7_lr025_2497.csv",
    SUB / "sub_imp_tuned_d6_lr03_2494.csv",
    SUB / "sub_imp_tuned_d5_lr03_2498.csv",
]
WEIGHTS = [0.05, 0.10, 0.15, 0.20, 0.30, 0.40]


def read(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    assert list(df.columns) == ["Index", "demand"], path
    assert df.shape == (41778, 2), path
    assert np.isfinite(df["demand"]).all(), path
    assert df["demand"].between(0, 1).all(), path
    return df


def main() -> None:
    anchor = read(ANCHOR)
    rows = []
    for path in CANDIDATES:
        cand = read(path)
        assert cand["Index"].equals(anchor["Index"]), path
        name = path.stem.replace("sub_imp_tuned_", "")
        corr = np.corrcoef(anchor["demand"], cand["demand"])[0, 1]
        mae = np.mean(np.abs(anchor["demand"] - cand["demand"]))
        print(f"{name}: corr_anchor={corr:.6f} mae_anchor={mae:.6f}")
        for w in WEIGHTS:
            out = anchor.copy()
            out["demand"] = (
                (1 - w) * anchor["demand"].to_numpy()
                + w * cand["demand"].to_numpy()
            ).clip(0, 1)
            out_path = SUB / f"sub_imp_tuned_anchor_{name}_w{int(w * 100):02d}.csv"
            out.to_csv(out_path, index=False)
            rows.append(
                dict(
                    file=out_path.name,
                    candidate=name,
                    weight=w,
                    mean=out["demand"].mean(),
                    std=out["demand"].std(),
                )
            )
    pd.DataFrame(rows).to_csv(SUB / "tuned_anchor_blends_summary.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
