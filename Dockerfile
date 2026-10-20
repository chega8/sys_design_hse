FROM python:3.12.8-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN --mount=type=secret,id=pip_ca \
    if [ -f /run/secrets/pip_ca ]; then \
      PIP_CERT=/run/secrets/pip_ca pip install --no-cache-dir -r requirements.txt; \
    else pip install --no-cache-dir -r requirements.txt; fi
COPY scripts ./scripts
COPY tests ./tests
COPY sql ./sql
CMD ["python", "scripts/produce.py", "/data/train.csv", "/data/test.csv"]
