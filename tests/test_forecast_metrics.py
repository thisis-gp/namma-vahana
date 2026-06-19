from src.forecast import precision_at_k


def test_precision_at_k_perfect():
    actual = {"a": 10, "b": 9, "c": 1, "d": 0}
    pred = {"a": 5, "b": 4, "c": 0.1, "d": 0.0}
    assert precision_at_k(actual, pred, k=2) == 1.0


def test_precision_at_k_half():
    actual = {"a": 10, "b": 9, "c": 1, "d": 0}
    pred = {"c": 5, "a": 4, "d": 1, "b": 0}
    assert precision_at_k(actual, pred, k=2) == 0.5
