"""
app/bot/handlers.py
-------------------
Telegram bot message handlers.

This module defines what the bot does when it receives each type of input.
Each handler is an async function that receives the Telegram update (the
incoming message) and a context object with bot utilities.

Handlers registered in main.py:
  - handle_start: responds to the /start command
  - handle_message: processes any free-text message and creates an alert
"""

from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes
from sqlmodel import Session, select
from app.db.session import engine
from app.db.models import User, Alert
from app.bot.parser import parse_alert


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main handler: receives any text message and creates an alert from it.

    Flow:
      1. Get or create the user in our database
      2. Parse the message with Claude to determine alert type and parameters
      3. Save the alert to the database
      4. Confirm to the user what was saved

    The function is async because Telegram's library is asynchronous —
    while waiting for the Claude API or database, other messages can be processed.
    """
    user_text = update.message.text
    telegram_user = update.effective_user

    with Session(engine) as session:

        # --- Step 1: Get or create user ---
        # We look up the user by telegram_id on every message.
        # If they're new, we create them automatically — no registration needed.
        # This pattern is called "get or create" and is very common in web apps.
        user = session.exec(
            select(User).where(User.telegram_id == telegram_user.id)
        ).first()

        if not user:
            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
            )
            session.add(user)
            session.commit()
            session.refresh(user)  # refresh loads the auto-generated id from the DB

        # --- Step 2: Parse the message ---
        result = parse_alert(user_text)

        if "error" in result:
            await update.message.reply_text(
                "❌ No pude entender la alerta. Prueba con algo como:\n"
                "• \"El martes a las 10 llamar al médico\"\n"
                "• \"Avísame cuando Bitcoin baje de 80.000€\"\n"
                "• \"Avísame cuando estrene la temporada 3 de Severance\""
            )
            return

        # --- Step 3: Build and save the alert ---
        alert_type = result["alert_type"]
        alert = Alert(user_id=user.id, message=result["message"], alert_type=alert_type)

        if alert_type == "scheduled":
            # For scheduled alerts, store the target datetime.
            # replace(tzinfo=timezone.utc) ensures the datetime is timezone-aware —
            # Python's datetime is "naive" (no timezone) by default, which causes
            # comparison bugs when mixed with timezone-aware datetimes.
            alert.scheduled_at = datetime.fromisoformat(result["scheduled_at"]).replace(
                tzinfo=timezone.utc
            )
            confirmation = (
                f"✅ Recordatorio guardado\n"
                f"📅 {alert.scheduled_at.strftime('%d/%m/%Y a las %H:%M')}\n"
                f"📝 {result['message']}"
            )
        else:
            # For condition-based alerts, store the condition parameters as JSON.
            # The scheduler will read these parameters each minute to evaluate
            # whether the condition has been met.
            alert.set_condition(result["condition"])
            confirmation = (
                f"✅ Alerta guardada\n"
                f"🔍 Te avisaré cuando se cumpla la condición\n"
                f"📝 {result['message']}"
            )

        session.add(alert)
        session.commit()

        # --- Step 4: Confirm to the user ---
        await update.message.reply_text(confirmation)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /start command.

    /start is sent automatically by Telegram when a user first opens the bot,
    and can also be sent manually at any time. It's the standard entry point
    for any Telegram bot.
    """
    await update.message.reply_text(
        "👋 Hola! Soy tu asistente de alertas.\n\n"
        "Puedo avisarte cuando:\n"
        "📅 Llegue una fecha: \"El viernes a las 9 enviar el informe\"\n"
        "₿ Crypto llegue a un precio: \"Bitcoin bajo de 80.000€\"\n"
        "💱 Una divisa cruce un umbral: \"El dólar sobre 0.95€\"\n"
        "🎬 Estrene una peli o serie: \"Temporada 3 de Severance\"\n\n"
        "Escríbeme en lenguaje natural, yo me encargo del resto."
    )