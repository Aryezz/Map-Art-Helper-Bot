# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm

ENV PREFIX="!!"
ENV TOKEN="YOUR TOKEN HERE"
ENV BLACKLIST="[]"

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY main.py .
COPY config.py .
COPY ./cogs ./cogs

CMD ["python3", "main.py"]