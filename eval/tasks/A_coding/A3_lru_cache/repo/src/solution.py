"""A fixed-capacity Least-Recently-Used (LRU) cache.

Implement the `LRUCache` class below:

    - `LRUCache(capacity: int)` — `capacity` is the max number of key/value
      pairs the cache may hold. Raise `ValueError` if `capacity <= 0`.
    - `get(key) -> object` — return the cached value, or `-1` if `key` is
      not present. A successful `get` counts as "using" the key: it becomes
      the most-recently-used entry.
    - `put(key, value) -> None` — insert or update `key`. This also counts
      as "using" the key (most-recently-used). If inserting a *new* key
      would push the cache over `capacity`, evict the single
      least-recently-used entry first.

All operations must run in O(1) amortized time.
"""


class LRUCache:
    def __init__(self, capacity: int) -> None:
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def put(self, key, value) -> None:
        raise NotImplementedError
