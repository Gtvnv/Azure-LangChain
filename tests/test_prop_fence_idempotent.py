from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.validator import extract_code

_fragments = st.sampled_from(
    ["```", "```python", "import pytest", "import pytest  ", "def test_x():", "    pass", "texto", ""]
)
_structured = st.lists(
    st.one_of(_fragments, st.text(max_size=20)), max_size=10
).flatmap(
    lambda parts: st.sampled_from(["\n", "\r\n", "\r"]).map(lambda sep: sep.join(parts))
)
_texts = st.one_of(st.text(), _structured)
_fence_wrapped = st.builds(
    lambda prefix, tag, body: f"{prefix}\n```{tag}\n{body}\n```\n",
    st.text(max_size=30),
    st.sampled_from(["", "python", "py"]),
    _texts,
)


# Feature: pytest-test-generator-agent, Property 14: Fence extraction is idempotent
# **Validates: Requirements 9.5**
@settings(max_examples=200)
@given(raw=st.one_of(_texts, _fence_wrapped))
def test_extract_code_is_idempotent(raw):
    once = extract_code(raw)

    assert extract_code(once) == once
