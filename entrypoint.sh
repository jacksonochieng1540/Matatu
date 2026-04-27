#!/bin/bash

set -e

echo "Starting MatatuBook Application..."

echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis started"

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

if [ "$CREATE_SUPERUSER" = "true" ]; then
    echo "Creating superuser..."
    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@matatubook.com', 'admin123')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
END
fi

echo "Starting application..."

if [ "$#" -gt 0 ]; then
    echo "Executing custom command: $@"
    exec "$@"
else
    echo "Starting Gunicorn server..."
    exec gunicorn matatu_booking.wsgi:application --bind 0.0.0.0:8000 --workers 3

fi
