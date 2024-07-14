#!/usr/bin/env bash

pip install -r requirements.txt

# Run migrations
python3 manage.py makemigrations
python3 manage.py migrate

# Seed Database
python3 manage.py loaddata superusers.json


# # Collect static files
python manage.py collectstatic --noinput