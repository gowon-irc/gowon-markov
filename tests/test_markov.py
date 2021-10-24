import pytest

from gowon_markov import markov


def cs(c, f):
    return {"command": c, "fn": f}


@pytest.mark.parametrize(
    "arg,expected",
    [
        pytest.param("a:b", [cs("a", "b")], id="one valid arg"),
        pytest.param("a:b,c:d", [cs("a", "b"), cs("c", "d")], id="two valid args"),
        pytest.param("a", [], id="one too small arg"),
        pytest.param("a:b:c", [cs("a", "b")], id="one too large arg"),
        pytest.param("a,b:c", [cs("b", "c")], id="one valid arg one invalid arg"),
        pytest.param("", [], id="empty arg string"),
    ],
)
def test_split_corpus_arg(arg, expected):
    got = markov.split_corpus_arg(arg)

    assert got == expected


@pytest.mark.parametrize(
    "corpus_file_dict,root,expected",
    [
        pytest.param(cs("a", "b"), "", cs("a", "b"), id="no root"),
        pytest.param(cs("a", "b"), "/d", cs("a", "/d/b"), id="with root"),
    ],
)
def test_add_root_to_corpus_file_dict(corpus_file_dict, root, expected):
    got = markov.add_root_to_corpus_file_dict(corpus_file_dict, root)

    assert got == expected


@pytest.mark.parametrize(
    "corpus_file_list,root,expected",
    [
        pytest.param([cs("a", "b")], "", [cs("a", "b")], id="no root"),
        pytest.param([cs("a", "b")], "/d", [cs("a", "/d/b")], id="with root"),
        pytest.param([], "", [], id="empty corpus list"),
    ],
)
def test_corpus_file_list_add_root(corpus_file_list, root, expected):
    got = markov.corpus_file_list_add_root(corpus_file_list, root)

    assert got == expected
