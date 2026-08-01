# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.10.2
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering logs.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install build tools for C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 2. Upgrade pip
RUN python -m pip install --upgrade pip

# 3. Create non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# 4. Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# 5. Copy application source code
COPY . .

# Switch to non-privileged user
USER appuser

EXPOSE 8080

CMD python ./run_screener.py
