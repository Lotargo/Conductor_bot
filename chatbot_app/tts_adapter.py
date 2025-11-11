
import logging
import os
import wave
import numpy as np
import sys

# Attempt to import the real IndexTTS2. If it fails, we'll rely on the mock.
try:
    # We need to add the indextts2 directory to the path to find the module
    # Assumes indextts2 is in the parent directory of chatbot_app
    indextts2_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'indextts2'))
    if indextts2_path not in sys.path:
        sys.path.append(indextts2_path)
    from indextts.infer_v2 import IndexTTS2
    REAL_TTS_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    logging.warning("Could not import real IndexTTS2. TTS functionality will be mocked.")
    # Define a dummy class if the real one is not available
    class IndexTTS2:
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("Real IndexTTS2 model is not available.")
    REAL_TTS_AVAILABLE = False


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
            sample_rate = 16000
            duration = 1
            n_samples = int(sample_rate * duration)
            audio_data = np.zeros(n_samples, dtype=np.int16)

            with wave.open(self.dummy_audio_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data.tobytes())

    def infer(self, text, emo_vector, output_path, **kwargs):
        """
        Simulates the inference process.
        """
        logging.info(f"Mock TTS Inference Called:")
        logging.info(f"  - Text: '{text}'")
        logging.info(f"  - Emotion Vector: {emo_vector}")
        return self.dummy_audio_path


def convert_sentio_to_tts_vector(sentio_report):
    """
    Converts a Sentio Engine report into an 8-dimensional emotion vector for IndexTTS2.
    """
    emotions = sentio_report.get('emotions', {})
    emotion_map = {
        'радость': 0, 'злость': 1, 'грусть': 2, 'страх': 3,
        'отвращение': 4, 'удивление': 6
    }
    calm_emotions = ['доверие', 'ожидание']
    tts_vector = [0.0] * 8

    for emotion_name, properties in emotions.items():
        intensity = properties.get('intensity', 0.0)
        if emotion_name in emotion_map:
            tts_vector[emotion_map[emotion_name]] = intensity
        elif emotion_name in calm_emotions:
            tts_vector[7] += intensity * 0.5

    tts_vector[7] = max(0.0, min(1.0, tts_vector[7]))
    return tts_vector
