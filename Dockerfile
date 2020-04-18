FROM python:3.5-stretch

WORKDIR /opt/qllr

COPY --chown=www-data . .

RUN python3 -m pip install -r requirements.txt

USER www-data

CMD ["sh", "-c", "./docker/entrypoint.py && ./main.py"]
