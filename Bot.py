import os
import requests
from fastapi import FastAPI, Request, HTTPException
from google import genai

app = FastAPI()

# Render injects these automatically from your Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize official Google Gen AI Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)
TELEGRAM_API_URL = f"https://telegram.org{TELEGRAM_TOKEN}"

def get_gemini_response(user_text: str) -> str:
    """Sends user text to Gemini 2.5 Flash and returns the text reply."""
    try:
        # Using Google's highly efficient gemini-2.5-flash model
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_text,
        )
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "Sorry, I am having trouble thinking right now."

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Listens for incoming webhooks sent by Telegram."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON data")

    # Filter incoming payload for text updates from a user chat
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]

        # 1. Fetch AI Response
        ai_reply = get_gemini_response(user_text)

        # 2. Forward the response to the Telegram User
        send_url = f"{TELEGRAM_API_URL}/sendMessage"
        send_payload = {"chat_id": chat_id, "text": ai_reply}
        
        try:
            requests.post(send_url, json=send_payload, timeout=5)
        except Exception as e:
            print(f"Telegram Send Error: {e}")

    return {"status": "success"}

@app.get("/")
def home():
    """Health check endpoint to verify the Render service is running."""
    return {"message": "Telegram Bot is running live via Webhook with Gemini!"}
          
