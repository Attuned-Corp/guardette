FROM python:3.13-slim

RUN pip install poetry

WORKDIR /app

COPY ./src/guardette /app/src/guardette
COPY pyproject.toml poetry.lock /app/
RUN poetry install --only main

COPY main.py /app/
COPY ./.guardette/policy.yml /app/.guardette/policy.yml

ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE ${PORT}
CMD poetry run uvicorn main:app --host ${HOST} --port ${PORT}
