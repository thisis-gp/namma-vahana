## Learned User Preferences

- Frame Flipkart Gridlock ML work like an ML PhD/researcher: deterministic function recovery, leakage-safe validation, and hypothesis-driven experiments — not autocorrelation or ARIMA-style time-series modeling.
- Do not use autocorrelation or classical time-series (ARIMA, LSTM) approaches; treat time dependence via engineered features (`hist_gt`, `hist_t`, `hist_g5t`, cyclical time).
- Build and compare multiple models on train-only splits; select the test submission from the best validated model.
- Goal is leaderboard score 100 (R² = 1.0 on all test rows).
- Validate model choice on train splits — prioritize testhours holdout (Day-48 hours 2:15–13:45, matching test window) over Day-48 random or Day-49 morning holdouts for midday LB correlation; morning holdout (~0.77) does not rank models well for test.
- Run model tournaments (`compare_models.py`, `validate_crossday_v2.py`, `classic_ml.py`, `validate_ml_v2.py`) before generating test submissions.
- Reject lookup as the primary prediction method; prefer learned ML models that explain variance (pure GBM with `W_LOOKUP=0` scored LB 90).
- Do not upload to the competition platform unless asked; user submits CSVs manually.

## Learned Workspace Facts

- Flipkart Gridlock hackathon: predict traffic `demand`; evaluation score = max(0, 100 × R²); test has 41,778 rows.
- Train: Day 48 (full day) + Day 49 morning labels only (0:00–2:00); test: Day 49 hours 2:15–13:45.
- ~99% of test rows share a geohash seen in train; ~89% have exact (geohash, timestamp) match in Day 48.
- Best leaderboard 90: pure GBM from `solution.ipynb` config (`num_leaves=63`, `min_child_samples=40`, `learning_rate=0.03`, `lambda_l2=1.0`, `BEST_ITER=245`, `W_LOOKUP=0`); prior reg_A3 scored ~88.95; high-capacity variants (`num_leaves` 1023+) scored ~86 on LB.
- Testhours holdout (2:15–13:45 on Day 48) is more informative for midday LB model selection than Day-49 morning holdout; local testhours winners can still lose on LB (Ridge 0.85 testhours → LB 88 vs GBM 0.84 → LB 90).
- Cross-day stack (`validate_crossday_v2.py`) scored high locally on morning (~0.978) but ~88 LB — worse than notebook GBM; not current best path.
- `hist_g5t` in `src/pipeline.py`: (geohash g5 prefix, timestamp) joint Day-48 prior mean.
- `hist_gt` is not a GBM training feature (LOO undefined for Day-48 rows); used in lookup/crossday inference only.
- Leak hunt clean; realistic performance ceiling ~0.90 R² given provided features; lookup alone ~0.52 R² on morning.
- Submission CSVs must be exactly 41,778 rows; `Index` must match `dataset/test.csv` order; `demand` in [0, 1], no NaNs.
- Core pipeline: `src/pipeline.py`, `src/spatial.py`, `src/model.py`, `validate.py`, `submit.py`; extended tooling `probe.py`, `leak_hunt.py`, `validate_ml_v2.py`, `submit_ml.py`, `classic_ml.py`, `submit_classic.py`, `src/ml_features.py`, `src/classic_features.py`; outputs under `submissions/`.
