#!/bin/bash

cd api  
# Run migrations
python3 manage.py makemigrations
python3 manage.py migrate

# Seed Database
#python3 manage.py loaddata superusers.json

# Collect static files
python3 manage.py collectstatic --noinput
gunicorn app.wsgi:application --bind 0.0.0.0:8000

cd .. 
