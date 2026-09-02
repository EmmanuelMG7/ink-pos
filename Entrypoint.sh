#!/bin/bash
set -e

echo "Esperando a que PostgreSQL acepte conexiones..."
# El script se detiene en este bucle hasta que pg_isready devuelve éxito
while ! pg_isready -h db -p 5432 -U "${DB_USER}"; do
  echo "Postgres no está listo, esperando 2 segundos..."
  sleep 2
done
echo "¡PostgreSQL está listo!"

echo "Aplicando migraciones de la base de datos..."
python manage.py migrate --noinput

echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "Iniciando Gunicorn..."
exec gunicorn mi_proyecto.wsgi:application --bind 0.0.0.0:8000 --workers 3