import asyncio
from workers.celery_app import celery_app
from workers.webhook_worker import process_webhook_event


@celery_app.task(name="recoveros.process_webhook_event", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def process_webhook_event_task(event_id: str) -> None:
    asyncio.run(process_webhook_event(event_id))
