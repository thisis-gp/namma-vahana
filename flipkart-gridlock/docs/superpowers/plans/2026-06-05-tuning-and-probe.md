# Feature Probe + Morning-Validated Tuning Sweep

> **For the implementing agent (Cursor):** Two parts. Part A is an INVESTIGATION (report output, don't act). Part B is a tuning sweep with a strict keep/discard rule. **Everything is scored on the day-48→day-49 (morning) holdout — the ONLY validation that predicts this leaderboard.** Ignore within-day-48 holdouts. Do not submit anything.

## Context (read first)
- Best model so far: **reg_A3** (num_leaves=15, min_child_samples=100, lambda_l2=5.0, BEST_ITER=223) → morning holdout R² **0.7710**, leaderboard **88.95**.
- A leak hunt came back clean; ~21% of `demand` variance is irreducible from the features. So **100 is not reachable** — the realistic target here is ~0.90.
- Two open questions this spec answers: (1) is there a hidden / non-linear feature relationship or multicollinearity we're not exploiting? (2) does careful hyperparameter tuning beat reg_A3's 0.7710?

---

## Part A — Feature-relationship probe (`probe.py`)

Mutual information detects **non-linear** dependence that Pearson correlation misses (e.g., we saw `corr(demand, Temperature)=0.003` — MI will say whether temperature truly carries nothing, or has a non-linear signal). The feature-feature correlation block addresses multicollinearity. Gain importance shows what the model actually uses.

- [ ] **Step 1: Install dep**

Run:
```bash
pip install -q scikit-learn
```
(already present; this is a no-op guard.)

- [ ] **Step 2: Create `probe.py`**

```python
"""Feature-relationship probe. Reports only -- does not change any model.
Detects non-linear feature->demand dependence (mutual information),
multicollinearity (feature-feature correlation), and what the model uses."""
import numpy as np
from sklearn.feature_selection import mutual_info_regression
from sklearn.metrics import r2_score
from src.pipeline import load_raw, prepare, add_hist_features, FEATURES, CAT_COLS
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import train_gbm, predict_gbm


def main():
    tr, te = load_raw()
    trc, _te, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    d48 = add_neighbor_feature(add_hist_features(trc[trc.day == 48].copy(), agg, True), sp, agg)
    d49 = add_neighbor_feature(add_hist_features(trc[trc.day == 49].copy(), agg, False), sp, agg)
    X = d48[FEATURES].fillna(0.0)
    y = d48["demand"].to_numpy()
    disc = [f in CAT_COLS for f in FEATURES]  # mark categoricals as discrete

    print("== Mutual information (non-linear dependence) feature -> demand ==")
    mi = mutual_info_regression(X, y, discrete_features=disc, random_state=0)
    for f, v in sorted(zip(FEATURES, mi), key=lambda t: -t[1]):
        print(f"  {f:14s} MI={v:.4f}")

    print("\n== Pearson corr feature <-> demand (linear only) ==")
    for f in FEATURES:
        print(f"  {f:14s} r={np.corrcoef(X[f], y)[0,1]:+.4f}")

    print("\n== Feature-feature |corr| > 0.8 (multicollinearity) ==")
    C = X.corr().abs()
    hits = 0
    for i, a in enumerate(FEATURES):
        for b in FEATURES[i + 1:]:
            if C.loc[a, b] > 0.8:
                print(f"  {a} ~ {b}: {C.loc[a, b]:.3f}"); hits += 1
    if not hits:
        print("  (none > 0.8)")

    print("\n== LightGBM gain importance (train day48, valid day49 morning) ==")
    cat = [FEATURES.index(c) for c in CAT_COLS]
    m, bit = train_gbm(d48[FEATURES], y, cat, eval_X=d49[FEATURES],
                       eval_y=d49["demand"].to_numpy(), use_log=True)
    imp = m.feature_importance(importance_type="gain"); tot = imp.sum()
    for f, v in sorted(zip(FEATURES, imp), key=lambda t: -t[1]):
        print(f"  {f:14s} gain={100*v/tot:5.1f}%")
    r2 = r2_score(d49["demand"].to_numpy(), predict_gbm(m, d49[FEATURES]))
    print(f"  morning valid R2={r2:.4f}  best_iter={bit}")
    print("\nINTERPRET: a feature with HIGH MI but LOW gain% is underused -> a hidden")
    print("relationship worth a transform/interaction. Multicollinearity doesn't hurt")
    print("tree prediction, but a |corr|~1.0 pair means one feature is redundant.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run and report**

Run:
```bash
python probe.py
```
Report the full output. **Flag** any feature with high MI but low gain (a hidden, underused relationship), and any feature pair with |corr| ≈ 1.0 (redundancy). Do not change the model yet — report so we decide.

---

## Part B — Morning-validated tuning sweep (`tune_morning.py`)

Optuna search over LightGBM params, objective = **day-49 morning holdout R²** (train on day 48, early-stop + score on day 49). Keep the result ONLY if it beats reg_A3's 0.7710 by a clear margin (≥ +0.005) — a smaller "win" is likely just fitting the small holdout's noise.

- [ ] **Step 1: Install Optuna**

Run:
```bash
pip install -q optuna
```

- [ ] **Step 2: Create `tune_morning.py`**

```python
"""Morning-validated LightGBM tuning. Objective = day48->day49 morning R2.
Keep ONLY if it beats reg_A3 (0.7710) by >= +0.005, else keep reg_A3."""
import numpy as np, optuna
from sklearn.metrics import r2_score
from src.pipeline import load_raw, prepare, add_hist_features, FEATURES, CAT_COLS
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import train_gbm, predict_gbm

BASELINE = 0.7710  # reg_A3 morning holdout
MARGIN = 0.005


def main():
    tr, te = load_raw()
    trc, _te, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    d48 = add_neighbor_feature(add_hist_features(trc[trc.day == 48].copy(), agg, True), sp, agg)
    d49 = add_neighbor_feature(add_hist_features(trc[trc.day == 49].copy(), agg, False), sp, agg)
    cat = [FEATURES.index(c) for c in CAT_COLS]
    X, y = d48[FEATURES], d48["demand"].to_numpy()
    Xv, yv = d49[FEATURES], d49["demand"].to_numpy()

    def objective(trial):
        p = dict(
            objective="regression", metric="rmse", verbose=-1, bagging_freq=1,
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            num_leaves=trial.suggest_int("num_leaves", 8, 128),
            min_child_samples=trial.suggest_int("min_child_samples", 20, 400),
            feature_fraction=trial.suggest_float("feature_fraction", 0.5, 1.0),
            bagging_fraction=trial.suggest_float("bagging_fraction", 0.5, 1.0),
            lambda_l1=trial.suggest_float("lambda_l1", 0.0, 10.0),
            lambda_l2=trial.suggest_float("lambda_l2", 0.0, 10.0),
        )
        m, _ = train_gbm(X, y, cat, eval_X=Xv, eval_y=yv, use_log=True, params=p)
        return r2_score(yv, predict_gbm(m, Xv))

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=0))
    study.optimize(objective, n_trials=60, show_progress_bar=False)

    print(f"\nbaseline reg_A3 morning R2 : {BASELINE:.4f}")
    print(f"best tuned morning R2      : {study.best_value:.4f}")
    print(f"best params                : {study.best_params}")
    # refit best to get best_iteration for submit.py
    bp = dict(objective="regression", metric="rmse", verbose=-1, bagging_freq=1,
              **study.best_params)
    _, bit = train_gbm(X, y, cat, eval_X=Xv, eval_y=yv, use_log=True, params=bp)
    print(f"best_iteration             : {bit}")
    if study.best_value >= BASELINE + MARGIN:
        print(f"\nDECISION: KEEP. Paste best params into model.py PARAMS (add the")
        print(f"  objective/metric/verbose/bagging_freq lines) and set submit.py BEST_ITER={bit}.")
    else:
        print(f"\nDECISION: DISCARD. Gain < +{MARGIN} over reg_A3 -> likely holdout noise; keep reg_A3.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the sweep**

Run:
```bash
python tune_morning.py
```
Expected: 60 trials (~3–8 min), then a baseline-vs-best comparison + a KEEP/DISCARD decision.

- [ ] **Step 4: Apply only if KEEP**

If the decision is KEEP: update `src/model.py` `PARAMS` with the printed best params (keep the `objective`, `metric`, `verbose=-1`, `bagging_freq=1` lines), set `submit.py` `BEST_ITER` to the printed value, then:
```bash
python validate.py
python submit.py
python -c "import pandas as pd; s=pd.read_csv('submissions/sub_gbm.csv'); te=pd.read_csv('dataset/test.csv'); print('rows', len(s)==41778, '| index', (s['Index'].values==te['Index'].values).all(), '| nan', bool(s['demand'].isna().any()), '| range', bool(((s['demand']>=0)&(s['demand']<=1)).all()))"
```
Confirm `validate.py` shows the improved morning R², the format check is all True, and `sub_gbm.csv` is regenerated. If the decision is DISCARD, change nothing and say so.

---

## Report back
- Part A: full `probe.py` output + any high-MI/low-gain feature or |corr|≈1 pair you noticed.
- Part B: baseline vs best morning R², best params, best_iteration, and the KEEP/DISCARD decision.
- If KEPT: confirmation of the values applied + the new `validate.py` morning R² + format check.

**Hard rules:** score everything on the day-48→day-49 morning holdout only; never tune against within-day-48 holdouts or the leaderboard; apply tuned params only if they beat 0.7710 by ≥ +0.005; do not submit to the platform.
