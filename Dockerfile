# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.10.2
FROM python:${PYTHON_VERSION}-slim as base


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser


COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

USER appuser
EXPOSE 8080
CMD python ./run_screener.py
