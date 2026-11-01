"""Tests for ``mpt.configure(expand_collections=...)``.

By default a collection (dict, list, tuple, set) is substituted in phase 2 by
its ``repr``.  With ``expand_collections=False`` the collection itself is kept
out of the line and the indexed *item* is substituted instead, so
``_p23['vgs']`` becomes the value of that key.  A bare collection with no index
keeps its name.
"""

import os

import pytest

from mathprint import mpt
from mathprint_main import LatexRenderer, SettingsStore

_HERE = os.path.abspath(__file__)

_MOSFET = {"model": "p5", "gmid": 7.97, "vgs": 1.85, "vth": 1.67}


# --- The option ------------------------------------------------------------

def test_default_is_true():
    mpt.configure(reset=True)
    assert SettingsStore.settings_for(_HERE).expand_collections is True


def test_option_enable_disable():
    assert mpt.configure(expand_collections=False) == _HERE
    assert SettingsStore.settings_for(_HERE).expand_collections is False
    assert mpt.configure(expand_collections=True) == _HERE
    assert SettingsStore.settings_for(_HERE).expand_collections is True


def test_option_rejects_non_bool():
    with pytest.raises(ValueError):
        mpt.configure(expand_collections="yes")  # pyright: ignore[reportArgumentType]


# --- Phase 2: dict ---------------------------------------------------------

def test_dict_is_expanded_by_default(capsys):
    p23 = dict(_MOSFET)
    fi_d21_s23 = 3.941
    mpt[result := fi_d21_s23 - p23["vgs"]]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == 'result := fi_d21_s23 - p23["vgs"]'
    assert out[1] == 'result := 3.941 - %r["vgs"]' % p23
    assert out[2] == "result := 2.0909999999999997"


def test_dict_keeps_its_name_when_disabled(capsys):
    p23 = dict(_MOSFET)
    fi_d21_s23 = 3.941
    mpt.configure(expand_collections=False)
    result = mpt[result := fi_d21_s23 - p23["vgs"]]
    out = capsys.readouterr().out.splitlines()
    assert out == [
        'result := fi_d21_s23 - p23["vgs"]',
        "result := 3.941 - 1.85",
        "result := 2.0909999999999997",
    ]
    # Only the display changes; the expression is still evaluated normally.
    assert result == 3.941 - _MOSFET["vgs"]


# --- Phase 2: list, tuple, set ---------------------------------------------

def test_list_substitutes_the_item_when_disabled(capsys):
    numbers = [1, 2, 3, 4, 5]
    index = 2
    mpt.configure(expand_collections=False)
    assert mpt[item := numbers[index]] == 3
    out = capsys.readouterr().out.splitlines()
    assert out == ["item := numbers[index]", "item := 3", "item := 3"]


def test_tuple_substitutes_the_item_when_disabled(capsys):
    pair = (3, 4)
    mpt.configure(expand_collections=False)
    mpt[first := pair[0]]
    out = capsys.readouterr().out.splitlines()
    assert out[1] == "first := 3"


def test_set_keeps_its_name_when_disabled(capsys):
    values = {1, 2, 3}
    mpt.configure(expand_collections=False)
    mpt[count := len(values)]
    out = capsys.readouterr().out.splitlines()
    assert out[1] == "count := len(values)"


def test_list_is_expanded_when_enabled(capsys):
    numbers = [1, 2, 3]
    index = 1
    mpt.configure(expand_collections=True)
    assert mpt[item := numbers[index]] == 2
    out = capsys.readouterr().out.splitlines()
    assert out[1] == "item := [1, 2, 3][1]"


def test_variable_index_is_rendered_when_enabled(capsys):
    data = {"a": 1, "b": 2}
    key = "b"
    mpt.configure(expand_collections=True)
    mpt[picked := data[key]]
    out = capsys.readouterr().out.splitlines()
    assert out[1] == "picked := {'a': 1, 'b': 2}[b]"


def test_nested_index_substitutes_the_final_item(capsys):
    data = {"a": {"b": 7}}
    mpt.configure(expand_collections=False)
    mpt[nested := data["a"]["b"]]
    out = capsys.readouterr().out.splitlines()
    assert out[1] == "nested := 7"


def test_bare_collection_keeps_its_name_when_disabled(capsys):
    numbers = [1, 2, 3]
    mpt.configure(expand_collections=False)
    mpt[result := numbers]
    out = capsys.readouterr().out.splitlines()
    assert out[1] == "result := numbers"


def test_enabled_does_not_index_during_phase_2(capsys):
    class CountingDict(dict):
        def __init__(self) -> None:
            super().__init__({"x": 1})
            self.reads = 0

        def __getitem__(self, key):
            self.reads += 1
            return super().__getitem__(key)

    data = CountingDict()
    mpt.configure(expand_collections=True)
    mpt[value := data["x"]]
    assert data.reads == 1  # the expression itself, not phase 2


def test_disabled_indexes_once_for_the_item(capsys):
    class CountingDict(dict):
        def __init__(self) -> None:
            super().__init__({"x": 1})
            self.reads = 0

        def __getitem__(self, key):
            self.reads += 1
            return super().__getitem__(key)

    data = CountingDict()
    mpt.configure(expand_collections=False)
    mpt[value := data["x"]]
    assert data.reads == 2  # the substituted item, then the expression


# --- LaTeX -----------------------------------------------------------------

def test_subscript_renders_as_latex():
    # Regression: pytexit has no `visit_Subscript`, so a kept collection
    # (``d["x"]``) used to fall back to plain text in LaTeX mode.
    pytest.importorskip("pytexit")
    tex = LatexRenderer.to_source("3.941 - _p23['vgs']")
    assert tex is not None
    assert r"\left[vgs\right]" in tex


def test_unexpanded_collection_latex_uses_the_item(capsys, monkeypatch):
    pytest.importorskip("pytexit")
    import IPython.display as ipython_display

    calls = []
    monkeypatch.setattr(ipython_display, "display", lambda obj: calls.append(obj))

    p23 = dict(_MOSFET)
    mpt.configure(out_format="latex", expand_collections=False)
    result = mpt[value := 3.941 - p23["vgs"]]

    # Three lines, all rendered as LaTeX (none printed as plain text), and the
    # substitution line carries the item value rather than the collection.
    assert len(calls) == 3
    assert "1.85" in calls[1].data
    assert "model" not in calls[1].data
    assert capsys.readouterr().out == ""
    assert result == 3.941 - _MOSFET["vgs"]
