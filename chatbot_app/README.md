
# Chatbot Application for Sentio Engine & IndexTTS2 Integration

This directory contains a Gradio-based chatbot application designed to test the integration between the Sentio Engine and the IndexTTS2 speech synthesis model.

## Features

- A simple chat interface.
- Integration with a running Sentio Engine instance to manage the bot's emotional state.
- A toggle to enable/disable Text-to-Speech (TTS) output.
- **Flexible TTS Backend**: The application can switch between a real `IndexTTS2` model (for GPU environments) and a mock model (for CPU-only development).

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

3. **(Optional) Set up IndexTTS2**: If you have a GPU and wish to use the real speech synthesis model, please follow the setup instructions in the `../indextts2/README.md` file to install the environment and download the models.

## How to Run

Once the dependencies are installed and the Sentio Engine is running, you can start the chatbot application.

### Using the Mock TTS (Recommended for CPU-only environments)

By default, the application uses a mock TTS model that simulates speech synthesis without requiring a GPU.

```bash
cd chatbot_app
python app.py
```

### Using the Real IndexTTS2 Model (Requires GPU)

To use the real `IndexTTS2` model, first ensure you have completed step 3 of the setup. Then, unset the `USE_MOCK_TTS` environment variable before running the app:

```bash
cd chatbot_app
export USE_MOCK_TTS=false
python app.py
```

The application will then attempt to load the real models from the `../indextts2` directory.

---

This will launch a Gradio web server. Open the URL provided in your terminal (usually `http://127.0.0.1:7860`) in your web browser to interact with the chatbot.
