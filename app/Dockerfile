FROM python:3.10-slim-bullseye
WORKDIR /app
ENV PATH "$PATH:/app"
COPY requirements.txt requirements.txt
RUN sed -i "s/http/https/g" /etc/apt/sources.list && apt-get update && apt-get install -y --no-install-recommends --fix-missing g++ gcc libxslt-dev libffi-dev make graphviz libgraphviz-dev && pip3 install -r requirements.txt
COPY . .
RUN chmod +x /app/*