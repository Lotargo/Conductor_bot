import importlib.util
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class PersonaManager:
    """
    Manages loading and resolving dynamic personas.
    """
    def __init__(self, config_dir: Path):
        self.personas_dir = config_dir / "personas"
        self.active_persona = "default"
        self._cache = {}

    def set_active_persona(self, persona_name: str):
        if not (self.personas_dir / persona_name).exists():
            logger.warning(f"Persona '{persona_name}' not found. Keeping '{self.active_persona}'.")
            return
        self.active_persona = persona_name

    def _load_module(self, persona_name: str):
        """Dynamically loads the manifest.py module for a persona."""
        if persona_name in self._cache:
            return self._cache[persona_name]

        manifest_path = self.personas_dir / persona_name / "manifest.py"
        prompt_path = self.personas_dir / persona_name / "system_prompt.txt"

        if not manifest_path.exists() or not prompt_path.exists():
            raise FileNotFoundError(f"Missing manifest.py or system_prompt.txt for persona '{persona_name}'")

        # Load Text
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt_template = f.read()

        # Load Module
        spec = importlib.util.spec_from_file_location(f"persona_{persona_name}", manifest_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        persona_data = {
            "template": system_prompt_template,
            "module": module
        }
        self._cache[persona_name] = persona_data
        return persona_data

    def build_system_prompt(self, emotional_state: dict) -> str:
        """
        Constructs the final system prompt by running the python manifest logic.
        """
        try:
            persona = self._load_module(self.active_persona)

            # Execute Python Logic
            # We pass the raw dict of emotions
            dynamic_behavior = persona["module"].resolve_behavior(emotional_state)

            # Fill Template
            # Note: The caller (LLM Client) will still need to format the REST of the fields (history, etc)
            # Or we can return a partial format string.
            # Ideally, we return the FULL template, but with the {dynamic_behavior} slot filled.
            # The LLM Client expects: {current_state_json}, {history_text}, {user_input}

            # Since we are using format(), we need to be careful about double braces in the text file
            # if we want to leave some placeholders for later.
            # My system_prompt.txt uses {current_state_json}, etc.
            # So here we ONLY format the 'dynamic_behavior' part if it exists in the template?
            # Actually, standard python format() will error if we don't provide all keys.

            # Strategy: We return the template string AND the resolved behavior string.
            # The LLM Client will combine them.

            return persona["template"], dynamic_behavior

        except Exception as e:
            logger.error(f"Error building prompt for persona '{self.active_persona}': {e}")
            # Fallback
            return "You are an AI assistant.", "Be nice."
