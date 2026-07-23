"""Sessionize a user-events log.

Given a pandas DataFrame of raw events with columns:
    - user_id: str
    - ts: pandas.Timestamp (not guaranteed to be sorted)
    - event: str

Group each user's events into sessions: a new session starts whenever the
gap since that user's previous event STRICTLY EXCEEDS ``gap_minutes``. Attach
a `session_id` column (int, starting at 0 for each user's first session;
session ids do NOT need to be unique across different users, only within one
user's own event stream).

Return a copy of `df`, sorted by (user_id, ts), with the `session_id` column
appended as the last column. All other input columns must be left untouched.
"""

import pandas as pd


def sessionize(df: pd.DataFrame, gap_minutes: int = 30) -> pd.DataFrame:
    raise NotImplementedError
