FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar cliente de postgres (para pg_isready) y curl (para healthcheck)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x Entrypoint.sh && \
    sed -i 's/\r$//' Entrypoint.sh

ENTRYPOINT ["./Entrypoint.sh"]