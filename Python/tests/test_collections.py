import pytest
from copy import deepcopy
from vermils.collections import freeze, FrozenDict, FrozenList, StrChain
from vermils.collections import ObjDict


def test_frozendict():
    d = {'a': 1, 'b': 2}
    fd = FrozenDict(d)
    assert str(fd) == f"FrozenDict{d}"
    assert fd['a'] == 1
    assert fd.get('a') == 1
    assert fd.get('n', 123) == 123
    assert fd.get('n') is None
    assert tuple(fd.keys()) == tuple(d.keys())
    assert tuple(fd.values()) == tuple(d.values())
    assert tuple(fd.items()) == tuple(d.items())
    assert fd == d
    assert d == fd
    assert hash(fd)
    assert hash(fd) == hash(fd)
    assert 'a' in fd
    assert 'n' not in fd
    assert all(k in d for k in fd)
    assert len(fd) == 2

    fd2 = FrozenDict(fd)
    assert fd2 is fd
    assert fd2 == fd
    assert fd == FrozenDict(d)


def test_frozenlist():
    fl = FrozenList([1, 2, 3])
    h1 = hash(fl)
    assert h1 == hash(fl)
    assert fl == [1, 2, 3]
    assert fl >= [1, 2, 3]
    assert fl >= [1, 2]
    assert fl > [1, 2]
    assert fl <= [1, 2, 3]
    assert fl <= [1, 2, 3, 4]
    assert fl < [1, 2, 3, 4]
    assert fl != [1, 2, 3, 4]
    assert repr(fl) == "FrozenList(1, 2, 3)"
    assert [1, 2, 3] == fl
    assert [1, 2] != fl
    assert isinstance(fl, tuple)
    assert fl[0] == 1
    t = (1, 2, 3)
    assert t is tuple(t)
    assert fl == t
    assert fl is FrozenList(fl)


def test_freeze():
    frozen = freeze([0, 1, 2, {'a': [1, 2, 3]}, {1, 2}])
    assert isinstance(frozen, tuple)
    assert isinstance(frozen[3], FrozenDict)
    assert isinstance(frozen[3]['a'], tuple)
    assert isinstance(frozen[4], frozenset)
    assert 12345 == freeze(12345)

    d = {}
    d['d'] = d
    with pytest.raises(TypeError, match="recursive"):
        freeze(d)

    with pytest.raises(TypeError, match="unhashable"):
        class Unhashable:
            __hash__ = None
        freeze({1: Unhashable()}, True)

    with pytest.raises(TypeError):
        frozen[0] = 10

    with pytest.raises(TypeError):
        frozen[3]['a'] = 10

    with pytest.raises(AttributeError):
        frozen[3].pop('a')

    with pytest.raises(AttributeError):
        frozen[3].update({'a': 9})

    class Freezable:
        def __freeze__(self, memo):
            return 123

    assert freeze(Freezable()) == 123


def test_strchain():
    # Test initialization
    c1 = StrChain("abc")
    c2 = StrChain(["abc"])
    assert c1 == c2 and c1() == "abc"

    # Size is not the total chars but the number of strings
    assert len(c1) == 1

    # Test attribute concatenation
    c3 = c1.defg
    assert c3() == "abc.defg"
    assert len(c3) == 2

    with pytest.raises(AttributeError):
        c1._abc

    # Test customised separator
    c4 = StrChain(joint=":")
    assert c4["abc"].defg() == "abc:defg"

    # Test get item
    assert c3[1] == "defg"

    c3.wert.ttre.tt[1:5]() == "defg.wert.ttre.tt"

    assert (str(c3["This is not possible as attribute"])
            == "abc.defg.This is not possible as attribute")

    with pytest.raises(IndexError):
        c3[5]

    with pytest.raises(TypeError):
        c3[1.0]

    # Test __repr__
    assert repr(
        c3) == "StrChain(['abc', 'defg'], joint='.', callback=<class 'str'>, **{})"

    # Test magic methods

    # Test equality
    assert c1 == c2
    assert c1 != c3
    assert c4.abc() == c1() and c4.abc != c1  # Different separator
    assert c1 != "abc"  # Different type

    # Test hash
    assert hash(c1) == hash(c2)
    assert hash(c1) != hash(c3)

    # Test len
    assert len(c1) == 1
    assert len(c3) == 2

    # Test bool
    assert bool(c1)
    assert not bool(StrChain())

    # Test add
    assert c1 + c3 == StrChain(["abc", "abc", "defg"])
    assert c1 + "defg" == StrChain(["abc", "defg"])

    # Test radd
    assert "abcde" + c1 == StrChain(["abcde", "abc"])

    # Test iadd
    c9 = StrChain("abc")
    c9 += "defg"
    assert c9 == StrChain(["abc", "defg"])
    c9 += ["hijk", "lmno"]
    assert c9 == StrChain(["abc", "defg", "hijk", "lmno"])

    # Test mul
    assert c1 * 3 == StrChain(["abc", "abc", "abc"])
    assert c1 * 0 == StrChain()
    with pytest.raises(TypeError):
        c1 * "abc"

    # Test rmul
    assert 3 * c1 == StrChain(["abc", "abc", "abc"])
    assert 0 * c1 == StrChain()

    # Test imul
    c1_cp = c1
    c1_cp *= 3
    assert c1_cp == StrChain(["abc", "abc", "abc"])
    assert c1 is not c1_cp  # StrChain is immutable

    # Test contains
    assert "abc" in c1
    assert "defg" in c3
    assert "123" not in c3
    assert 123 not in c3

    # Test iter
    assert list(iter(c1)) == ["abc"]

    # Test reversed
    assert list(reversed(c1)) == ["abc"]
    assert list(reversed(c3)) == ["defg", "abc"]

    # Test callbacks
    def callback(s):
        return str(s).upper()

    c5 = StrChain(callback=callback)

    assert c5.abc() == "ABC"

    # Test kw
    c6 = StrChain(juicy=True)
    assert c6.abc._kw == {"juicy": True}


def test_objdict_dict_like():
    d = {"a": 1, "b": 2, "c": 3}

    # Test initialization
    od = ObjDict()
    assert od == {}

    od = ObjDict(d)
    assert od == d
    assert od['a'] == 1

    # Test methods
    od.update({"a": 2, "d": 4})
    od.update(key="value")
    assert od == {"a": 2, "b": 2, "c": 3, "d": 4, "key": "value"}
    assert od.copy() is not od
    assert od.copy() == od

    # Test loop reference
    d = {}
    d['d'] = d
    od = ObjDict(d)
    assert od['d'] is od
    assert deepcopy(od)['d'] is not od

    d = {
        "list": [{"a": 1}, {"b": 2}, 2, 4],
        "dict": {"a": 1, "b": 2},
        "set": {1, 2, 3},
        "tuple": (1, 2, 3, {"a": 1}),
        "empty": {
            "list": [],
            "dict": {},
            "set": set(),
            "tuple": ()
        }
    }

    od = ObjDict(d)
    assert od == d


def test_objdict_extra():
    d = {
        'a': 0,
        'b': 1,
        'c': {
            123: 321,
            'str': str
        }
    }

    od = ObjDict(d)

    assert od.a == 0
    assert od.b == 1
    assert od.c[123] == 321
    assert od.c.str is str
    assert od.default is od.NotExist
    with pytest.raises(AttributeError):
        od.d

    od2 = ObjDict(d, recursive=False)
    assert type(od2.c) is dict

    # Test set attr
    od.d = 4
    assert od.d == 4
    with pytest.raises(AttributeError):
        od._starts_with_ = 1

    # Test default
    od.default = None
    assert od.not_a_key == None
    assert od.c.not_a_key == None
    od3 = ObjDict(od)
    assert od3.not_a_key == None
