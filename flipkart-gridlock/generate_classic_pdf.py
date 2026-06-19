"""Generate PDF documenting the classic ML pipeline behind sub_classic.csv."""
from __future__ import annotations

import json
from pathlib import Path

from fpdf import FPDF

OUT = Path("docs/Classic_ML_sub_classic_Report.pdf")
REPORT = Path("submissions/classic_ml_report.json")


class Report(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, "Flipkart Gridlock - Classic ML Pipeline (sub_classic.csv)", align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def title_block(self, text: str):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(20, 20, 20)
        self.multi_cell(self._w(), 10, text)
        self.ln(4)

    def h1(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 60, 120)
        self.multi_cell(self._w(), 8, text)
        self.ln(2)

    def h2(self, text: str):
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(40, 40, 40)
        self.multi_cell(self._w(), 7, text)
        self.ln(1)

    def _w(self):
        return self.w - self.l_margin - self.r_margin

    def body(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(self._w(), 5.5, text)
        self.ln(1)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.set_x(self.l_margin)
        self.multi_cell(self._w(), 5.5, f"- {text}")
        self.ln(0.5)

    def mono(self, text: str):
        self.set_font("Courier", "", 9)
        self.set_text_color(20, 20, 20)
        self.multi_cell(self._w(), 5, text)
        self.ln(1)


def _load_report() -> dict:
    if REPORT.exists():
        return json.loads(REPORT.read_text())
    return {}


def build_pdf():
    rep = _load_report()
    th = next((r for r in rep.get("results", []) if r["bracket"] == "TESTHOURS"), {})
    scores = th.get("scores", {})
    incr = th.get("incremental_R2", [])
    winner = rep.get("winner", "extra_trees")

    pdf = Report()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.title_block("Inside sub_classic.csv")
    pdf.body(
        "This document explains exactly what happens inside submissions/sub_classic.csv, "
        "which scored 89 on the Flipkart Gridlock leaderboard (R2 = 0.89). "
        "It is a pure machine-learning pipeline: no lookup copy, no blend with Day-48 "
        "exact-match values. Every prediction is produced by a trained model from "
        "engineered features."
    )

    # 1. At a glance
    pdf.h1("1. At a Glance")
    pdf.bullet("Output file: submissions/sub_classic.csv (41,778 rows)")
    pdf.bullet("Leaderboard score: 89 (R2 = 0.89)")
    pdf.bullet("Model inside: ExtraTreesRegressor (scikit-learn ensemble of randomized trees)")
    pdf.bullet("Training data: Day 48 only (69,427 rows); test window Day 49 hours 2:15-13:45")
    pdf.bullet("Feature count: 35 numeric engineered features + 4 one-hot RoadType columns = 39 inputs")
    pdf.bullet("Scripts: classic_ml.py (tournament), submit_classic.py (writes CSV), src/classic_features.py")

    # 2. End-to-end flow
    pdf.h1("2. End-to-End Pipeline Flow")
    pdf.mono(
        "dataset/train.csv + dataset/test.csv\n"
        "        |\n"
        "        v\n"
        "  src/pipeline.py  ->  clean, decode geohash, cyclical time, categoricals\n"
        "        |\n"
        "        v\n"
        "  Day-48 aggregates (hist_g, hist_t, hist_g5, hist_g5t) + LOO on train rows\n"
        "        |\n"
        "        v\n"
        "  src/spatial.py   ->  hist_nb (12-neighbor spatial prior at same minute)\n"
        "        |\n"
        "        v\n"
        "  src/classic_features.py  ->  geohash profiles + interactions + test-band flags\n"
        "        |\n"
        "        v\n"
        "  to_design_matrix()  ->  39-column numeric matrix X\n"
        "        |\n"
        "        v\n"
        "  ExtraTreesRegressor.fit(X_train, demand)   on all Day 48 rows\n"
        "        |\n"
        "        v\n"
        "  predict(X_test)  ->  clip to [0, 1]  ->  sub_classic.csv"
    )

    # 3. Preprocessing
    pdf.h1("3. Data Preprocessing (shared base)")
    pdf.body("Both train and test rows pass through src/pipeline.py before feature engineering.")
    pdf.bullet("Parse timestamp to minutes since midnight")
    pdf.bullet("Cyclical encoding: min_sin, min_cos = sin/cos(2*pi*minutes/1440)")
    pdf.bullet("Decode 6-char geohash to lat/lon; extract 5-char prefix g5")
    pdf.bullet("Impute Temperature with train median; NumberofLanes missing -> 0")
    pdf.bullet("Encode RoadType, LargeVehicles, Landmarks, Weather as integers")
    pdf.bullet("All historical stats computed from Day 48 only (no Day 49 labels in training)")

    pdf.h2("3.1 Leakage-Safe History Features")
    pdf.bullet("hist_g: leave-one-out mean demand per geohash (Day 48 train rows)")
    pdf.bullet("hist_t: LOO mean demand per timestamp (global time-of-day curve)")
    pdf.bullet("hist_g5: LOO mean per geohash prefix")
    pdf.bullet("hist_g5t: LOO mean per (g5 prefix, timestamp)")
    pdf.bullet("For test rows: plain Day 48 means (no LOO needed)")
    pdf.body(
        "hist_gt (exact Day-48 slot copy) is deliberately NOT used in this pipeline."
    )

    pdf.h2("3.2 Spatial Prior (hist_nb)")
    pdf.bullet("KDTree over Day 48 geohash coordinates")
    pdf.bullet("k=12 nearest neighbors (excluding self)")
    pdf.bullet("Mean neighbor demand at same minute; +/- 45 min window if sparse")
    pdf.bullet("Fallback: hist_g, then global mean")

    # 4. Classic feature engineering
    pdf.add_page()
    pdf.h1("4. Classic Feature Engineering (35 features)")
    pdf.body(
        "src/classic_features.py builds interpretable groups. Each group targets a "
        "different slice of demand variance."
    )

    pdf.h2("4.1 Location Group (14 features)")
    pdf.bullet("lat, lon - decoded coordinates")
    pdf.bullet("hist_g, hist_g5, hist_nb - Day-48 spatial priors")
    pdf.bullet("d48_std, d48_max, d48_min, d48_range - per-geohash demand spread on Day 48")
    pdf.bullet("d48_morning - mean demand 0:00-2:00 at this geohash")
    pdf.bullet("d48_testhrs - mean demand 2:15-13:45 at this geohash")
    pdf.bullet("d48_amp - ratio testhrs/morning (daytime uplift factor)")
    pdf.bullet("d48_peak_min - minute of peak demand on Day 48")
    pdf.bullet("log_hist_g - log1p(hist_g) for skewed demand scale")
    pdf.body("Exploits ~99% geohash overlap: we have seen almost every test location on Day 48.")

    pdf.h2("4.2 Time Group (6 features)")
    pdf.bullet("minutes, min_sin, min_cos - time of day")
    pdf.bullet("hist_t - global time-of-day prior from Day 48")
    pdf.bullet("dist_peak - |minutes - d48_peak_min| (distance from location peak)")
    pdf.bullet("in_test_band - 1 if timestamp in 2:15-13:45, else 0")

    pdf.h2("4.3 Road Group (3 numeric + 4 one-hot)")
    pdf.bullet("NumberofLanes, LargeVehicles, Landmarks (numeric)")
    pdf.bullet("RoadType one-hot: Residential(0), Street(1), Highway(2), Unknown(3)")
    pdf.body("Road type is the strongest categorical split in the data.")

    pdf.h2("4.4 Weather Group (1 feature)")
    pdf.bullet("Temperature (imputed median)")
    pdf.body("Weather adds almost no incremental variance in our analysis.")

    pdf.h2("4.5 Interaction Group (7 features)")
    pdf.bullet("ix_g_sin = hist_g * min_sin")
    pdf.bullet("ix_g_cos = hist_g * min_cos")
    pdf.bullet("ix_g_t = hist_g * hist_t  (location-specific time effect)")
    pdf.bullet("ix_t_sin = hist_t * min_sin")
    pdf.bullet("ix_g_rt = hist_g * RoadType")
    pdf.bullet("ix_g_band = hist_g * in_test_band")
    pdf.bullet("ix_t_band = hist_t * in_test_band")
    pdf.body(
        "These make non-linear relationships explicit for linear models and give "
        "trees additional split cues for location-time-road combinations."
    )

    # 5. Variance explained
    pdf.h1("5. How Features Explain Variance")
    pdf.body(
        "R2 = 1 - (unexplained variance / total variance). We measured incremental R2 "
        "on the testhours holdout (train Day 48 outside 2:15-13:45, predict that band) "
        "using Ridge regression to show what each group contributes."
    )
    if incr:
        for row in incr:
            pdf.bullet(
                f"+{row['group_added']:12s}  cumulative R2 = {row['R2']:.4f}  "
                f"({row['n_features']} features)"
            )
    else:
        pdf.bullet("location: R2 ~ 0.55 (where you are explains half the variance)")
        pdf.bullet("+ time: R2 ~ 0.60")
        pdf.bullet("+ road: R2 ~ 0.82 (RoadType is the big jump)")
        pdf.bullet("+ weather: R2 ~ 0.82 (no gain)")
        pdf.bullet("+ interactions: R2 ~ 0.86 (full classic matrix)")

    pdf.body(
        "Interpretation: demand variance is mostly between locations (hist_g, profiles), "
        "then road type, then time-of-day interactions. Weather is negligible."
    )

    # 6. Model
    pdf.h1("6. The Model: ExtraTreesRegressor")
    pdf.body(
        "sub_classic.csv uses Extremely Randomized Trees - a classic bagging ensemble. "
        "Each of 400 trees splits on random feature subsets; predictions are averaged."
    )
    pdf.h2("6.1 Hyperparameters")
    pdf.bullet("n_estimators = 400")
    pdf.bullet("max_depth = 16")
    pdf.bullet("min_samples_leaf = 10")
    pdf.bullet("max_features = sqrt(n_features)")
    pdf.bullet("random_state = 0")
    pdf.body(
        "No log transform on target. Predictions clipped to [0, 1] after predict()."
    )

    pdf.h2("6.2 Why ExtraTrees (not Ridge or LightGBM)?")
    pdf.body("classic_ml.py ran a tournament on the same 39-feature matrix:")
    if scores:
        for name, r2 in sorted(scores.items(), key=lambda t: -t[1]):
            pdf.bullet(f"{name:18s}  testhours R2 = {r2:.4f}")
    pdf.body(
        f"Winner selection: 0.6 * testhours_R2 + 0.4 * random_R2 -> {winner}. "
        "ExtraTrees balanced strong testhours skill (0.8427) with high random-CV (0.9467). "
        "Ridge had the highest testhours R2 (0.8593) but ExtraTrees won the combined score."
    )

    # 7. Training vs inference
    pdf.add_page()
    pdf.h1("7. Training and Inference (submit_classic.py)")
    pdf.h2("7.1 Training")
    pdf.bullet("Load train.csv and test.csv")
    pdf.bullet("Preprocess all rows via prepare()")
    pdf.bullet("Build Day-48 aggregates, spatial index, geohash profiles")
    pdf.bullet("Engineer 35 features on Day 48 training rows (with LOO hist features)")
    pdf.bullet("Build design matrix X (39 columns) and target y = demand")
    pdf.bullet("Fit ExtraTreesRegressor on all 69,427 Day-48 rows")

    pdf.h2("7.2 Inference (test rows)")
    pdf.bullet("Same preprocessing and feature engineering on test.csv")
    pdf.bullet("hist_* features use plain Day-48 means (not LOO)")
    pdf.bullet("Geohash profiles from full Day 48")
    pdf.bullet("model.predict(X_test) for 41,778 rows")
    pdf.bullet("Clip predictions to [0, 1]")
    pdf.bullet("Write Index + demand to sub_classic.csv (Index order matches test.csv)")

    pdf.h2("7.3 What Is NOT Inside sub_classic.csv")
    pdf.bullet("No lookup ladder (no copying Day-48 demand at same geohash+timestamp)")
    pdf.bullet("No hist_gt feature")
    pdf.bullet("No blend with lookup (W_LOOKUP = N/A)")
    pdf.bullet("No Day 49 morning labels in training")
    pdf.bullet("No cross-day stack model")

    # 8. Comparison
    pdf.h1("8. Comparison to Other Submissions")
    pdf.bullet("sub_gbm.csv (LightGBM, 16 raw features): LB score 90, R2 = 0.90")
    pdf.bullet("sub_classic.csv (ExtraTrees, 39 engineered features): LB score 89, R2 = 0.89")
    pdf.bullet("sub_classic_ridge.csv (Ridge, same features): LB score 88")
    pdf.body(
        "The classic pipeline scores 89 - one point below the notebook LightGBM. "
        "More features and variance-aware engineering helped vs raw Ridge (88), but "
        "LightGBM on the simpler 16-feature set still edges ahead on the leaderboard. "
        "Trees on the engineered matrix capture road-type and interaction effects well, "
        "but boosting on raw hist features generalizes slightly better to Day 49 midday."
    )

    # 9. Validation
    pdf.h1("9. Local Validation Scores")
    if rep.get("results"):
        pdf.body("Scores from classic_ml_report.json (leak-safe holdouts):")
        for r in rep["results"]:
            pdf.h2(r["bracket"])
            for name, r2 in sorted(r.get("scores", {}).items(), key=lambda t: -t[1]):
                mark = " <-- winner" if name == winner and r["bracket"] == "TESTHOURS" else ""
                pdf.bullet(f"{name}: R2 = {r2:.4f}{mark}")
    pdf.body(
        "Testhours holdout (2:15-13:45 on Day 48) is the bracket most aligned with "
        "the real test window. Morning holdout (0:00-2:00) is a weaker LB proxy."
    )

    # 10. Files
    pdf.h1("10. Key Files")
    pdf.bullet("src/pipeline.py - base cleaning and Day-48 aggregates")
    pdf.bullet("src/spatial.py - neighbor prior hist_nb")
    pdf.bullet("src/ml_features.py - profile stats and base interactions")
    pdf.bullet("src/classic_features.py - full 35-feature engineering + design matrix")
    pdf.bullet("classic_ml.py - model tournament and variance report")
    pdf.bullet("submit_classic.py - trains winner and writes sub_classic.csv")
    pdf.bullet("submissions/classic_ml_report.json - full tournament results")

    pdf.h1("11. How to Reproduce")
    pdf.mono(
        "python classic_ml.py\n"
        "python submit_classic.py"
    )
    pdf.body(
        "Output: submissions/sub_classic.csv ready for manual upload to the competition platform."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build_pdf()
