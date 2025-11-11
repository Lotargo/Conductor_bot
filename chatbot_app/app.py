
import gradio as gr
import requests
import json
import logging
import os
from tts_adapter import MockIndexTTS2, convert_sentio_to_tts_vector, REAL_TTS_AVAILABLE

# --- Configuration ---
SENTIO_ENGINE_URL = "http://127.0.0.1:8000"
USE_MOCK_TTS = os.environ.get("USE_MOCK_TTS", "true").lower() == "true"
logging.basicConfig(level=logging.INFO)

# --- Initialize TTS Model ---
tts_model = None
if USE_MOCK_TTS:
    logging.info("Using Mock TTS model as per environment variable.")
    tts_model = MockIndexTTS2()
elif REAL_TTS_AVAILABLE:
    logging.info("Attempting to initialize REAL IndexTTS2 model...")
    try:
        from tts_adapter import IndexTTS2
        # Assumes the checkpoints are in the indextts2 directory
        indextts2_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'indextts2'))
        tts_model = IndexTTS2(
            cfg_path=os.path.join(indextts2_dir, "checkpoints/config.yaml"),
            model_dir=os.path.join(indextts2_dir, "checkpoints"),
            use_fp16=True # Recommended for better performance
        )
        logging.info("Real IndexTTS2 model initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize real IndexTTS2 model: {e}. Falling back to mock.", exc_info=True)
        tts_model = MockIndexTTS2()
else:
    logging.warning("Real TTS is not available and mock is disabled. TTS functionality will not work.")
    tts_model = None


# --- Sentio Engine API Interaction ---
def get_sentio_report():
    """Fetches the latest emotional report from Sentio Engine."""
    try:
        response = requests.get(f"{SENTIO_ENGINE_URL}/report")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching report from Sentio Engine: {e}")
        return None

def send_sentio_stimulus(message):
    """Sends a stimulus to Sentio Engine based on the user's message."""
    stimulus = {
        "source": "user_chatbot_message", "type": "text", "content": message, "intensity": 0.5,
        "emotion_map": {
            "радость": ["happy", "joy", "great"], "грусть": ["sad", "sorry", "bad"],
            "злость": ["angry", "hate", "stupid"]
        }
    }
    try:
        response = requests.post(f"{SENTIO_ENGINE_URL}/stimulus", json=stimulus)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending stimulus to Sentio Engine: {e}")
        return None

# --- Chatbot Logic ---
def chatbot_response(message, history, enable_tts):
    send_sentio_stimulus(message)
    report = get_sentio_report()
    if not report:
        return "Sorry, I couldn't connect to my emotional core.", None

    emotions = report.get('emotions', {})
    dominant_emotion = max(emotions, key=lambda e: emotions[e]['intensity']) if emotions else "neutral"
    text_response = f"Feeling {dominant_emotion}. You said: {message}"

    audio_output = None
    if enable_tts and tts_model:
        logging.info("TTS is enabled. Synthesizing speech...")
        emotion_vector = convert_sentio_to_tts_vector(report)

        # This will now use either the real or the mock model
        audio_output_path = tts_model.infer(
            text=text_response, emo_vector=emotion_vector,
            # Placeholder for speaker prompt, required by the real model
            spk_audio_prompt=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'indextts2', 'examples', 'voice_01.wav')),
            output_path="chatbot_response.wav"
        )
        audio_output = audio_output_path
        logging.info(f"Generated audio path: {audio_output}")

    return text_response, audio_output

# --- Gradio Interface ---
with gr.Blocks() as iface:
    gr.Markdown("# Sentio Engine & IndexTTS2 Integration Demo")

    with gr.Row():
        chatbot = gr.Chatbot(label="Chat History", height=500)
    with gr.Row():
        msg_input = gr.Textbox(label="Your Message", placeholder="Type your message here...", scale=4)
        tts_checkbox = gr.Checkbox(label="Enable TTS", value=False, scale=1)
    with gr.Row():
        audio_player = gr.Audio(label="Synthesized Speech", type="filepath", interactive=False)

    def handle_submit(message, history, enable_tts):
        text_resp, audio_resp = chatbot_response(message, history, enable_tts)
        history.append((message, text_resp))
        return history, "", audio_resp or None

    msg_input.submit(fn=handle_submit, inputs=[msg_input, chatbot, tts_checkbox], outputs=[chatbot, msg_input, audio_player])

if __name__ == "__main__":
    iface.launch(share=False)
