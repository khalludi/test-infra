# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /app

COPY coalesce.py coalesce_test.py ./

CMD [ "python3", "coalesce_test.py"]