FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# NOTE: OPENAI_API_KEY is intentionally NOT set here to avoid
# baking secrets into the image. Pass it at runtime, for example:
#   docker run -e OPENAI_API_KEY=... resume-matcher-api

CMD ["uvicorn", "backend.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]

