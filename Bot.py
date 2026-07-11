import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# --- 1. DUMMY WEB SERVER FOR RENDER ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

# --- 2. GEMINI AI CONFIGURATION ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
user_chats = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    user_text = update.message.text
    
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
        
    try:
        response = user_chats[user_id].send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Gemini Error: {e}")
        await update.message.reply_text("Sorry, I had trouble processing that request.")

# --- 3. MAIN RUNNER ---
def main():
    # Start the dummy web server in a separate thread so Render is happy
    threading.Thread(target=run_web_server, daemon=True).start()

    # Start Telegram Bot
    token = os.environ.get("TELEGRAM_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is up and listening...")
    app.run_polling()

if __name__ == '__main__':
    main()
