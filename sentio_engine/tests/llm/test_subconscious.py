import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from sentio_engine.llm.client import LLMGatewayClient

@pytest.mark.asyncio
async def test_generate_emotional_reaction(tmp_path):
    # Setup Config
    config_file = tmp_path / "llm_config.json"
    with open(config_file, "w") as f:
        json.dump({"openai_api_key": "test"}, f)

    client = LLMGatewayClient(tmp_path)

    # Mock Response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"emotions": {"joy": 0.8}, "instruction": "Be happy!"}'
            }
        }]
    }
    mock_response.raise_for_status = MagicMock()

    # Mock Client Instance
    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = mock_response

    # Mock Constructor
    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", mock_client_cls):
        state = {"joy": 0.5}
        history = [{"role": "user", "content": "Hello"}]

        result = await client.generate_emotional_reaction(state, history, "I am happy")

        assert result["emotions"]["joy"] == 0.8
        assert result["instruction"] == "Be happy!"

        # Verify call
        mock_client_instance.post.assert_awaited_once()
