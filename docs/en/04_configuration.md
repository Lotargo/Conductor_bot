# Personality Configuration

The personality of the Sentio Engine is not hard-coded. Instead, it is defined by a set of simple JSON configuration files located in the `sentio_engine/config` directory. This allows for deep customization and experimentation without changing any code.

## `emotions.json`

This is the most critical configuration file. It defines the emotional palette of the AI.

### Structure

The file contains a single top-level key, `definitions`, which is an object where each key is the name of an emotion.

```json
{
  "definitions": {
    "joy": {
      "base_intensity": 0.1,
      "decay_rate": 0.95
    },
    "sadness": {
      "base_intensity": 0.05,
      "decay_rate": 0.98
    }
  }
}
```

### Parameters

*   **`base_intensity`** (float, 0.0 to 1.0):
    *   This is the emotion's "resting state" or baseline level.
    *   When no stimuli are present, the emotion's intensity will gradually return to this value.
    *   A high `base_intensity` can represent a generally cheerful or melancholic personality.

*   **`decay_rate`** (float, 0.0 to 1.0):
    *   This controls how "sticky" an emotion is. It determines the percentage of the emotion's intensity (above its baseline) that remains after each "tick" or processing cycle.
    *   A value close to `1.0` (e.g., `0.99`) means the emotion is very persistent and fades slowly.
    *   A value closer to `0.0` (e.g., `0.5`) means the emotion is fleeting and disappears quickly.

## `drives.json` (Future Extension)

This file is designed for a future extension to model the core motivations or "drives" of the AI. While not fully implemented in the core logic yet, the structure is planned as follows.

### Planned Structure

```json
{
  "definitions": {
    "curiosity": {
      "base_level": 0.8,
      "target_emotions": ["interest", "anticipation"]
    },
    "social_connection": {
      "base_level": 0.6,
      "target_emotions": ["joy", "trust"]
    }
  }
}
```

### Planned Parameters

*   **`base_level`**: The fundamental strength of the drive.
*   **`target_emotions`**: A list of emotions that this drive seeks to experience. An unfulfilled drive could, for example, amplify the intensity of stimuli related to its target emotions.

By modifying these files, you can create a wide range of AI personalities, from stoic and calm to volatile and passionate.

---

**Next:** [Integration Guide](./05_integration_guide.md)
