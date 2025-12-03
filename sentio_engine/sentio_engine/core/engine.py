import json
import datetime
import logging
from pathlib import Path
from typing import List, Optional

from sentio_engine.schemas.sentio_pb2 import EmotionalState, Stimulus, Report

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentioEngine:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._load_configuration()
        # Note: self.state is removed. The engine is now stateless.

    def _load_configuration(self):
        """Loads personality configuration from JSON files."""
        try:
            with open(self.config_path / "emotions.json", "r", encoding="utf-8") as f:
                self.emotion_definitions = json.load(f)["definitions"]
            with open(self.config_path / "drives.json", "r", encoding="utf-8") as f:
                self.drive_definitions = json.load(f)["definitions"]
            with open(self.config_path / "engine_settings.json", "r", encoding="utf-8") as f:
                self.engine_settings = json.load(f)
            with open(self.config_path / "feelings.json", "r", encoding="utf-8") as f:
                self.feelings_definitions = json.load(f)
            with open(self.config_path / "BeliefSystem.json", "r", encoding="utf-8") as f:
                self.belief_system = json.load(f)["personality"]
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON configuration: {e}")
            raise

    def create_initial_state(self) -> EmotionalState:
        """Creates a fresh EmotionalState with default values."""
        state = EmotionalState()
        for emotion, params in self.emotion_definitions.items():
            state.emotions[emotion] = params["base_intensity"]
        self._update_primary_mood(state)
        state.cause = "System initialization."
        return state

    def _update_primary_mood(self, state: EmotionalState):
        """Determines the dominant mood based on current emotions."""
        if not state.emotions:
            state.primary_mood = "neutral"
            return

        primary_emotion = max(state.emotions, key=state.emotions.get)
        state.primary_mood = f"dominating {primary_emotion}"

    def _synchronize_decay(self, state: EmotionalState, last_update_time: datetime.datetime) -> datetime.datetime:
        """
        Applies time-based decay to emotions.
        Returns the new 'last_update_timestamp'.
        """
        now = datetime.datetime.utcnow()

        # If last_update_time is None (new state), just return now
        if last_update_time is None:
            return now

        time_elapsed = now - last_update_time
        tick_seconds = self.engine_settings.get("simulation_tick_seconds", 60)

        if tick_seconds <= 0:
             return now

        steps_to_simulate = int(time_elapsed.total_seconds() / tick_seconds)

        if steps_to_simulate > 0:
            for _ in range(steps_to_simulate):
                self._decay_emotions(state)

            # Update timestamp to now after simulation
            return now

        return last_update_time

    def process_stimulus(self, state: EmotionalState, stimulus: Stimulus, last_update_time: datetime.datetime) -> datetime.datetime:
        """
        Processes an incoming stimulus, updates the provided state.
        Returns the new update timestamp.
        """
        # 1. Catch up with time decay
        new_timestamp = self._synchronize_decay(state, last_update_time)

        cause_text = "Unknown stimulus"
        if stimulus.emotions:
            top_stimulus = max(stimulus.emotions, key=stimulus.emotions.get)
            cause_text = f"Reaction to stimulus: {top_stimulus}"

        state.cause = cause_text

        # 2. Apply stimulus
        for emotion, intensity in stimulus.emotions.items():
            if emotion in state.emotions:
                modifier = self._calculate_personality_modifier(emotion)
                modified_intensity = intensity * modifier

                state.emotions[emotion] += modified_intensity
                state.emotions[emotion] = max(0.0, min(1.0, state.emotions[emotion]))

                # TODO: Log to History (DB layer should handle this separately or we return a log object)
                # For now, we rely on the state being updated.

        # 3. Apply mechanics
        self._apply_dominance(state)
        self._update_primary_mood(state)

        return new_timestamp

    def _calculate_personality_modifier(self, emotion: str) -> float:
        """Calculates stimulus multiplier based on personality traits."""
        emotion_def = self.emotion_definitions.get(emotion, {})
        influences = emotion_def.get("personality_influence", {})
        if not influences:
            return 1.0

        total_modifier = 1.0
        for trait, factor in influences.items():
            trait_value = self.belief_system.get(trait, {}).get("value", 0.5)
            modifier_effect = (trait_value - 0.5) * (factor - 1.0)
            total_modifier += modifier_effect

        return max(0.1, total_modifier)

    def _apply_dominance(self, state: EmotionalState):
        """Applies dominance suppression (stronger emotion suppresses opposite)."""
        dominance_factor = self.engine_settings.get("dominance_factor", 0.5)
        processed_emotions = set()

        # We iterate over a copy of keys to modify the state safely
        for emotion in list(state.emotions.keys()):
            if emotion in processed_emotions:
                continue

            intensity = state.emotions[emotion]
            definition = self.emotion_definitions.get(emotion, {})
            opposite_emotion = definition.get("opposite")

            if not opposite_emotion or opposite_emotion not in state.emotions:
                continue

            opposite_intensity = state.emotions[opposite_emotion]

            if intensity > opposite_intensity:
                suppression = intensity * dominance_factor
                state.emotions[opposite_emotion] = max(0.0, opposite_intensity - suppression)
            elif opposite_intensity > intensity:
                suppression = opposite_intensity * dominance_factor
                state.emotions[emotion] = max(0.0, intensity - suppression)

            processed_emotions.add(emotion)
            processed_emotions.add(opposite_emotion)

    def _decay_emotions(self, state: EmotionalState):
        """Simulates gradual emotion decay."""
        emotions_snapshot = dict(state.emotions)

        for emotion, intensity in emotions_snapshot.items():
            decay_rate = self.emotion_definitions.get(emotion, {}).get("decay_rate", 0.99)
            base_intensity = self.emotion_definitions.get(emotion, {}).get("base_intensity", 0.0)

            new_intensity = base_intensity + (intensity - base_intensity) * decay_rate
            state.emotions[emotion] = new_intensity

        self._apply_dominance(state)

    def _evaluate_complex_states(self, state: EmotionalState, history_provider=None) -> List[str]:
        """
        Analyzes emotional history to identify complex feelings.
        Note: logic requires history. If history_provider is None, returns empty.
        history_provider should be a callable: (start_time, end_time) -> List[EmotionalHistoryEntry]
        """
        # Since we decoupled DB, we can't query history directly here easily without an interface.
        # For this refactor, we will temporarily disable complex states or require a provider.
        # Given the scope, I'll return empty list or implement a basic check based on current state if possible,
        # but complex states definition relies on time window.

        # Placeholder for now.
        return []

    def get_report(self, state: EmotionalState, last_update_time: datetime.datetime) -> Report:
        """Generates a report from the given state."""
        # Sync decay first to make sure report is up to date
        self._synchronize_decay(state, last_update_time)

        report = Report()
        report.emotional_state.CopyFrom(state)
        # report.complex_states.extend(self._evaluate_complex_states(state))
        return report
