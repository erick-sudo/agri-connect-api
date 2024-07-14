#!/usr/bin/env bash

pip install --upgrade pip

pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Seed Database
# python3 manage.py loaddata superusers.json


# # Collect static files
python manage.py collectstatic --noinput