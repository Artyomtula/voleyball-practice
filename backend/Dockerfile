FROM python:3.12-slim

# Системные библиотеки, без которых не загружается OpenCV
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# PyTorch ставится из индекса CPU-сборок, чтобы образ не тянул библиотеки CUDA
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.15.0 torchvision==0.29.2 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATA_DIR=/data
EXPOSE 8000
