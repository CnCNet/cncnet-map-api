# Don't run this file manually. It's the entry point for the dockerfile.
python manage.py collectstatic --noinput
python manage.py migrate
# `python manage.py runserver`, but with gunicorn instead.
gunicorn "kirovy.wsgi:application" --bind "0.0.0.0:8000"
