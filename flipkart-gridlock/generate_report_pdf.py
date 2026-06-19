"""Generate solution documentation PDF."""
from __future__ import annotations

from fpdf import FPDF
from pathlib import Path

OUT = Path("docs/Flipkart_Gridlock_Solution_Report.pdf")


class Report(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, "Flipkart Gridlock - Traffic Demand Prediction", align="R", new_x="LMARGIN", new_y="NEXT")
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


def build_pdf():
    pdf = Report()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.title_block("Traffic Demand Prediction Solution")
    pdf.body(
        "This document describes the complete machine learning pipeline built for the "
        "Flipkart Gridlock hackathon: preprocessing, feature engineering, model training, "
        "validation, and test submission generation."
    )

    # 1. Problem
    pdf.h1("1. Problem Definition")
    pdf.body(
        "Predict traffic demand (target column: demand, range (0, 1]) for each test row "
        "defined by geohash, timestamp, road attributes, and weather on Day 49."
    )
    pdf.bullet("Evaluation metric: score = max(0, 100 x R2)")
    pdf.bullet("Test set: 41,778 rows; Day 49 timestamps from 2:15 to 13:45 (47 slots)")
    pdf.bullet("Train set: Day 48 full day (69,427 rows) + Day 49 morning only (7,872 rows, 0:00-2:00)")
    pdf.bullet("89% of test rows have an exact (geohash, timestamp) match in Day 48")

    # 2. Preprocessing
    pdf.h1("2. Data Preprocessing")
    pdf.h2("2.1 Loading and Cleaning (src/pipeline.py)")
    pdf.bullet("Load train.csv and test.csv from dataset/")
    pdf.bullet("Parse timestamp into minutes since midnight (minutes)")
    pdf.bullet("Decode 6-character geohash to latitude and longitude (pygeohash)")
    pdf.bullet("Extract geohash 5-character prefix (g5) for coarser spatial grouping")
    pdf.bullet("Impute Temperature with train-set median (reused for test)")
    pdf.bullet("Impute NumberofLanes missing values with 0")
    pdf.bullet("Encode categoricals with integer maps; unseen/missing -> Unknown bucket:")
    pdf.body(
        "  RoadType (Residential/Street/Highway), LargeVehicles (Allowed/Not Allowed), "
        "Landmarks (Yes/No), Weather (Sunny/Rainy/Foggy/Snowy)"
    )

    pdf.h2("2.2 Cyclical Time Encoding")
    pdf.bullet("min_sin = sin(2*pi*minutes/1440)")
    pdf.bullet("min_cos = cos(2*pi*minutes/1440)")
    pdf.body("Captures daily periodic demand patterns without treating time as a linear trend.")

    pdf.h2("2.3 Leakage-Safe History Construction")
    pdf.bullet("All historical aggregates built from Day 48 only")
    pdf.bullet("Day 48 training rows: leave-one-out (LOO) means to prevent target leakage")
    pdf.bullet("Day 49 and test rows: plain Day 48 means (mirrors inference)")

    # 3. Feature Engineering
    pdf.h1("3. Feature Engineering")
    pdf.h2("3.1 Raw / Structural Features")
    pdf.bullet("lat, lon - decoded geohash coordinates")
    pdf.bullet("minutes, min_sin, min_cos - time of day")
    pdf.bullet("NumberofLanes, Temperature")
    pdf.bullet("RoadType, LargeVehicles, Landmarks, Weather (integer encoded)")

    pdf.h2("3.2 Historical Prior Features (Day 48 aggregates)")
    pdf.bullet("hist_g - mean demand per geohash")
    pdf.bullet("hist_t - mean demand per timestamp (time-of-day prior)")
    pdf.bullet("hist_g5 - mean demand per geohash 5-char prefix")
    pdf.bullet("hist_g5t - mean demand per (g5 prefix, timestamp) joint key")
    pdf.bullet("hist_nb - spatial neighbor prior (see Section 4)")
    pdf.body(
        "hist_gt - exact Day 48 demand at same (geohash, timestamp). Used only for "
        "cross-day inference (Day 49 / test), never as a GBM training feature on Day 48."
    )

    pdf.h2("3.3 Lookup Ladder (baseline predictor)")
    pdf.body("Fallback chain for rows without a learned model prediction:")
    pdf.bullet("1. Exact (geohash, timestamp) Day 48 demand")
    pdf.bullet("2. Optional spatial neighbor at same minute")
    pdf.bullet("3. Geohash daily mean")
    pdf.bullet("4. g5 prefix mean")
    pdf.bullet("5. Timestamp mean")
    pdf.bullet("6. Global Day 48 mean")
    pdf.body("Final lookup predictions clipped to [0, 1].")

    # 4. Spatial
    pdf.h1("4. Spatial Feature Engineering (src/spatial.py)")
    pdf.bullet("Build KDTree index from unique Day 48 geohash coordinates")
    pdf.bullet("For each row: find k=12 nearest geohashes (self excluded)")
    pdf.bullet("neighbor_predict: mean demand of neighbors at same minute")
    pdf.bullet("If exact minute empty (~58% grid sparsity): widen to +/- 45 minutes")
    pdf.bullet("hist_nb fills remaining NaNs with hist_g, then global mean")

    # 5. Models
    pdf.h1("5. Models Implemented")
    pdf.h2("5.1 LightGBM Structure Model (src/model.py)")
    pdf.body("Primary gradient boosting regressor trained on Day 48 features.")
    pdf.bullet("Algorithm: LightGBM regression (RMSE objective)")
    pdf.bullet("Categorical features: RoadType, LargeVehicles, Landmarks, Weather")
    pdf.bullet("reg_A3 hyperparameters (leaderboard-best baseline):")
    pdf.bullet("  num_leaves=15, min_child_samples=100, lambda_l2=5.0")
    pdf.bullet("  learning_rate=0.03, feature_fraction=0.8, bagging_fraction=0.8")
    pdf.bullet("Early stopping: 100 rounds on Day 49 morning validation")
    pdf.bullet("Optional log1p target transform (expm1 at predict, clip to [0,1])")

    pdf.h2("5.2 Lookup Baselines")
    pdf.bullet("lookup_plain - ladder without neighbor fallback")
    pdf.bullet("lookup_nb - ladder with spatial neighbor in fallback chain")

    pdf.h2("5.3 Cross-Day Stacked Model (src/crossday_model.py)")
    pdf.body("Two-model stack for Day 49 / test inference:")
    pdf.bullet("Matched rows (exact Day 48 key): cross-day GBM with FEATURES + hist_gt")
    pdf.bullet("  Trained on all 7,872 Day 49 morning rows")
    pdf.bullet("Unmatched rows (~11%): main Day 48 GBM (reg_A3) as fallback")
    pdf.bullet("Final prediction: clip(matched -> crossday, else -> main) to [0, 1]")

    pdf.h2("5.4 Model Tournament (compare_models.py)")
    pdf.body("Nine variants compared on train-only splits:")
    pdf.bullet("lookup_plain, lookup_nb")
    pdf.bullet("gbm_baseline, gbm_cap511, gbm_cap1023, gbm_cap1023_nolog")
    pdf.bullet("blend_cap1023, crossday_stack, hist_gt_hybrid")

    pdf.add_page()
    pdf.h1("6. Validation Strategy")
    pdf.h2("6.1 Primary Leaderboard Proxy (validate.py, validate_crossday_v2.py)")
    pdf.bullet("Train on Day 48, evaluate on Day 49 morning labels")
    pdf.bullet("80/20 holdout on Day 49 for cross-day model selection")
    pdf.bullet("Metric: R2 (coefficient of determination)")

    pdf.h2("6.2 Additional Holdouts (compare_models.py)")
    pdf.bullet("random_holdout - 80/20 Day 48 split, aggregates rebuilt from kept rows")
    pdf.bullet("testhours_holdout - hold out 2:15-13:45 on Day 48")
    pdf.bullet("day49_morning - full cross-day evaluation")

    pdf.h2("6.3 Honesty Check (validate_midday.py)")
    pdf.bullet("Within Day 48: compare model skill on morning vs test-hour band")
    pdf.bullet("Conservative estimate of daytime generalization")

    pdf.h1("7. Model Selection Results")
    pdf.h2("7.1 Cross-Day V2 Tournament (validate_crossday_v2.py)")
    pdf.body("Winner: crossday_nolog_all")
    pdf.bullet("Holdout R2: 0.9231")
    pdf.bullet("Full Day 49 R2: 0.9638")
    pdf.bullet("crossday_iter: 2994, main_iter: 226")
    pdf.bullet("Both models use identity link (use_log=False)")
    pdf.bullet("reg_A3 params for both cross-day and main fallback models")

    pdf.body("Comparison on Day 49 morning holdout:")
    pdf.bullet("crossday_nolog_all: 0.9231 (selected)")
    pdf.bullet("crossday_log: 0.9211")
    pdf.bullet("crossday_nolog: 0.9114")
    pdf.bullet("gbm_baseline: 0.7834")

    pdf.h2("7.2 Key Findings")
    pdf.bullet("High-capacity LightGBM (num_leaves 1023+) memorized Day 48 but scored worse on leaderboard (~86)")
    pdf.bullet("reg_A3 regularization generalized best to Day 49 (~88.95 leaderboard)")
    pdf.bullet("Removing log1p transform improved cross-day exact recovery")
    pdf.bullet("hist_g5t joint encoding added finer spatio-temporal prior")
    pdf.bullet("Raw hist_gt copy alone gives R2 ~0.52; cross-day mapping model required")

    pdf.h1("8. Final Test Pipeline (submit_v2.py)")
    pdf.bullet("1. Load and preprocess train + test via prepare()")
    pdf.bullet("2. Build spatial index and all historical features")
    pdf.bullet("3. Train cross-day model on Day 49 with hist_gt (crossday_nolog_all settings)")
    pdf.bullet("4. Train main GBM on Day 48 with early-stop on Day 49")
    pdf.bullet("5. Route predictions: matched rows -> crossday, unmatched -> main")
    pdf.bullet("6. Write submissions/sub_best.csv and sub_crossday_v2.csv")
    pdf.bullet("7. Also regenerate sub_gbm.csv (reg_A3 baseline for A/B)")

    pdf.h1("9. Submission Format")
    pdf.bullet("File: CSV with exactly 41,778 rows x 2 columns")
    pdf.bullet("Columns: Index, demand")
    pdf.bullet("Index order must match dataset/test.csv exactly")
    pdf.bullet("demand values in [0, 1], no NaN or Inf")
    pdf.bullet("Primary submission: submissions/sub_best.csv")

    pdf.h1("10. Project File Structure")
    pdf.bullet("src/pipeline.py - loading, cleaning, aggregates, hist features, lookup")
    pdf.bullet("src/spatial.py - KDTree neighbor index and hist_nb")
    pdf.bullet("src/model.py - LightGBM train/predict, reg_A3 params")
    pdf.bullet("src/crossday_model.py - cross-day stack training and inference")
    pdf.bullet("validate.py - Day 48 -> Day 49 morning validation")
    pdf.bullet("validate_crossday_v2.py - cross-day variant selection")
    pdf.bullet("compare_models.py - 9-model tournament on train splits")
    pdf.bullet("submit_v2.py - final test submission generator")
    pdf.bullet("submissions/ - output prediction CSVs")

    pdf.h1("11. Tech Stack")
    pdf.bullet("Python 3.14, pandas, numpy, scikit-learn, lightgbm, pygeohash")
    pdf.bullet("Platform: Windows, PowerShell")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build_pdf()
