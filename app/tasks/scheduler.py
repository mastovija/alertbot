from datetime import datetime, timezone
from celery import Celery
from celery.schedules import crontab
from sqlmodel import Session, select
from app.db.session import engine
from app.db.models import Alert, User
from app.core.config import settings

celery_app = Celery(
    "alertbot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Run check_and_send_alerts every minute
celery_app.conf.beat_schedule = {
    "check-alerts-every-minute": {
        "task": "app.tasks.scheduler.check_and_send_alerts",
        "schedule": crontab(minute="*"),
    }
}


@celery_app.task
def check_and_send_alerts():
    """
    Checks the database for pending alerts that are due and sends them.
    Runs every minute via Celery Beat.
    """
    import asyncio
    from telegram import Bot

    now = datetime.now(timezone.utc)
    bot = Bot(token=settings.telegram_bot_token)

    with Session(engine) as session:
        # Find all unsent alerts whose scheduled time has passed
        due_alerts = session.exec(
            select(Alert)
            .where(Alert.sent == False)
            .where(Alert.scheduled_at <= now)
        ).all()

        if not due_alerts:
            return

        for alert in due_alerts:
            user = session.get(User, alert.user_id)
            if not user:
                continue

            # Send the reminder via Telegram
            asyncio.run(
                bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"🔔 Recordatorio\n📝 {alert.message}",
                )
            )

            # Mark as sent so we don't send it again
            alert.sent = True
            session.add(alert)

        session.commit()