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

# Collect one snapshot on startup then keep collecting hourly in background;
# geo-viz serves the data as it accumulates.
CMD ["sh", "-c", "ig-pulse collect --once --data-dir /app/data && ig-pulse collect --interval 90 --data-dir /app/data & ig-pulse geo-viz --port 8080 --data-dir /app/data"]
