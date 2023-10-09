FROM python:3.10-slim
WORKDIR /app
ENV PATH "$PATH:/app"
COPY requirements.txt requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing g++ gcc make && pip3 install -r requirements.txt
COPY . .
RUN chmod +x /app/*
