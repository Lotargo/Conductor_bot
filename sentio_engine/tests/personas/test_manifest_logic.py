import pytest
from pathlib import Path
from sentio_engine.personas.manager import PersonaManager

def test_persona_manager_loading_custom(tmp_path):
    # Setup dummy persona
    persona_dir = tmp_path / "personas" / "test_persona"
    persona_dir.mkdir(parents=True)

    (persona_dir / "system_prompt.txt").write_text("Prompt: {dynamic_behavior}", encoding="utf-8")

    manifest_code = """
def resolve_behavior(state):
    if state.get('joy', 0) > 0.5:
        return "Be happy"
    return "Be neutral"
"""
    (persona_dir / "manifest.py").write_text(manifest_code, encoding="utf-8")

    manager = PersonaManager(tmp_path)
    manager.set_active_persona("test_persona")

    # Test High Joy
    template, behavior = manager.build_system_prompt({"joy": 0.9})
    assert template == "Prompt: {dynamic_behavior}"
    assert behavior == "Be happy"

def test_default_persona_integration():
    # Attempt to locate the real config directory
    # Assumes running from 'sentio_engine' directory
    current_dir = Path.cwd()
    config_dir = current_dir / "config"

    if not (config_dir / "personas").exists():
        pytest.skip(f"Config directory not found at {config_dir}, skipping integration test")

    manager = PersonaManager(config_dir)
    manager.set_active_persona("default")

    # Test Anger Logic from default manifest
    template, behavior = manager.build_system_prompt({"anger": 0.9})
    assert "CRITICAL: You are furious" in behavior

    # Test Sadness
    _, behavior = manager.build_system_prompt({"sadness": 0.9})
    assert "deep despair" in behavior
