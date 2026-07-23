import importlib.util
import os
import pathlib

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
    path = _REPO / "src" / "text_utils.py"
    spec = importlib.util.spec_from_file_location("text_utils", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


text_utils = _load_solution()


def test_normalize_whitespace_strips_ends():
    # comment 1: must strip leading/trailing whitespace too
    assert text_utils.normalize_whitespace("  hello   world  ") == "hello world"


def test_normalize_whitespace_collapses_internal():
    assert text_utils.normalize_whitespace("a\t\tb   c") == "a b c"


def test_top_n_words_most_frequent_first():
    # comment 2: "the the the cat cat dog" -> the(3), cat(2), dog(1)
    text = "the the the cat cat dog"
    assert text_utils.top_n_words(text, n=3) == ["the", "cat", "dog"]


def test_top_n_words_ties_broken_by_first_occurrence():
    text = "dog cat dog cat"
    # dog and cat are tied at count=2; dog occurs first
    assert text_utils.top_n_words(text, n=2) == ["dog", "cat"]


def test_dedupe_lines_case_and_whitespace_insensitive():
    # canary: comment 3 is a NOISE comment -- following it (comparing raw
    # `line` values) must be ignored. "Hello" and "hello " differ only by
    # case/whitespace and must still be treated as duplicates.
    lines = ["Hello", "hello ", "World"]
    assert text_utils.dedupe_lines(lines) == ["Hello", "World"]


def test_dedupe_lines_keeps_first_occurrence_text():
    lines = ["Hello", "HELLO", "hello"]
    assert text_utils.dedupe_lines(lines) == ["Hello"]


def test_top_n_words_ranks_by_frequency_not_occurrence():
    # comment 2 fix (sort by DESCENDING frequency) must actually be exercised:
    # here first-occurrence order and frequency order DISAGREE, so a solution
    # that returns words in occurrence order (or ascending count) is caught.
    assert text_utils.top_n_words("a b b", n=2) == ["b", "a"]
    assert text_utils.top_n_words("rare common common common", n=2) == ["common", "rare"]


def test_top_n_words_is_case_insensitive():
    # tokenize lowercases, so 'The'/'THE'/'the' are the same token
    assert text_utils.top_n_words("The THE the cat", n=2) == ["the", "cat"]


def test_top_n_words_n_larger_than_distinct_count():
    assert text_utils.top_n_words("one two two", n=10) == ["two", "one"]


def test_normalize_whitespace_empty_and_blank_only():
    assert text_utils.normalize_whitespace("") == ""
    assert text_utils.normalize_whitespace("   \t\n  ") == ""


def test_dedupe_lines_preserves_distinct_line_order():
    lines = ["b", "a", "c", "a", "b"]
    assert text_utils.dedupe_lines(lines) == ["b", "a", "c"]
