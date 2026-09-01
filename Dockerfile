
FROM python:3.12-slim

WORKDIR /app

COPY requirements-docker.txt .

RUN pip install --no-cache-dir -r requirements-docker.txt

COPY src ./src
COPY .env.example .env

CMD ["python", "-m", "src.main"]