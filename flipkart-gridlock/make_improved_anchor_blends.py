from pathlib import Path

import numpy as np
import pandas as pd


SUB = Path("submissions")
ANCHOR = SUB / "sub_improved_notebook_exact.csv"
CANDIDATES = {
    "ens_es": SUB / "sub_improved_ens_es_mean.csv",
    "ens_all": SUB / "sub_improved_ens_all_mean.csv",
    "ens_mix50": SUB / "sub_improved_ens_mix_all50.csv",
    "seed11_all": SUB / "sub_improved_seed11_all.csv",
    "seed89_all": SUB / "sub_improved_seed89_all.csv",
}
WEIGHTS = [0.10, 0.20, 0.30, 0.40, 0.50]


def read_submission(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    assert list(df.columns) == ["Index", "demand"], path
    assert df["Index"].is_monotonic_increasing, path
    assert np.isfinite(df["demand"]).all(), path
    assert df["demand"].between(0, 1).all(), path
    return df


def main() -> None:
    anchor = read_submission(ANCHOR)
    rows = []
    for name, path in CANDIDATES.items():
        cand = read_submission(path)
        assert cand["Index"].equals(anchor["Index"]), path
        corr = np.corrcoef(anchor["demand"], cand["demand"])[0, 1]
        mae = np.mean(np.abs(anchor["demand"] - cand["demand"]))
        print(f"{name}: corr_anchor={corr:.6f} mae_anchor={mae:.6f}")
        for w in WEIGHTS:
            out = anchor.copy()
            out["demand"] = (
                (1.0 - w) * anchor["demand"].to_numpy()
                + w * cand["demand"].to_numpy()
            )
            out["demand"] = out["demand"].clip(0, 1)
            out_path = SUB / f"sub_imp_anchor_{name}_w{int(w * 100):02d}.csv"
            out.to_csv(out_path, index=False)
            rows.append((out_path.name, name, w, out["demand"].mean(), out["demand"].std()))
    summary = pd.DataFrame(rows, columns=["file", "candidate", "weight", "mean", "std"])
    summary.to_csv(SUB / "improved_anchor_blends_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
