
import gradio as gr
import requests
import json
import logging
from tts_adapter import MockIndexTTS2, convert_sentio_to_tts_vector
import time
import os

# --- Configuration ---
SENTIO_ENGINE_URL = "http://127.0.0.1:8000"
logging.basicConfig(level=logging.INFO)

# --- Initialize TTS Model (Mock) ---
# We need to make sure the dummy wav is created in the correct directory
# so the gradio app can find it.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    tts_model = MockIndexTTS2()
except Exception as e:
    logging.error(f"Failed to initialize TTS model: {e}")
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
        "source": "user_chatbot_message",
        "type": "text",
        "content": message,
        "intensity": 0.5,
        "emotion_map": {
            "радость": ["happy", "joy", "great"],
            "грусть": ["sad", "sorry", "bad"],
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
    """
    Main function to handle user interaction, Sentio Engine integration, and TTS.
    """
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

        audio_output_path = tts_model.infer(
            text=text_response,
            emo_vector=emotion_vector,
            output_path="chatbot_response.wav"
        )
        audio_output = audio_output_path
        logging.info(f"Generated audio path: {audio_output}")

    return text_response, audio_output

# --- Gradio Interface ---
with gr.Blocks() as iface:
    gr.Markdown("# Sentio Engine & IndexTTS2 Integration Demo")
    gr.Markdown("A chatbot that uses Sentio Engine for its emotional state and IndexTTS2 for speech synthesis.")

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

    msg_input.submit(
        fn=handle_submit,
        inputs=[msg_input, chatbot, tts_checkbox],
        outputs=[chatbot, msg_input, audio_player]
    )

if __name__ == "__main__":
    try:
        iface.launch(share=False)
    except Exception as e:
        logging.error(f"Failed to launch Gradio interface: {e}", exc_info=True)
