#!/bin/bash
# 启动 Celery Worker

celery -A backend.tasks.celery_app worker --loglevel=info
