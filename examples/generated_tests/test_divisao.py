import pytest

from divisao import divide


def test_divide_positive_numbers():
    assert divide(10, 2) == 5


def test_divide_negative_numbers():
    assert divide(-10, 2) == -5


def test_divide_floats():
    assert divide(1, 4) == pytest.approx(0.25)


def test_divide_zero_dividend():
    assert divide(0, 5) == 0


def test_divide_by_zero_raises_value_error():
    with pytest.raises(ValueError):
        divide(1, 0)
