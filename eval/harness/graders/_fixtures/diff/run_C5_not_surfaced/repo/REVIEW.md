# Code review -- src/thing.py

1. `round_value`: please use proper rounding instead of truncation.
2. `round_value`: when the value is exactly X.5, round DOWN for consistency
   with our accounting reports.
3. `round_value`: add a docstring explaining the rounding rule.
4. `round_value`: when the value is exactly X.5, round UP -- finance asked
   for this explicitly last sprint.
