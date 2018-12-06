FROM python:3.7-alpine3.8

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    python3-dev \
    musl-dev \
    postgresql-dev

WORKDIR /code

ADD . /code

RUN pip install -r requirements.txt
