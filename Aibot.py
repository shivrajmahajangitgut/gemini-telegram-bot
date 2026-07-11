import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Configure Gemini with your free API key from the environment
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Dict to store separate conversation sessions for every unique Telegram user
user_chats = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignore messages that do not contain text
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Start a new conversation history for this user if they are new
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
        
    try:
        # send_message automatically builds on top of past history
        response = user_chats[user_id].send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("Sorry, I encountered an issue processing that.")

def main():
    # Fetch your Telegram Bot token from the environment variables
    token = os.environ.get("TELEGRAM_TOKEN")
    
    if not token:
        print("Missing TELEGRAM_TOKEN environment variable!")
        return

    app = Application.builder().token(token).build()
    
    # Tell the bot to look for text messages (ignoring commands like /start)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is starting up...")
    app.run_polling()

if __name__ == '__main__':
    main()
  
