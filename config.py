import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация Celery
class CeleryConfig:
    broker_url = os.getenv('REDIS_URL')
    result_backend = os.getenv('REDIS_URL')
    task_serializer = 'json'
    result_serializer = 'json'
    accept_content = ['json']
    enable_utc = True
    task_always_eager = True


# celery -A main worker --loglevel=info