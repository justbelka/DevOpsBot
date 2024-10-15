#!/bin/bash
set -e

# Создание пользователя для репликации с паролем и создание базы данных
psql -v ON_ERROR_STOP=1 --username "$DB_USER" --dbname "postgres" <<-EOSQL
    CREATE USER $DB_REPL_USER REPLICATION LOGIN ENCRYPTED PASSWORD '$DB_REPL_PASSWORD';
EOSQL

# Подключаемся к базе данных pt и создаем таблицы
psql -v ON_ERROR_STOP=1 --username "$DB_USER" --dbname "pt" <<-EOSQL
    CREATE TABLE phones (
        id SERIAL PRIMARY KEY,
        phone VARCHAR(11)
    );

    CREATE TABLE emails (
        id SERIAL PRIMARY KEY,
        email VARCHAR(30)
    );
EOSQL

echo "host replication ${DB_REPL_USER} 192.168.0.12/32 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
