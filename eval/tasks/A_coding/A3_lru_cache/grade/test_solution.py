import importlib.util
import os
import pathlib

import pytest

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


def test_invalid_capacity_raises():
    with pytest.raises(ValueError):
        solution.LRUCache(0)
    with pytest.raises(ValueError):
        solution.LRUCache(-1)


def test_basic_get_put():
    cache = solution.LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    assert cache.get(1) == "a"
    assert cache.get(2) == "b"
    assert cache.get(3) == -1


def test_eviction_of_least_recently_used():
    cache = solution.LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    cache.put(3, "c")  # capacity 2 -> evicts key 1 (least recently used)
    assert cache.get(1) == -1
    assert cache.get(2) == "b"
    assert cache.get(3) == "c"


def test_get_promotes_recency():
    cache = solution.LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    cache.get(1)  # 1 is now most-recently-used, 2 is least
    cache.put(3, "c")  # should evict 2, not 1
    assert cache.get(1) == "a"
    assert cache.get(2) == -1
    assert cache.get(3) == "c"


def test_put_existing_key_updates_value_and_recency():
    cache = solution.LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    cache.put(1, "updated")  # 1 is now most-recently-used
    cache.put(3, "c")  # should evict 2, not 1
    assert cache.get(1) == "updated"
    assert cache.get(2) == -1


def test_capacity_one():
    cache = solution.LRUCache(1)
    cache.put(1, "a")
    cache.put(2, "b")
    assert cache.get(1) == -1
    assert cache.get(2) == "b"


def test_updating_existing_key_does_not_grow_size():
    cache = solution.LRUCache(2)
    cache.put(1, "a")
    cache.put(1, "b")
    cache.put(2, "c")
    # cache should hold {1: "b", 2: "c"}, no eviction should have happened
    assert cache.get(1) == "b"
    assert cache.get(2) == "c"


def test_comprehensive_leetcode_sequence():
    cache = solution.LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1     # 1 becomes most-recently-used
    cache.put(3, 3)              # evicts key 2 (LRU)
    assert cache.get(2) == -1
    cache.put(4, 4)             # evicts key 1 (LRU)
    assert cache.get(1) == -1
    assert cache.get(3) == 3
    assert cache.get(4) == 4


def test_capacity_three_recency_reordering():
    cache = solution.LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") == 1   # now order (LRU->MRU) is b, c, a
    cache.put("d", 4)           # evicts b, NOT a or c
    assert cache.get("b") == -1
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_repeated_get_keeps_key_hot():
    cache = solution.LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    for _ in range(5):
        assert cache.get(1) == "a"  # keep key 1 hot; key 2 is LRU
    cache.put(3, "c")              # must evict 2, not 1
    assert cache.get(1) == "a"
    assert cache.get(2) == -1


def test_falsy_key_and_value_are_supported():
    # a falsy key (0) and a falsy stored value (0) must not be confused with a
    # missing entry -- guards against `if not key` / `if not value` shortcuts.
    cache = solution.LRUCache(2)
    cache.put(0, "zero-key")
    cache.put("x", 0)
    assert cache.get(0) == "zero-key"
    assert cache.get("x") == 0
    assert cache.get("missing") == -1
