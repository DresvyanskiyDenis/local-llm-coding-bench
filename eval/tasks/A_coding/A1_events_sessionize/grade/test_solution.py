import importlib.util
import os
import pathlib

import pandas as pd

_HERE = pathlib.Path(__file__).parent


def _resolve_repo():
    # Works both when the test is run in place (repo/ is a sibling of grade/)
    # and under the harness (which copies test_*.py to a temp dir and points
    # PYTHONPATH at the model's repo/).
    candidates = [_HERE / "repo", _HERE.parent / "repo"]
    candidates += [pathlib.Path(p) for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    for c in candidates:
        if (c / "src").exists():
            return c
    return _HERE.parent / "repo"


_REPO = _resolve_repo()


def _load_solution():
    path = _REPO / "src" / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


solution = _load_solution()


def _ts(hhmm: str) -> pd.Timestamp:
    return pd.Timestamp(f"2026-01-01 {hhmm}:00")


def _sample_df() -> pd.DataFrame:
    rows = [
        ("bob", _ts("09:36"), "click"),
        ("alice", _ts("09:00"), "view"),
        ("alice", _ts("10:29"), "view"),
        ("bob", _ts("09:05"), "click"),
        ("alice", _ts("09:20"), "click"),
        ("alice", _ts("10:59"), "view"),
        ("alice", _ts("10:00"), "purchase"),
    ]
    return pd.DataFrame(rows, columns=["user_id", "ts", "event"])


def test_session_boundaries():
    result = solution.sessionize(_sample_df(), gap_minutes=30)
    expected = {
        ("alice", "09:00"): 0,
        ("alice", "09:20"): 0,
        ("alice", "10:00"): 1,
        ("alice", "10:29"): 1,
        ("alice", "10:59"): 1,  # gap from 10:29 is exactly 30min -> NOT a new session
        ("bob", "09:05"): 0,
        ("bob", "09:36"): 1,  # gap is 31min -> new session
    }
    for _, row in result.iterrows():
        key = (row["user_id"], row["ts"].strftime("%H:%M"))
        assert row["session_id"] == expected[key], key


def test_sorted_by_user_and_ts():
    result = solution.sessionize(_sample_df(), gap_minutes=30)
    pairs = list(zip(result["user_id"], result["ts"]))
    assert pairs == sorted(pairs)


def test_preserves_other_columns():
    result = solution.sessionize(_sample_df(), gap_minutes=30)
    assert set(result.columns) == {"user_id", "ts", "event", "session_id"}
    assert result["event"].isin(["click", "view", "purchase"]).all()
    assert list(result.columns)[-1] == "session_id"


def test_single_event_user():
    df = pd.DataFrame([("carol", _ts("08:00"), "view")], columns=["user_id", "ts", "event"])
    result = solution.sessionize(df, gap_minutes=30)
    assert result.iloc[0]["session_id"] == 0


def test_default_gap_minutes_is_30():
    result = solution.sessionize(_sample_df())
    row = result[(result["user_id"] == "alice") & (result["ts"] == _ts("10:00"))]
    assert row.iloc[0]["session_id"] == 1


def test_smaller_gap_splits_more_sessions():
    # with a 15-minute gap, alice's 09:00->09:20 (20min) is now also a new session
    result = solution.sessionize(_sample_df(), gap_minutes=15)
    row = result[(result["user_id"] == "alice") & (result["ts"] == _ts("09:20"))]
    assert row.iloc[0]["session_id"] == 1


def test_column_order_is_preserved_with_session_id_last():
    # spec: do not drop/rename/reorder input columns; only APPEND session_id last
    result = solution.sessionize(_sample_df(), gap_minutes=30)
    assert list(result.columns) == ["user_id", "ts", "event", "session_id"]


def test_input_dataframe_is_not_mutated():
    # spec: return a COPY; the caller's frame must not gain a session_id column
    df = _sample_df()
    before_cols = list(df.columns)
    before_len = len(df)
    _ = solution.sessionize(df, gap_minutes=30)
    assert "session_id" not in df.columns
    assert list(df.columns) == before_cols
    assert len(df) == before_len


def test_session_ids_are_nonnegative_integers():
    result = solution.sessionize(_sample_df(), gap_minutes=30)
    for value in result["session_id"]:
        assert int(value) == value  # integer-valued (accepts int / numpy int)
        assert value >= 0


def _multi_session_df() -> pd.DataFrame:
    # deliberately unsorted; dave has THREE sessions, erin resets to 0
    rows = [
        ("dave", _ts("11:00"), "x"),
        ("dave", _ts("08:10"), "x"),
        ("erin", _ts("07:00"), "x"),
        ("dave", _ts("09:05"), "x"),
        ("dave", _ts("08:00"), "x"),
        ("dave", _ts("09:00"), "x"),
    ]
    return pd.DataFrame(rows, columns=["user_id", "ts", "event"])


def test_session_counter_increments_beyond_one_and_resets_per_user():
    result = solution.sessionize(_multi_session_df(), gap_minutes=30)
    got = {
        (row["user_id"], row["ts"].strftime("%H:%M")): row["session_id"]
        for _, row in result.iterrows()
    }
    assert got[("dave", "08:00")] == 0
    assert got[("dave", "08:10")] == 0  # +10min, same session
    assert got[("dave", "09:00")] == 1  # +50min, new session
    assert got[("dave", "09:05")] == 1  # +5min, same session
    assert got[("dave", "11:00")] == 2  # +115min, third session
    assert got[("erin", "07:00")] == 0  # ids restart at 0 for each user


def test_duplicate_timestamps_stay_in_same_session():
    df = pd.DataFrame(
        [("z", _ts("08:00"), "a"), ("z", _ts("08:00"), "b"), ("z", _ts("08:20"), "c")],
        columns=["user_id", "ts", "event"],
    )
    result = solution.sessionize(df, gap_minutes=30)
    assert list(result["session_id"]) == [0, 0, 0]
