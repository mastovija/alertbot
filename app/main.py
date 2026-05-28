"""
app/main.py
-----------
Entry point for the Telegram bot.

This module creates the bot application, registers the message handlers,
and starts the polling loop that listens for incoming messages.

How Telegram bots work:
  When a user writes to your bot, Telegram stores the message on their servers.
  Your bot retrieves it in one of two ways:

  - Polling (used here): your bot asks Telegram every few seconds
    "any new messages?" This is simple and works great for development
    since it doesn't require a public URL.

  - Webhook (used in production): you give Telegram a URL, and Telegram
    calls your server instantly when a new message arrives. Faster and
    more efficient, but requires a public HTTPS server.

  We use polling for now and will switch to webhook in Phase 4 when
  we deploy to a cloud server.

To run:
  python -m app.main
"""

from telegram.ext import Application, MessageHandler, CommandHandler, filters
from app.core.config import settings
from app.bot.handlers import handle_message, handle_start


def main():
    """
    Initializes and starts the Telegram bot in polling mode.

    Application.builder() creates a new bot application using the token
    from our settings. The token identifies which bot we are to Telegram —
    obtained from @BotFather when the bot was created.
    """
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Register handlers — these tell the bot which function to call
    # for each type of incoming message.

    # CommandHandler fires when a user sends a command like /start
    app.add_handler(CommandHandler("start", handle_start))

    # MessageHandler fires for any text message that isn't a command.
    # filters.TEXT: only text messages (not photos, stickers, etc.)
    # ~filters.COMMAND: exclude messages starting with / (those go to CommandHandler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot iniciado. Ctrl+C para parar.")

    # run_polling() starts an infinite loop that:
    #   1. Asks Telegram for new messages every few seconds
    #   2. Routes each message to the appropriate handler
    #   3. Repeats until Ctrl+C
    app.run_polling()


if __name__ == "__main__":
    main()