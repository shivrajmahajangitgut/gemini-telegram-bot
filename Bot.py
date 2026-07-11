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
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"Dummy web server running on port {port}")
    server.serve_forever()

# --- 2. GEMINI AI CONFIGURATION ---
gemini_key = os.environ.get("GEMINI_API_KEY")
if not gemini_key:
    print("CRITICAL ERROR: GEMINI_API_KEY environment variable is empty or not set in Render!")
else:
    print("Gemini API key loaded successfully.")

genai.configure(api_key=gemini_key)
model = genai.GenerativeModel('gemini-1.5-flash')
user_chats = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    user_text = update.message.text
    chat_type = update.message.chat.type  # 'private', 'group', or 'supergroup'
    bot_username = context.bot.username   # Fetches your bot's exact handle

    # --- GROUP PRIVACY SHIELD ---
    # Stops bot from replying to everything unless tagged in groups
    if chat_type in ["group", "supergroup"]:
        if f"@{bot_username}" not in user_text:
            return  # Completely ignore if the bot name isn't mentioned
        
        # Strip the tag so the AI doesn't process its own name
        user_text = user_text.replace(f"@{bot_username}", "").strip()

    # --- INITIALIZE CHAT SESSION ---
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
        
    ai_response_text = ""
    try:
        # Generate response from Gemini
        response = user_chats[user_id].send_message(user_text)
        
        if response and response.text:
            ai_response_text = response.text
        else:
            print("Gemini returned an empty response object.")
            ai_response_text = "Sorry, I generated an empty answer. Try rephrasing."
            
    except Exception as gemini_err:
        # If Render put the app to sleep and broke the session history, force reset it
        print(f"Gemini API Error: {gemini_err}")
        try:
            user_chats[user_id] = model.start_chat(history=[])
            response = user_chats[user_id].send_message(user_text)
            ai_response_text = response.text
        except Exception as retry_err:
            print(f"Critical Gemini breakdown: {retry_err}")
            ai_response_text = "Sorry, I am having trouble connecting to my brain right now."

    # --- SEND DELIVERABLE MESSAGE TO TELEGRAM ---
    try:
        await update.message.reply_text(ai_response_text)
    except telegram.error.BadRequest as telegram_err:
        # Fallback to direct messaging if Render lost track of the original message ID
        if "Message to be replied not found" in str(telegram_err):
            await context.bot.send_message(chat_id=update.message.chat_id, text=ai_response_text)
        else:
            print(f"Telegram Delivery Error: {telegram_err}")
    except Exception as e:
        print(f"General delivery crash: {e}")

# --- 3. MAIN RUNNER ---
def main():
    # Keep Render alive
    threading.Thread(target=run_web_server, daemon=True).start()

    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("CRITICAL ERROR: TELEGRAM_TOKEN environment variable is missing!")
        return

    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is up, listening safely, and checking Gemini context...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
  
