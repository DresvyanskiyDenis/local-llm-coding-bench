# Task: propose 3 approaches with tradeoffs

You are a data scientist. Two CRM systems need to be merged, and each has
its own customer table with **different schemas** (different column
names, and no shared numeric ID — e.g. one system has
`(full_name, email, phone)`, the other has `(first_name, last_name,
email_address, address)`). Some records refer to the same real customer
but have typos, formatting differences, or missing fields.

Propose **3 distinct approaches** to detecting which records across the
two tables refer to the same customer (record linkage / deduplication).
For each approach:
- Briefly describe how it works.
- Give its main tradeoffs (accuracy, engineering effort, maintainability,
  explainability, compute cost — pick whichever are actually relevant to
  that approach).
- Note at least one concrete failure mode or limitation.

Keep the whole answer roughly 300-500 words. Prose or a short structured
list is fine; you do not need to write any code.
