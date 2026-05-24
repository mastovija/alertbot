from telegram.ext import Application, MessageHandler, CommandHandler, filters
from app.core.config import settings
from app.bot.handlers import handle_message, handle_start


def main():
    """Start the bot in polling mode (development only)."""
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot iniciado. Ctrl+C para parar.")
    app.run_polling()


if __name__ == "__main__":
    main()