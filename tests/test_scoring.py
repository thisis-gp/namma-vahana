from src.scoring import severity_for, normalize


def test_severity_blocking_vs_incidental():
    assert severity_for(["DOUBLE PARKING"], "LGV") > severity_for(["WRONG PARKING"], "CAR")
    assert severity_for(["DEFECTIVE NUMBER PLATE"], "SCOOTER") == 0.0


def test_severity_commercial_multiplier():
    assert severity_for(["WRONG PARKING"], "LGV") > severity_for(["WRONG PARKING"], "SCOOTER")


def test_normalize_0_1():
    out = normalize([0, 5, 10])
    assert out[0] == 0.0 and out[-1] == 1.0
