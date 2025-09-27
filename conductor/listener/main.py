import sys
import os
from fastapi import FastAPI, Request

# Adjust path to import from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.screenshotter.main import trigger_screenshot

app = FastAPI()

@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Receives a webhook notification (e.g., from WhatsApp) and
    triggers the screenshot process.
    """
    data = await request.json()
    chat_id = data.get("chat_id")

    if not chat_id:
        return {"status": "error", "message": "chat_id is required"}, 400

    print(f"LISTENER: Received webhook for chat_id: {chat_id}")

    # Trigger the screenshotter
    trigger_screenshot(chat_id)

    return {"status": "ok", "message": f"Screenshot process triggered for chat_id: {chat_id}"}

@app.get("/")
def read_root():
    return {"message": "Conductor Listener is running."}