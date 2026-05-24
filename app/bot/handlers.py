from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes
from sqlmodel import Session, select
from app.db.session import engine
from app.db.models import User, Alert
from app.bot.parser import parse_reminder


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main handler: receives any text message and tries to create a reminder."""
    user_text = update.message.text
    telegram_user = update.effective_user

    with Session(engine) as session:
        # Get or create the user in our database
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
            session.refresh(user)

        # Parse the reminder from natural language
        result = parse_reminder(user_text)

        if "error" in result:
            await update.message.reply_text(
                "❌ No pude entender el recordatorio. Prueba con algo como:\n"
                "\"El martes a las 10 llamar al médico\""
            )
            return

        # Save the alert to the database
        scheduled_at = datetime.fromisoformat(result["scheduled_at"]).replace(
            tzinfo=timezone.utc
        )
        alert = Alert(
            user_id=user.id,
            message=result["message"],
            scheduled_at=scheduled_at,
        )
        session.add(alert)
        session.commit()

        await update.message.reply_text(
            f"✅ Recordatorio guardado\n"
            f"📅 {scheduled_at.strftime('%d/%m/%Y a las %H:%M')}\n"
            f"📝 {result['message']}"
        )


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    await update.message.reply_text(
        "👋 Hola! Soy tu bot de recordatorios.\n\n"
        "Dime qué quieres recordar y cuándo, por ejemplo:\n"
        "\"El viernes a las 9 enviar el informe\"\n"
        "\"Mañana comprar pan\""
    )