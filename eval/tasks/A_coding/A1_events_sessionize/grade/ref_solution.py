"""Reference solution for A1_events_sessionize (audit only, not shipped to the model)."""

import pandas as pd


def sessionize(df: pd.DataFrame, gap_minutes: int = 30) -> pd.DataFrame:
    out = df.sort_values(["user_id", "ts"], kind="mergesort").reset_index(drop=True).copy()
    threshold = pd.Timedelta(minutes=gap_minutes)

    session_ids: list[int] = [0] * len(out)
    prev_user = None
    prev_ts = None
    current_id = -1
    for i, row in enumerate(out.itertuples(index=False)):
        if row.user_id != prev_user:
            current_id = 0
        elif row.ts - prev_ts > threshold:
            current_id += 1
        session_ids[i] = current_id
        prev_user = row.user_id
        prev_ts = row.ts

    out["session_id"] = session_ids
    return out
