# Dockerfile для главной БД
FROM postgres:15

RUN mkdir -p /oracle/pg_data/archive && chown -R postgres:postgres /oracle

COPY ./init.sh /docker-entrypoint-initdb.d/
