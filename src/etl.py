import json
import pandas as pd
import h3
from src.config import (RAW_CSV, INTERIM, BBOX, H3, TZ, VALIDATION,
                        footprint_class, shift_of, PEAK)

USECOLS = ["id", "latitude", "longitude", "location", "vehicle_type",
           "violation_type", "created_datetime", "police_station",
           "junction_name", "validation_status", "vehicle_number",
           "device_id", "updated_vehicle_number", "updated_vehicle_type"]


def to_ist(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, errors="coerce").dt.tz_convert(TZ)


def parse_violations(raw) -> list:
    if raw is None or isinstance(raw, float) or raw == "NULL":
        return []
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


def footprint_for_row(vehicle_type) -> str:
    return footprint_class(vehicle_type if isinstance(vehicle_type, str) else "")


def _is_peak(hour: int) -> bool:
    mp, ep = PEAK["morning"], PEAK["evening"]
    return mp[0] <= hour < mp[1] or ep[0] <= hour < ep[1]


def run() -> pd.DataFrame:
    df = pd.read_csv(RAW_CSV, usecols=USECOLS, dtype=str)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df[(df.latitude.between(BBOX["min_lat"], BBOX["max_lat"])) &
            (df.longitude.between(BBOX["min_lon"], BBOX["max_lon"]))].copy()
    df["ts"] = to_ist(df["created_datetime"])
    df = df.dropna(subset=["ts"]).copy()
    df["hour"] = df["ts"].dt.hour
    df["dow"] = df["ts"].dt.dayofweek
    df["is_weekend"] = df["dow"] >= 5
    df["date"] = df["ts"].dt.date.astype(str)
    df["shift"] = df["hour"].map(shift_of)
    df["is_peak"] = df["hour"].map(_is_peak)
    vs = df["validation_status"].fillna("NULL")
    df["confirmed"] = ~vs.isin(VALIDATION["exclude"])
    # a record is "corrected" if rejected, or its vehicle number/type was updated
    upd_num = df["updated_vehicle_number"].notna() & (df["updated_vehicle_number"] != "NULL") & \
        (df["updated_vehicle_number"] != df["vehicle_number"])
    upd_typ = df["updated_vehicle_type"].notna() & (df["updated_vehicle_type"] != "NULL") & \
        (df["updated_vehicle_type"] != df["vehicle_type"])
    df["corrected"] = (vs == "rejected") | upd_num | upd_typ
    df["h3"] = [h3.latlng_to_cell(la, lo, H3["res_op"])
                for la, lo in zip(df.latitude, df.longitude)]
    df["footprint"] = df["vehicle_type"].map(footprint_for_row)
    df["violations"] = df["violation_type"].map(parse_violations)
    INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_parquet(INTERIM / "clean.parquet")
    expl = df[["id", "h3", "ts", "hour", "shift", "is_peak", "footprint",
               "confirmed", "vehicle_type"]].join(
        df["violations"].explode().rename("violation"))
    expl.to_parquet(INTERIM / "violations_exploded.parquet")
    print(f"ETL done: {len(df):,} clean rows, "
          f"{expl['violation'].notna().sum():,} violation records")
    return df


if __name__ == "__main__":
    run()
