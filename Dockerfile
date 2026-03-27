FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry && poetry config virtualenvs.in-project true

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root

COPY . .

RUN mkdir -p /data

EXPOSE 8000

CMD ["sh", "-c", "poetry run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
