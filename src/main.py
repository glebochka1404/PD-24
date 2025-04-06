from google import genai
import json
import logging
from google.genai import types
import os

import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load configuration
with open(os.path.join(os.getcwd(), "config.json"), "r", encoding="utf-8") as f:
    config = json.load(f)

TELEGRAM_BOT_TOKEN = config.get("telegram_bot_token")
API_KEY = config.get("api_key")
SYSTEM_PROMPT = config.get("system_prompt")

os.environ["HTTP_PROXY"] = config.get("http_proxy")
os.environ["HTTPS_PROXY"] = config.get("https_proxy")

client = genai.Client(api_key=API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    await update.message.reply_text(
        "Привет! Отправь мне текст и я переведу его на Ясный язык."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    help_text = """Привет! 👋 
 
Я — твой помощник по переводу сложных текстов на ясный и понятный язык. Моя задача — сделать информацию доступной и легкой для восприятия.  
 
Если у тебя есть текст, который ты хочешь упростить, просто отправь его мне, и я помогу сделать его более понятным😊 
 
Давай сделаем общение проще вместе!"""
    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    user_message = update.message.text
    logger.info(f"Received message from {update.effective_user.id}: {user_message}")

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT),
            contents=user_message
        )

        response_data = response.text
        print(response_data)
        ai_reply = response_data


    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with AI API: {e}")
        ai_reply = "Извините, произошла ошибка при обработке вашего запроса."

    # Send the AI's reply back to the user
    await update.message.reply_text(ai_reply)


async def on_startup(application):
    pass


def main():
    """Start the Telegram bot."""
    application = (
        ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(on_startup).build()
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Start the bot and run the startup coroutine
    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
