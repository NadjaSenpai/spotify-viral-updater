FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget unzip libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libxss1 libasound2 libxcomposite1 libxrandr2 libgbm-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip && pip install -r requirements.txt && playwright install chromium

CMD ["python", "update_playlist.py"]
