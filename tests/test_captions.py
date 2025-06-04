import ast
from pathlib import Path
from typing import List


def load_split_long_word():
    """Dynamically load `split_long_word` from captions.py without importing heavy dependencies."""
    source = Path("captions.py").read_text()
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "split_long_word":
            ns = {}
            exec(compile(ast.Module([node], type_ignores=[]), filename="captions.py", mode="exec"), {"List": List}, ns)
            return ns["split_long_word"]
    raise RuntimeError("split_long_word not found")


split_long_word = load_split_long_word()


def test_word_shorter_than_max_length():
    assert split_long_word("hello", max_length=10) == ["hello"]


def test_word_exactly_max_length():
    word = "abcdefghij"
    assert len(word) == 10
    assert split_long_word(word, max_length=10) == [word]


def test_word_longer_than_max_length_hyphenated():
    result = split_long_word("abcdefghijk", max_length=5)
    assert result == ["abcde-", "fghij-", "k"]
    # ensure intermediate parts end with hyphen
    assert all(part.endswith("-") for part in result[:-1])
