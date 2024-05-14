# Используем базовый образ PostgreSQL
FROM postgres:latest

COPY init.sql /docker-entrypoint-initdb.d/init.sql
# Указываем порт, на котором будет доступна база данных
EXPOSE ${DB_PORT}
