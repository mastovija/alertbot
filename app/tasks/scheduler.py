"""
app/tasks/scheduler.py
----------------------
Background task scheduler powered by Celery and Redis.

This module is the "delivery engine" of the application — it runs
independently of the bot and is responsible for actually sending
notifications when conditions are met.

Architecture:
  Two separate processes work together:
  
  - Celery Beat: the clock. Wakes up every minute and puts a
    'check_and_send_alerts' task into the Redis queue. Doesn't
    execute anything itself — just schedules.

  - Celery Worker: the executor. Listens to the Redis queue and
    runs tasks as they arrive. Does the actual database queries,
    condition checks, and Telegram sends.

Why this separation?
  The Telegram bot (main.py) only runs when users are actively writing.
  Celery runs independently 24/7, ensuring alerts are sent at the right
  time regardless of bot activity.

Why Redis?
  Beat and Worker are separate processes that don't share memory.
  Redis acts as the message broker between them — Beat writes tasks
  to Redis, Worker reads and executes them.
"""

from datetime import datetime, timezone
from celery import Celery
from celery.schedules import crontab
from sqlmodel import Session, select
from app.db.session import engine
from app.db.models import Alert, User
from app.core.config import settings

# Initialize Celery with Redis as both the message broker and result backend.
# broker: where tasks are queued (Beat writes here, Worker reads from here)
# backend: where task results are stored (useful for monitoring and debugging)
celery_app = Celery(
    "alertbot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Tell Celery Beat to run check_and_send_alerts every minute.
# crontab(minute="*") means "at every minute of every hour of every day"
# — equivalent to "* * * * *" in standard cron syntax.
celery_app.conf.beat_schedule = {
    "check-alerts-every-minute": {
        "task": "app.tasks.scheduler.check_and_send_alerts",
        "schedule": crontab(minute="*"),
    }
}


def evaluate_condition(alert: Alert) -> tuple[bool, str]:
    """
    Evaluates whether a condition-based alert should be fired.

    Routes the alert to the appropriate checker based on alert_type,
    passes the stored condition parameters, and returns whether the
    condition is met along with a message to send the user.

    Args:
        alert: the Alert object with alert_type and condition_config set

    Returns:
        A tuple of (should_fire, message_to_send)
        should_fire is True if the notification should be sent now

    Note:
        Imports are inside the function to avoid circular import issues
        that can occur with Celery workers loading modules at startup.
    """
    from app.checkers.crypto import check_crypto_price
    from app.checkers.currency import check_currency_rate
    from app.checkers.release import check_release

    # Deserialize the JSON condition parameters stored in the database
    condition = alert.get_condition()
    if not condition:
        return False, ""

    if alert.alert_type == "crypto":
        met, price = check_crypto_price(
            coin=condition["coin"],
            currency=condition["currency"],
            threshold=condition["threshold"],
            direction=condition["direction"],
        )
        msg = f"💰 {alert.message}\nPrecio actual: {price:,.0f} {condition['currency'].upper()}"
        return met, msg

    elif alert.alert_type == "currency":
        met, rate = check_currency_rate(
            from_currency=condition["from"],
            to_currency=condition["to"],
            threshold=condition["threshold"],
            direction=condition["direction"],
        )
        msg = f"💱 {alert.message}\nTipo de cambio actual: {rate:.4f}"
        return met, msg

    elif alert.alert_type == "release":
        met, status = check_release(
            query=condition["query"],
            media_type=condition["media_type"],
        )
        msg = f"🎬 {status}"
        return met, msg

    return False, ""


@celery_app.task
def check_and_send_alerts():
    """
    Core task: checks all pending alerts and sends notifications when due.

    Runs every minute via Celery Beat. For each unsent alert:
      - Scheduled alerts: fires if scheduled_at has passed
      - Condition alerts: calls the appropriate checker to evaluate

    Important: we mark alerts as sent BEFORE sending the Telegram message.
    This "mark before send" pattern prevents duplicate notifications if
    the task runs again before the message is delivered — we prefer
    missing one message over spamming the user.
    """
    import asyncio
    from telegram import Bot

    now = datetime.now(timezone.utc)
    bot = Bot(token=settings.telegram_bot_token)

    # Collect (chat_id, message) pairs to send after processing all alerts.
    # We send them all in a single asyncio.run() call to avoid the
    # "event loop is closed" error that occurs when asyncio.run() is
    # called multiple times in the same Celery worker process.
    messages_to_send = []

    with Session(engine) as session:
        pending_alerts = session.exec(
            select(Alert).where(Alert.sent == False)
        ).all()

        if not pending_alerts:
            return

        for alert in pending_alerts:
            user = session.get(User, alert.user_id)
            if not user:
                continue

            should_fire = False
            message = ""

            if alert.alert_type == "scheduled":
                if alert.scheduled_at and alert.scheduled_at <= now:
                    should_fire = True
                    message = f"🔔 Recordatorio\n📝 {alert.message}"
            else:
                try:
                    should_fire, message = evaluate_condition(alert)
                except Exception as e:
                    print(f"Error checking alert {alert.id}: {e}")
                    continue

            if should_fire:
                # Mark as sent and commit BEFORE sending
                alert.sent = True
                session.add(alert)
                session.commit()

                # Queue the message for sending
                messages_to_send.append((user.telegram_id, message))

    # Send all messages in a single async call using gather()
    # gather() runs all sends concurrently instead of one by one
    if messages_to_send:
        async def send_all():
            tasks = [
                bot.send_message(chat_id=chat_id, text=text)
                for chat_id, text in messages_to_send
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        asyncio.run(send_all())