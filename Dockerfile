FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (including your new app/fonts/ folder automatically)
COPY app ./app

RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8025

CMD ["gunicorn", "app.main:app", "--bind", "0.0.0.0:8025", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--preload", "--log-level", "warning", "--access-logfile", "/dev/null"]
