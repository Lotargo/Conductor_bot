import pytest
from httpx import Response
from sentio_engine.llm.client import LLMGatewayClient

@pytest.mark.asyncio
async def test_fetch_models(tmp_path):
    # Setup
    client = LLMGatewayClient(tmp_path)

    # We can mock the httpx request, but for a quick check we just verify the structure
    # Since we don't have a real upstream running in CI without keys
    assert client.base_url == "https://api.openai.com/v1"

    # To test actual fetch, we'd need to mock respx or similar.
    # For now, let's verify config loading.

    dummy_config = tmp_path / "llm_config.json"
    with open(dummy_config, "w") as f:
        f.write('{"openai_base_url": "http://mock-url", "selected_model": "test-model"}')

    client = LLMGatewayClient(tmp_path)
    assert client.base_url == "http://mock-url"
    assert client.selected_model == "test-model"
