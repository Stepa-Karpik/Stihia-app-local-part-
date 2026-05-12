FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
COPY requirements-asr.txt .
RUN pip install --no-cache-dir -r requirements.txt
ARG INSTALL_ASR_RUNTIME=false
RUN if [ "$INSTALL_ASR_RUNTIME" = "true" ]; then \
    apt-get update && \
    apt-get install -y --no-install-recommends build-essential cmake && \
    rm -rf /var/lib/apt/lists/*; \
    fi
RUN if [ "$INSTALL_ASR_RUNTIME" = "true" ]; then pip install --no-cache-dir -r requirements-asr.txt; fi

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
