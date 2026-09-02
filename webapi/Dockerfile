FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/api

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default internal port; docker-compose overrides the bind via $PORT.
EXPOSE 5454

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5454} --workers 2 --timeout 60 --access-logfile - wblester_api.wsgi:application"]
