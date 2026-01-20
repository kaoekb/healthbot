FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

# matplotlib/reportlab dependencies
RUN apt-get update && apt-get install -y --no-install-recommends     fonts-dejavu-core     fontconfig     && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app

# default data dir inside container
ENV DATA_DIR=/data
RUN mkdir -p /data

CMD ["python", "-m", "app.main"]
