FROM python:3.6-stretch AS production

WORKDIR /opt/qllr

COPY --chown=www-data . .

RUN python3 -m pip install -r requirements.txt

# -------

FROM production AS develop

RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ stretch-pgdg main" > /etc/apt/sources.list.d/pgdg.list
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -

RUN apt-get update && apt-get install -y postgresql-9.6

RUN python3 -m pip install -r requirements_dev.txt

ENV PATH="/usr/lib/postgresql/9.6/bin:${PATH}"

USER www-data

CMD ["./scripts/test"]

# -------

FROM production

USER www-data

CMD ["sh", "-c", "./docker/entrypoint.py && ./main.py"]
