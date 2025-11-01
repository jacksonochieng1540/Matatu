#!/bin/bash
# docker/entrypoint.sh

set -e

echo "Starting MatatuBook Application..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis started"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if it doesn't exist (for development)
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

# FIX: Use explicit commands based on service
echo "Starting application..."

# Check if we're running a specific command, otherwise default to gunicorn
if [ "$#" -gt 0 ]; then
    # If arguments are passed, execute them
    echo "Executing custom command: $@"
    exec "$@"
else
    # Default command for web service
    echo "Starting Gunicorn server..."
    exec gunicorn matatu_booking.wsgi:application --bind 0.0.0.0:8000 --workers 3

fi