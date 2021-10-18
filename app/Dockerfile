FROM python:3.9-slim as vkaci
RUN apt-get -o Acquire::http::Timeout=5 update && apt-get -o Acquire::http::Timeout=5 install -y --no-install-recommends --fix-missing g++ gcc libxslt-dev libffi-dev make graphviz libgraphviz-dev && pip3 install https://github.com/datacenter/pyaci/archive/master.zip kubernetes flask pygraphviz
WORKDIR /app
ENV PATH "$PATH:/app"
COPY . .
RUN chmod +x /app/*

FROM python:3.9-slim as vkaci-init
RUN pip3 install requests
WORKDIR /app
COPY init.py .
