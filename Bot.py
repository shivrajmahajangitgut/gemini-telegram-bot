import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telegram
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
    # Render binds to port 10000 by default, falls back to 8080
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"Dummy web server running on port {port}")
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
    
    # Initialize chat session if it does not exist
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
        
    try:
        # Generate response from Gemini
        response = user_chats[user_id].send_message(user_text)
        ai_response_text = response.text
        
        try:
            # Attempt normal reply to the user's message
            await update.message.reply_text(ai_response_text)
        except telegram.error.BadRequest as telegram_err:
            # If Render restarted and lost track of the original message, send a direct chat message instead
            if "Message to be replied not found" in str(telegram_err):
                await context.bot.send_message(chat_id=user_id, text=ai_response_text)
            else:
                raise telegram_err  # Re-throw if it is a different BadRequest error
                
    except Exception as e:
        print(f"Error encountered: {e}")
        try:
            await update.message.reply_text("Sorry, I had trouble processing that request.")
        except Exception:
            pass

# --- 3. MAIN RUNNER ---
def main():
    # Start the dummy web server in a separate thread so Render is happy
    threading.Thread(target=run_web_server, daemon=True).start()

    # Fetch token from environment variables
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("CRITICAL ERROR: TELEGRAM_TOKEN environment variable is missing!")
        return

    # Build the application
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is up and listening...")
    
    # drop_pending_updates=True clears the message queue on startup, fixing the loop error
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
  
