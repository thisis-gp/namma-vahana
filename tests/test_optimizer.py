import pandas as pd
from src.optimizer import greedy_allocate


def test_greedy_picks_highest_value_per_shift():
    cells = pd.DataFrame({
        "h3": ["a", "b", "c"], "shift": ["MORNING"] * 3,
        "value": [10.0, 5.0, 1.0],
    })
    plan = greedy_allocate(cells, n_units=2)
    assert list(plan["h3"]) == ["a", "b"]
    assert list(plan["assigned_unit"]) == ["Unit 1", "Unit 2"]
