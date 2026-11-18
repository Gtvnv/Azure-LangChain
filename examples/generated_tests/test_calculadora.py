import pytest

from calculadora import add, subtract


def test_add_positive_numbers():
    assert add(2, 3) == 5


def test_add_negative_numbers():
    assert add(-2, -3) == -5


def test_add_floats():
    assert add(0.5, 0.25) == pytest.approx(0.75)


def test_add_incompatible_types_raises_type_error():
    with pytest.raises(TypeError):
        add("a", 1)


def test_subtract_positive_numbers():
    assert subtract(5, 3) == 2


def test_subtract_resulting_in_negative():
    assert subtract(3, 5) == -2


def test_subtract_floats():
    assert subtract(0.75, 0.25) == pytest.approx(0.5)


def test_subtract_incompatible_types_raises_type_error():
    with pytest.raises(TypeError):
        subtract("a", 1)
