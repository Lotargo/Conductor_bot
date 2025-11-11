
# Chatbot Application for Sentio Engine & IndexTTS2 Integration

This directory contains a Gradio-based chatbot application designed to test the integration between the Sentio Engine and the IndexTTS2 speech synthesis model.

## Features

- A simple chat interface.
- Integration with a running Sentio Engine instance to manage the bot's emotional state.
- A toggle to enable/disable Text-to-Speech (TTS) output.
- Uses a mock TTS model (`tts_adapter.py`) for development in CPU-only environments. The real `IndexTTS2` can be swapped in when a GPU is available.

## Setup and Installation

1.  **Install Dependencies**: Before running the application, ensure you have installed all the required Python packages. From the `chatbot_app` directory, run:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Ensure Sentio Engine is Running**: This application requires the Sentio Engine API to be running and accessible at `http://127.0.0.1:8000`. You can run it locally using `poetry` from the `sentio_engine` directory:

    ```bash
    cd ../sentio_engine
    TESTING=true poetry run uvicorn sentio_engine.api.main:app --host 0.0.0.0 --port 8000 &
    ```

## How to Run

Once the dependencies are installed and the Sentio Engine is running, you can start the chatbot application:

```bash
python app.py
```

This will launch a Gradio web server. Open the URL provided in your terminal (usually `http://127.0.0.1:7860`) in your web browser to interact with the chatbot.
