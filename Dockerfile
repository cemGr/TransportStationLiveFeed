# syntax=docker/dockerfile:1
FROM python:3.11-slim

# 1) set working dir
WORKDIR /app

# 2) ensure logs are unbuffered
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 3) system deps for Postgres & building wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       libpq-dev \
       build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4) install Python requirements
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# 5) copy all application code
COPY . .

# 6) expose Streamlit’s default port
EXPOSE 8501

# 7) default entrypoint so we can override with `command:` in compose
ENTRYPOINT ["python"]
