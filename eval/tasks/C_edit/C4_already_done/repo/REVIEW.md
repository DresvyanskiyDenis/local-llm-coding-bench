# Code review — src/payroll.py

1. `calculate_overtime_pay`: the docstring says only the hours BEYOND 40
   should be paid at 1.5x, but the implementation applies the 1.5x
   multiplier to ALL hours once the total exceeds 40. Please fix so only
   the excess hours are paid at the overtime rate.

2. `round_to_nearest_cent`: this truncates (`int(amount * 100) / 100`)
   instead of rounding. `10.126` should round to `10.13`, not truncate down
   to `10.12`. Please use proper rounding.

3. `clamp_hours`: I don't see a check for negative hours anywhere in this
   function — please add a guard that returns `0.0` when `hours_worked` is
   negative, otherwise a data-entry typo like -8 hours slips straight
   through to payroll.
