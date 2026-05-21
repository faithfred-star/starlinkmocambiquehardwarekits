#!/usr/bin/env bash
# exit on error
set -o errexit

# Force upgrade pip and install requirements directly into Render's active environment
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Run migrations and static collection
python manage.py collectstatic --no-input
python manage.py migrate