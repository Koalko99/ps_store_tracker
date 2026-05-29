FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY config.json ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

CMD ["ps-store-tracker", "collect", "--region", "ru-ua"]
