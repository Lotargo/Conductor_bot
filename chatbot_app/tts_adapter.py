
import logging
import os
import wave
import numpy as np

logging.basicConfig(level=logging.INFO)

class MockIndexTTS2:
    """
    A mock class that simulates the IndexTTS2 model for development purposes
    in a CPU-only environment.
    """
    def __init__(self, *args, **kwargs):
        logging.info("Initializing MockIndexTTS2...")
        self.dummy_audio_path = "dummy_output.wav"
        self._create_dummy_wav()

    def _create_dummy_wav(self):
        """Creates a short, silent WAV file to be used as a placeholder."""
        if not os.path.exists(self.dummy_audio_path):
            logging.info(f"Creating dummy WAV file at: {self.dummy_audio_path}")
            sample_rate = 16000  # 16kHz
            duration = 1  # 1 second
            n_samples = int(sample_rate * duration)
            audio_data = np.zeros(n_samples, dtype=np.int16)

            with wave.open(self.dummy_audio_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data.tobytes())

    def infer(self, text, emo_vector, output_path, **kwargs):
        """
        Simulates the inference process. Logs the inputs and returns the path
        to a dummy audio file.
        """
        logging.info(f"Mock TTS Inference Called:")
        logging.info(f"  - Text: '{text}'")
        logging.info(f"  - Emotion Vector: {emo_vector}")
        logging.info(f"  - Output Path: {output_path}")

        # In a real scenario, this would generate the audio. Here, we just
        # ensure the dummy file is our output. For simplicity, we will just return
        # the path to the pre-generated dummy file.
        return self.dummy_audio_path


def convert_sentio_to_tts_vector(sentio_report):
    """
    Converts a Sentio Engine report (as a dictionary) into an 8-dimensional
    emotion vector for IndexTTS2.

    IndexTTS2 emotion order: [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]
    """
    emotions = sentio_report.get('emotions', {})

    # Mapping from Sentio emotions to IndexTTS2 vector indices
    emotion_map = {
        'радость': 0,    # happy
        'злость': 1,     # angry
        'грусть': 2,     # sad
        'страх': 3,      # afraid
        'отвращение': 4, # disgusted
        'удивление': 6,  # surprised
    }

    # 'calm' is influenced by 'доверие' and 'ожидание'
    calm_emotions = ['доверие', 'ожидание']

    # Initialize the 8-dimensional vector with zeros
    tts_vector = [0.0] * 8

    # Melancholic is not in sentio, so it's always 0.
    # tts_vector[5] = 0.0

    for emotion_name, properties in emotions.items():
        intensity = properties.get('intensity', 0.0)

        if emotion_name in emotion_map:
            tts_vector[emotion_map[emotion_name]] = intensity
        elif emotion_name in calm_emotions:
            # Add to the 'calm' component. We can weigh them if needed.
            tts_vector[7] += intensity * 0.5  # Example: 50% weight for each

    # Normalize the calm component to be between 0.0 and 1.0
    tts_vector[7] = max(0.0, min(1.0, tts_vector[7]))

    return tts_vector

if __name__ == '__main__':
    # Example usage for testing the adapter logic

    # 1. Test the mock TTS
    mock_tts = MockIndexTTS2()
    mock_tts.infer("This is a test.", [0.8, 0.0, 0.1, 0, 0, 0, 0.2, 0.5], "test.wav")

    # 2. Test the emotion conversion
    sample_report = {
        "emotions": {
            "радость": {"intensity": 0.75, "base_intensity": 0.1, "decay_rate": 0.95},
            "грусть": {"intensity": 0.2, "base_intensity": 0.05, "decay_rate": 0.98},
            "доверие": {"intensity": 0.9, "base_intensity": 0.2, "decay_rate": 0.99}
        },
        "complex_states": ["contentment"]
    }

    vector = convert_sentio_to_tts_vector(sample_report)
    print(f"Sample Sentio Report: {sample_report}")
    print(f"Converted TTS Vector: {vector}")

    # Expected output: [0.75, 0.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.45]
    expected_vector = [0.75, 0.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.45]
    assert vector == expected_vector, f"Test failed: expected {expected_vector}, got {vector}"
    print("Emotion conversion test passed!")
