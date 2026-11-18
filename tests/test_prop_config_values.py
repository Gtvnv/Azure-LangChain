from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.config import REQUIRED_VARS, AzureConfig, load_config

non_blank = st.text().filter(lambda s: s.strip() != "")


# Feature: pytest-test-generator-agent, Property 10: Config loading returns the supplied values
# **Validates: Requirements 5.1**
@settings(max_examples=100)
@given(api_key=non_blank, endpoint=non_blank, api_version=non_blank, deployment=non_blank)
def test_load_config_returns_supplied_values(api_key, endpoint, api_version, deployment):
    env = dict(zip(REQUIRED_VARS, (api_key, endpoint, api_version, deployment)))

    config = load_config(env)

    assert isinstance(config, AzureConfig)
    assert config.api_key == api_key
    assert config.endpoint == endpoint
    assert config.api_version == api_version
    assert config.deployment_name == deployment
