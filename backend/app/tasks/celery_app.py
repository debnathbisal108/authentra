from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "authentra",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.resume_tasks",
        "app.tasks.consent_tasks",
        "app.tasks.verification_tasks",
        "app.tasks.analysis_tasks",
        "app.tasks.followup_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.resume_tasks.*": {"queue": "resume_parsing"},
        "app.tasks.consent_tasks.*": {"queue": "consent_email"},
        "app.tasks.verification_tasks.*": {"queue": "employment_verification"},
        "app.tasks.analysis_tasks.*": {"queue": "fraud_analysis"},
        "app.tasks.followup_tasks.*": {"queue": "followups"},
    },
    beat_schedule={
        "send-verification-followups": {
            "task": "app.tasks.followup_tasks.send_followup_reminders",
            "schedule": 3600.0,  # every hour
        },
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_use_ssl={"ssl_cert_reqs": None},
    redis_backend_use_ssl={"ssl_cert_reqs": None},
)
