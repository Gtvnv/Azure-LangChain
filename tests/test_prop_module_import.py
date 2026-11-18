"""Propriedade 16: a checagem de import do módulo segue a regra de import no nível superior."""

from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.validator import validate_module_import

_FIRST = st.sampled_from(list("abcxyzABCXYZ_"))
_REST = st.text(st.sampled_from(list("abcxyzABCXYZ0123456789_")), max_size=15)
_names = st.builds(lambda a, b: a + b, _FIRST, _REST).filter(
    lambda s: s not in {"pytest", "os", "sys"}
    and not __import__("keyword").iskeyword(s)
)
_pairs = st.tuples(_names, _names).filter(lambda p: p[0] != p[1])

_BASE = "import pytest\n\n\ndef test_x():\n    with pytest.raises(ValueError):\n        raise ValueError()\n"


# Feature: pytest-test-generator-agent, Property 16: Module import check matches the top-level import rule
# **Validates: Requirements 3.11**
@settings(max_examples=100, deadline=None)
@given(_names)
def test_top_level_from_import_accepted(name):
    content = f"import pytest\nfrom {name} import f\n\n" + _BASE.split("\n\n", 1)[1]
    assert validate_module_import(content, name).ok


# Feature: pytest-test-generator-agent, Property 16: Module import check matches the top-level import rule
# **Validates: Requirements 3.11**
@settings(max_examples=100, deadline=None)
@given(_names)
def test_import_only_in_function_rejected(name):
    content = _BASE + f"\n\ndef helper():\n    from {name} import f\n    return f\n"
    result = validate_module_import(content, name)
    assert not result.ok
    assert f"from {name} import" in result.error


# Feature: pytest-test-generator-agent, Property 16: Module import check matches the top-level import rule
# **Validates: Requirements 3.11**
@settings(max_examples=100, deadline=None)
@given(_names)
def test_plain_import_rejected(name):
    assert not validate_module_import(f"import pytest\nimport {name}\n", name).ok


# Feature: pytest-test-generator-agent, Property 16: Module import check matches the top-level import rule
# **Validates: Requirements 3.11**
@settings(max_examples=100, deadline=None)
@given(_pairs)
def test_other_module_rejected(pair):
    name, other = pair
    assert not validate_module_import(f"import pytest\nfrom {other} import f\n", name).ok


# Feature: pytest-test-generator-agent, Property 16: Module import check matches the top-level import rule
# **Validates: Requirements 3.11**
@settings(max_examples=100, deadline=None)
@given(_names, st.integers(min_value=1, max_value=3))
def test_relative_import_rejected(name, level):
    dots = "." * level
    assert not validate_module_import(f"import pytest\nfrom {dots}{name} import f\n", name).ok
