FROM python:3.12

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./ /code/appversion: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 80 --reload
    ports:
       - "80:80"