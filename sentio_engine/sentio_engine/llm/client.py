import httpx
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from sentio_engine.personas.manager import PersonaManager

logger = logging.getLogger(__name__)

class LLMGatewayClient:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_path = config_dir / "llm_config.json"
        self._load_config()
        self.persona_manager = PersonaManager(config_dir)

    def _load_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load LLM config: {e}")
            self.config = {}

    @property
    def base_url(self) -> str:
        return self.config.get("openai_base_url", "https://api.openai.com/v1")

    @property
    def api_key(self) -> str:
        return self.config.get("openai_api_key", "")

    @property
    def selected_model(self) -> str:
        return self.config.get("selected_model", "gpt-3.5-turbo")

    @property
    def subconscious_model(self) -> str:
        return self.config.get("subconscious_model", self.selected_model)

    async def fetch_models(self) -> List[str]:
        """
        Fetches available models from the upstream gateway and saves them.
        """
        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                # Assume standard OpenAI format: {"data": [{"id": "model-id", ...}]}
                models = [m["id"] for m in data.get("data", [])]

                # Save to file
                output_path = self.config_dir / "available_models.json"
                with open(output_path, "w") as f:
                    json.dump({"models": models, "updated_at": str(response.headers.get("date"))}, f, indent=2)

                logger.info(f"Fetched {len(models)} models and saved to {output_path}")
                return models

        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []

    async def chat_completion(self, messages: List[Dict], stream: bool = True):
        """
        Proxies a chat completion request.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.selected_model,
            "messages": messages,
            "stream": stream
        }

        async with httpx.AsyncClient() as client:
            if stream:
                async with client.stream("POST", url, json=payload, headers=headers, timeout=60.0) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk
            else:
                response = await client.post(url, json=payload, headers=headers, timeout=60.0)
                response.raise_for_status()
                yield response.content

    async def generate_emotional_reaction(self, current_state: Dict, chat_history: List[Dict], user_input: str) -> Dict[str, Any]:
        """
        Acts as the 'Gatekeeper' and 'Synthesizer'.
        Analyzes the input + history + current state to produce updated emotions and response instructions.
        Uses Dynamic Persona Manifest.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 1. Build Prompt using Persona Manager
        template, dynamic_behavior = self.persona_manager.build_system_prompt(current_state)

        # 2. Format Template
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-10:]])
        current_state_json = json.dumps(current_state, indent=2)

        system_prompt = template.format(
            current_state_json=current_state_json,
            history_text=history_text,
            user_input=user_input,
            dynamic_behavior=dynamic_behavior
        )

        payload = {
            "model": self.subconscious_model,
            "messages": [{"role": "system", "content": system_prompt}],
            "temperature": 0.7,
            "stream": False,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error in subconscious processing: {e}")
            return {"emotions": {}, "instruction": "Respond naturally."}
