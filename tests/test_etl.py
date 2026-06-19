import pandas as pd
from src.etl import to_ist, parse_violations, footprint_for_row


def test_to_ist_adds_530():
    s = pd.Series(["2023-11-20 00:28:46+00"])
    out = to_ist(s)
    assert out.dt.hour.iloc[0] == 5 and out.dt.minute.iloc[0] == 58


def test_parse_violations_handles_array_and_garbage():
    assert parse_violations('["WRONG PARKING","NO PARKING"]') == ["WRONG PARKING", "NO PARKING"]
    assert parse_violations("NULL") == []
    assert parse_violations(None) == []


def test_footprint_for_row():
    assert footprint_for_row("LGV") == "commercial"
    assert footprint_for_row("SCOOTER") == "two_wheeler"
    assert footprint_for_row("CAR") == "car"
