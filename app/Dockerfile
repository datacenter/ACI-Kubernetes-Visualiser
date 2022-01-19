FROM python:3.9-slim as vkaci
WORKDIR /app
ENV PATH "$PATH:/app"
COPY requirements.txt requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing g++ gcc libxslt-dev libffi-dev make graphviz libgraphviz-dev && pip3 install -r requirements.txt
COPY . .
RUN chmod +x /app/*

FROM python:3.9-slim as vkaci-init
RUN pip3 install requests
WORKDIR /app
COPY init.py .
