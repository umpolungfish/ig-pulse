FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
COPY ig_pulse/ /app/ig_pulse/
COPY data/     /app/data/

RUN pip install --no-cache-dir flask flask-cors numpy scipy networkx requests hatchling && \
    pip install --no-cache-dir .

EXPOSE 8080

CMD ["ig-pulse", "geo-viz", "--port", "8080", "--data-dir", "/app/data"]
