FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=${TZ:-UTC}

RUN apt-get update && apt-get install -y --no-install-recommends \
      tzdata \
      libjpeg62-turbo \
      libfreetype6 \
      libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# create data dir for sqlite and reports
RUN mkdir -p /app/data
VOLUME ["/app/data"]

CMD ["python", "-m", "app.bot"]
