import json
import logging
import asyncio
import aiohttp
import time
import uuid
from pathlib import Path
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import asyncio
import requests

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

TELEGRAM_BOT_TOKEN = config.get("telegram_bot_token")
OAUTH_CONFIG = config.get("oauth", {})
AI_API_CONFIG = config.get("ai_api", {})
SYSTEM_PROMPT = config.get("system_prompt", "You are a helpful assistant.")

class TokenManager:
    def __init__(self, oauth_config):
        self.oauth_url = oauth_config.get("url")
        self.scope = oauth_config.get("scope")
        self.authorization = oauth_config.get("authorization")
        self.verify = oauth_config.get("verify")
        self.access_token = None
        self.expires_at = 0  # Unix timestamp in seconds
        self.lock = asyncio.Lock()

    async def fetch_token(self):
        """Fetch a new access token from the OAuth endpoint."""
        payload = {
            'scope': self.scope
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': str(uuid.uuid4()),
            'Authorization': self.authorization
        }

        ssl_verify = self.verify_path()

        async with aiohttp.ClientSession() as session:
            try:
                resp = requests.post(self.oauth_url, headers=headers, data=payload, verify=ssl_verify)

                if resp.status_code != 200:
                    text = resp.text
                    logger.error(f"Failed to fetch token: {resp.status_code} {text}")
                    raise Exception(f"Failed to fetch token: {resp.status_code} {text}")

                data = resp.json()
                self.access_token = data.get("access_token")
                expires_at_ms = data.get("expires_at")
                if not self.access_token or not expires_at_ms:
                    logger.error("Invalid token response")
                    raise Exception("Invalid token response")

                # Преобразуем миллисекунды в секунды
                self.expires_at = expires_at_ms / 1000
                logger.info("Successfully fetched new access token.")
            except Exception as e:
                logger.error(f"Error fetching token: {e}")
                raise

    def is_token_valid(self):
        """Check if the current token is still valid."""
        return self.access_token and time.time() < self.expires_at - 60  # Refresh 60 seconds before expiry

    async def get_token(self):
        """Get a valid access token, refreshing it if necessary."""
        async with self.lock:
            if not self.is_token_valid():
                logger.info("Access token expired or not present. Fetching a new token.")
                await self.fetch_token()
            return self.access_token

    def verify_path(self):
        """Return the path to the SSL certificate or True to use default."""
        verify = self.verify
        if verify:
            path = Path(verify)
            if path.exists():
                return verify
            else:
                logger.warning(f"SSL certificate not found at {verify}. Using default SSL verification.")
        return True

# Initialize TokenManager
token_manager = TokenManager(OAUTH_CONFIG)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    await update.message.reply_text('Привет! Отправь мне текст и я переведу его на Ясный язык.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    help_text = (
        "Отправь мне текст и я переведу его на Ясный язык"
    )
    await update.message.reply_text(help_text)

    #     access_token = await token_manager.get_token()
    # AI_API_CONFIG.get("url")
    # verify=token_manager.verify_path()
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    user_message = update.message.text
    access_token = await token_manager.get_token()
    logger.info(f"Received message from {update.effective_user.id}: {user_message}")

    # Prepare the payload for the AI API
    payload = {
        "model": "GigaChat",
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "stream": False,
        "repetition_penalty": 1
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    try:
        response = requests.post(AI_API_CONFIG.get("url"), headers=headers, json=payload, verify=token_manager.verify_path())
        response.raise_for_status()  # Raise an error for bad status codes
        response_data = response.json()

        # Extract the AI's reply
        ai_reply = response_data.get('choices', [{}])[0].get('message', {}).get('content', 'Извините, я не смог ответить на это.')

    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with AI API: {e}")
        ai_reply = "Извините, произошла ошибка при обработке вашего запроса."

    # Send the AI's reply back to the user
    await update.message.reply_text(ai_reply)

async def on_startup(application):
    """Fetch the initial access token when the bot starts."""
    try:
        await token_manager.get_token()
        logger.info("Initial access token fetched successfully.")
    except Exception as e:
        logger.error(f"Failed to obtain initial access token: {e}")
        # Depending on your needs, you might want to exit or retry
        # For now, we'll let the bot continue running
        pass

def main():
    """Start the Telegram bot."""
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(on_startup).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot and run the startup coroutine
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
